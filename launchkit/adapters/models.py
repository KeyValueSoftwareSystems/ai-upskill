import os
import socket
from urllib.parse import urlparse

from agno.exceptions import ModelProviderError
from agno.models.openai import OpenAIChat

from launchkit.adapters.fakes import BriefModel, EchoModel, EndlessModel, GoodModel, LookupModel, MalformedModel, MemoryModel, ProfileModel
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



def check_reachable(model):
    """Called when a run starts: a proxy model whose proxy does not answer stops the run here."""
    if isinstance(model, ProxyChat):
        reach(str(model.base_url))


def resolve_model(settings, trace: Trace):
    provider, sep, model_id = settings.model.partition(":")
    if not sep:
        provider, model_id = "openai", settings.model
    if provider == "fake":
        if model_id not in FAKES:
            raise ValueError(f"unknown fake model {model_id!r}; choose one of {sorted(FAKES)}")
        return FAKES[model_id]()
    if provider == "openai" and proxy():
        key, url = proxy()
        model = ProxyChat(
            # No retry inside the OpenAI client: it is silent. Agno's retries reach the trace and the Working line.
            id=model_id, api_key=key, base_url=url, timeout=settings.timeout, max_retries=0, retries=3, delay_between_retries=1,
            extra_body={"cache": {"no-cache": True}},
        )
        model.on_retry = lambda text: trace.note(text)
        return model
    key = PROVIDER_KEYS.get(provider)
    if key and not os.environ.get(key):
        trace.note(
            f"No key: set LITELLM_API_KEY and LITELLM_BASE_URL (KeyValue's proxy) or {key}. "
            f"LAUNCHKIT_MODEL={settings.model} cannot run, so this is the Good fake model."
        )
        return GoodModel()
    if provider == "openai":
        return OpenAIChat(id=model_id, timeout=settings.timeout, max_retries=1)
    return f"{provider}:{model_id}"


def model_name(model) -> str:
    return model if isinstance(model, str) else f"{model.provider}:{model.id}"


from launchkit.adapters.fakes import ToolsModel  # noqa: E402  Session 2's fake for the main agent

FAKES["tools"] = ToolsModel
