import os

from agno.models.openai import OpenAIChat

from launchkit.adapters.fakes import EchoModel, EndlessModel, GoodModel, MalformedModel, ProfileModel
from launchkit.harness.trace import Trace

PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
}

FAKES = {"echo": EchoModel, "malformed": MalformedModel, "endless": EndlessModel, "good": GoodModel, "profile": ProfileModel}


def proxy() -> tuple[str, str] | None:
    key, url = os.environ.get("LITELLM_API_KEY"), os.environ.get("LITELLM_BASE_URL")
    return (key, url) if key and url else None


class ProxyChat(OpenAIChat):
    """Through the proxy a 401 is usually its upstream key having a bad moment, not ours, so it is worth another try."""

    def _is_retryable_error(self, error) -> bool:
        return error.status_code == 401 or super()._is_retryable_error(error)


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
        return ProxyChat(
            id=model_id, api_key=key, base_url=url, timeout=settings.timeout, max_retries=1, retries=3, delay_between_retries=1,
            extra_body={"cache": {"no-cache": True}},
        )
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
