import os
import socket
import time
from urllib.parse import urlparse

import httpx
from agno.exceptions import ModelProviderError
from agno.models.openai import OpenAIChat

from launchkit.adapters.fakes import BriefModel, DownModel, EchoModel, EndlessModel, GoodModel, LookupModel, MalformedModel, ProfileModel
from launchkit.adapters.pricing import cost_usd
from launchkit.settings import DEFAULT_MODEL
from launchkit.trace import Trace

PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
}

FAKES = {"echo": EchoModel, "malformed": MalformedModel, "endless": EndlessModel, "good": GoodModel, "lookup": LookupModel, "profile": ProfileModel, "brief": BriefModel, "down": DownModel}


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


def scoreboard_client(model_ref: dict) -> httpx.Client:
    """An HTTP client that tells the model about every answer it gets back: how long it took, the tokens, and what the
    proxy charged (the x-litellm-response-cost header). The model passes that on to the scoreboard through `on_call`."""

    def started(request: httpx.Request):
        request.extensions["started"] = time.perf_counter()

    def finished(response: httpx.Response):
        model = model_ref.get("model")
        on_call = getattr(model, "on_call", None)
        if on_call is None or response.status_code >= 400:
            return
        response.read()
        try:
            usage = response.json().get("usage") or {}
        except ValueError:
            usage = {}
        seconds = time.perf_counter() - response.request.extensions.get("started", time.perf_counter())
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
        cached = int(((usage.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0)
        header = response.headers.get("x-litellm-response-cost")
        usd = float(header) if header else cost_usd(model.id, input_tokens, cached, output_tokens)
        on_call(round(seconds, 2), input_tokens, cached, output_tokens, usd)

    return httpx.Client(event_hooks={"request": [started], "response": [finished]})


class ProxyChat(OpenAIChat):
    """Through the proxy a 401 is usually its upstream key having a bad moment, not ours, so it is worth another try."""

    on_call = None

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



def check_reachable(model):
    """Called when a run starts: a proxy model whose proxy does not answer stops the run here."""
    if isinstance(model, ProxyChat):
        reach(str(model.base_url))


def resolve_model(settings, trace: Trace, name: str | None = None):
    """The model object for a name: a fake, the proxy, or a provider's own client. With no name, the configured one,
    and with nothing configured, DEFAULT_MODEL."""
    wanted = name or settings.model or DEFAULT_MODEL
    provider, sep, model_id = wanted.partition(":")
    if not sep:
        provider, model_id = "openai", wanted
    if provider == "fake":
        if model_id not in FAKES:
            raise ValueError(f"unknown fake model {model_id!r}; choose one of {sorted(FAKES)}")
        return FAKES[model_id]()
    if provider == "openai" and proxy():
        key, url = proxy()
        model_ref: dict = {}
        model = ProxyChat(
            # No retry inside the OpenAI client: it is silent. Agno's retries reach the trace and the Working line.
            id=model_id, api_key=key, base_url=url, timeout=settings.timeout, max_retries=0, retries=3, delay_between_retries=1,
            extra_body={"cache": {"no-cache": True}}, http_client=scoreboard_client(model_ref),
        )
        model_ref["model"] = model
        model.on_retry = lambda text: trace.note(text)
        return model
    key = PROVIDER_KEYS.get(provider)
    if key and not os.environ.get(key):
        trace.note(
            f"No key: set LITELLM_API_KEY and LITELLM_BASE_URL (KeyValue's proxy) or {key}. "
            f"{wanted} cannot run, so this is the Good fake model."
        )
        return GoodModel()
    if provider == "openai":
        return OpenAIChat(id=model_id, timeout=settings.timeout, max_retries=1)
    return f"{provider}:{model_id}"


def model_name(model) -> str:
    return model if isinstance(model, str) else f"{model.provider}:{model.id}"


from launchkit.adapters.fakes import ToolsModel  # noqa: E402  Session 2's fake for the main agent

FAKES["tools"] = ToolsModel
