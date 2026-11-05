import os
import socket
import threading
import time
from dataclasses import replace

import httpx
from urllib.parse import urlparse

from agno.exceptions import ModelProviderError
from agno.models.openai import OpenAIChat

from launchkit.adapters.fakes import BriefModel, EchoModel, EndlessModel, GoodModel, LookupModel, MalformedModel, MemoryModel, ProfileModel
from launchkit.adapters.routing import route
from launchkit.settings import DEFAULT_MODEL
from launchkit.trace import Trace

PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
}

FAKES = {"echo": EchoModel, "malformed": MalformedModel, "endless": EndlessModel, "good": GoodModel, "lookup": LookupModel, "profile": ProfileModel, "brief": BriefModel, "memory": MemoryModel}


def proxy() -> tuple[str, str] | None:
    key, url = os.environ.get("LITELLM_API_KEY"), os.environ.get("LITELLM_BASE_URL")
    return (key, url) if key and url else None


def reach(url: str, seconds: float = 3.0):
    """KeyValue's proxy is reached through the VPN. If it does not answer, say so now; a model call would wait minutes."""
    found = urlparse(url)
    try:
        socket.create_connection((found.hostname, found.port or (443 if found.scheme == "https" else 80)), timeout=seconds).close()
    except OSError:
        raise ModelProviderError(f"Cannot reach KeyValue's model proxy ({found.hostname}). Is the VPN on?", status_code=503) from None


_proxy_cost = threading.local()  # the cost the proxy reported for this thread's last call


def _remember_cost(response: httpx.Response):
    """LiteLLM puts what it charged for a call in a response header, not in the body."""
    value = response.headers.get("x-litellm-response-cost")
    _proxy_cost.value = float(value) if value else None


PROXY_HTTP = httpx.Client(event_hooks={"response": [_remember_cost]})


class ProxyChat(OpenAIChat):
    """Through the proxy a 401 is usually its upstream key having a bad moment, not ours, so it is worth another try."""

    def _is_retryable_error(self, error) -> bool:
        retry = error.status_code == 401 or super()._is_retryable_error(error)
        self.last_error = " ".join(str(error.message).split())[:80]
        return retry

    def _get_retry_delay(self, attempt: int) -> float:
        """Agno asks for the delay only when it is about to try again, so this is where the trace hears of a retry."""
        if getattr(self, "on_retry", None):
            error = getattr(self, "last_error", "no answer")
            why = f"the model did not answer in {self.timeout:g} s" if self.timeout and "timed out" in error.lower() else f"model call failed ({error})"
            self.on_retry(f"{why}, trying again: {attempt + 2} of {self.retries + 1}")
        return super()._get_retry_delay(attempt)

    def invoke(self, *args, **kwargs):
        """Every real model call, timed, so the scoreboard can say which job spent what. Agents, the memory manager
        and the summary all come through here."""
        _proxy_cost.value = None
        started = time.perf_counter()
        response = super().invoke(*args, **kwargs)
        if getattr(self, "on_call", None):
            usage = response.response_usage
            self.on_call(time.perf_counter() - started, getattr(usage, "input_tokens", 0) or 0,
                         getattr(usage, "cache_read_tokens", 0) or 0, getattr(usage, "output_tokens", 0) or 0,
                         getattr(_proxy_cost, "value", None))
        return response



def check_reachable(model):
    """Called when a run starts: a proxy model whose proxy does not answer stops the run here."""
    if isinstance(model, ProxyChat):
        reach(str(model.base_url))


def resolve_model(settings, trace: Trace, name: str | None = None):
    """One model object from a name: Maya's pick, the routed model, or DEFAULT_MODEL when nothing is set."""
    name = name or settings.model or DEFAULT_MODEL
    provider, sep, model_id = name.partition(":")
    if not sep:
        provider, model_id = "openai", name
    if provider == "fake":
        if model_id not in FAKES:
            raise ValueError(f"unknown fake model {model_id!r}; choose one of {sorted(FAKES)}")
        return FAKES[model_id]()
    if provider == "openai" and proxy():
        key, url = proxy()
        model = ProxyChat(
            # No retry inside the OpenAI client: it is silent. Agno's retries reach the trace and the Working line.
            id=model_id, api_key=key, base_url=url, timeout=settings.timeout, max_retries=0, retries=3, delay_between_retries=1,
            http_client=PROXY_HTTP,  # reads what the proxy charged for each call
            extra_body={"cache": {"no-cache": True}},
            reasoning_effort=settings.effort or None,  # LAUNCHKIT_EFFORT or --effort; only reasoning models use it
        )
        model.on_retry = lambda text: trace.note(text)
        return model
    key = PROVIDER_KEYS.get(provider)
    if key and not os.environ.get(key):
        trace.note(
            f"No key: set LITELLM_API_KEY and LITELLM_BASE_URL (KeyValue's proxy) or {key}. "
            f"LAUNCHKIT_MODEL={name} cannot run, so this is the Good fake model."
        )
        return GoodModel()
    if provider == "openai":
        return OpenAIChat(id=model_id, timeout=settings.timeout, max_retries=1)
    return f"{provider}:{model_id}"


def model_name(model) -> str:
    return model if isinstance(model, str) else f"{model.provider}:{model.id}"


from launchkit.adapters.fakes import ToolsModel  # noqa: E402  Session 2's fake for the main agent

FAKES["tools"] = ToolsModel


class DownModel(EchoModel):
    """A model whose provider is down: every call fails, as a real outage does. The routing check uses it."""

    def __init__(self):
        super().__init__()
        self.id = self.name = "down"

    def respond(self, messages, tools):
        raise ModelProviderError("fake:down is down", status_code=503)


FAKES["down"] = DownModel

MAIN_JOBS = ("long_text", "short_text")  # the jobs Maya's pick applies to: the main agent's and the onboarding agent's


class Jobs:
    """Which model does each job.

    - Given one model (a fake in the checks), every job uses it, as in every session before this one.
    - Before route() is built, every job runs on Maya's pick, or on DEFAULT_MODEL when she made none.
    - Once route() is built, it decides per job: Maya's pick, the skill's pin, then the job's rank list. Each choice
      is one route line in the trace, and a failed call moves to the next model on the list.
    """

    def __init__(self, settings, trace: Trace, given=None):
        self.settings, self.trace, self.given = settings, trace, given

    @property
    def routed(self) -> bool:
        return self.given is None and not getattr(route, "todo", False)

    def options(self, job: str, ask: str | None = None, skill=None) -> tuple[str, list[tuple[str, str]]]:
        if self.given is not None:
            return job, [(model_name(self.given), "given")]
        if not self.routed:
            return job, [(self.settings.model or DEFAULT_MODEL, "one setting")]
        pick = (self.settings.model or None) if job in MAIN_JOBS else None
        return route(job, self.settings, ask=ask, pick=pick, skill=skill)

    def build(self, name: str, job: str):
        if self.given is not None:
            return self.given
        offline = self.settings.fake_models or self.settings.model.startswith("fake:")
        if offline and not name.startswith("fake:"):
            from launchkit.adapters.fakes import MemoryModel

            # LAUNCHKIT_FAKE_MODELS, or a fake picked in Model: every job stays offline. The trace keeps the routed name.
            return MemoryModel()
        # Thinking effort is for the main agent's reply only: the other jobs run on models that may not take it.
        settings = self.settings if job in MAIN_JOBS else replace(self.settings, effort="")
        model = resolve_model(settings, self.trace, name)
        if isinstance(model, ProxyChat):
            model.on_call = lambda seconds, sent, cached, got, usd: self.trace.call(job, name, seconds, sent, cached, got, usd)
        return model

    def first(self, job: str, ask: str | None = None, skill=None, when_used: bool = False):
        """The first choice for a job, as (job, model). For calls that are not retried on another model. when_used: the
        route line is written at the model's first call, not now (the memory write may not happen this turn)."""
        job, options = self.options(job, ask, skill)
        if not options:
            raise ModelProviderError(f"No enabled model for {job}: every model on its list is switched off.", status_code=503)
        name, reason = options[0]
        model = self.build(name, job)
        if self.routed and when_used and getattr(model, "on_call", None):
            timed, said = model.on_call, []

            def route_then_time(*args):
                if not said:
                    said.append(True)
                    self.trace.route(job, name, reason)
                timed(*args)

            model.on_call = route_then_time
        elif self.routed:
            self.trace.route(job, name, reason)
        return job, model

    def in_order(self, job: str, call, ask: str | None = None, skill=None):
        """Run call(model) on the first choice; when the call fails, on the next one, and say so in the trace."""
        job, options = self.options(job, ask, skill)
        if not options:
            raise ModelProviderError(f"No enabled model for {job}: every model on its list is switched off.", status_code=503)
        for i, (name, reason) in enumerate(options):
            if self.routed:
                self.trace.route(job, name, "fallback" if i else reason)
            try:
                return call(job, self.build(name, job))
            except ModelProviderError as error:
                if not self.routed or i == len(options) - 1:
                    raise
                self.trace.note(f"{name} failed for {job} ({' '.join(str(error.message).split())[:60]}); trying the next model")


def timed_vision_call(model, **request):
    """A raw chat call for the vision tools, timed for the scoreboard like every call through Agno."""
    from launchkit.adapters.llm import client

    if "api.openai.com" in str(client().base_url):
        request.pop("extra_body", None)  # the no-cache flag is the proxy's; OpenAI itself refuses it
    started = time.perf_counter()
    raw = client().chat.completions.with_raw_response.create(model=model.id, **request)
    reply = raw.parse()
    if getattr(model, "on_call", None) and reply.usage:
        cost = raw.headers.get("x-litellm-response-cost")
        model.on_call(time.perf_counter() - started, reply.usage.prompt_tokens or 0, 0, reply.usage.completion_tokens or 0,
                      float(cost) if cost else None)
    return reply


class Chooser:
    """Picks the model for one job at the moment of the call. The vision tools hold one: ingest_image may be loaded
    mid-turn, and its Model: line pins the vision model from then on."""

    chooser = True

    def __init__(self, jobs: "Jobs", job: str):
        self.jobs, self.job, self.catalogue = jobs, job, None

    def __call__(self):
        skill = self.catalogue.pinning(self.job) if self.catalogue is not None else None
        return self.jobs.first(self.job, skill=skill)[1]


def now(model):
    """A model, or a chooser that picks one at call time (the vision tools: a skill loaded mid-turn can pin a model)."""
    return model() if getattr(model, "chooser", False) else model
