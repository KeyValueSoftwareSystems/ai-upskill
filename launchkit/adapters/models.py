import os

from launchkit.adapters.fakes import EchoModel, EndlessModel, GoodModel, MalformedModel, ProfileModel
from launchkit.harness.trace import Trace

PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
}

FAKES = {"echo": EchoModel, "malformed": MalformedModel, "endless": EndlessModel, "good": GoodModel, "profile": ProfileModel}


def resolve_model(settings, trace: Trace):
    provider, _, model_id = settings.model.partition(":")
    if provider == "fake":
        if model_id not in FAKES:
            raise ValueError(f"unknown fake model {model_id!r}; choose one of {sorted(FAKES)}")
        return FAKES[model_id]()
    key = PROVIDER_KEYS.get(provider)
    if key and not os.environ.get(key):
        trace.note(f"{key} is not set, so LAUNCHKIT_MODEL={settings.model} cannot run. Using the Good fake model.")
        return GoodModel()
    return settings.model


def model_name(model) -> str:
    return model if isinstance(model, str) else f"{model.provider}:{model.id}"
