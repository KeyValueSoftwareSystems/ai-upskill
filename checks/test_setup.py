import base64
from dataclasses import replace
from types import SimpleNamespace

import httpx
import openai
from agno.exceptions import ModelProviderError
from agno.models.openai import OpenAIChat

from launchkit.adapters.images import FakeImages, RealImages, make_images
from launchkit.adapters.models import resolve_model
from launchkit.harness.trace import Trace


def test_proxy_key_and_bare_model_id(settings, monkeypatch):
    """With KeyValue's LiteLLM key set, a bare model id like gpt-4.1-mini runs through the proxy."""
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_BASE_URL", "https://proxy.example/v1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    model = resolve_model(replace(settings, model="gpt-4.1-mini"), Trace())
    assert isinstance(model, OpenAIChat)
    assert model.id == "gpt-4.1-mini"
    assert str(model.base_url) == "https://proxy.example/v1"
    assert model.api_key == "test-key"


def test_provider_prefix_still_works_without_the_proxy(settings, monkeypatch):
    """Without the proxy, provider:model and OPENAI_API_KEY work as before."""
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert resolve_model(replace(settings, model="openai:gpt-5.4-mini"), Trace()) == "openai:gpt-5.4-mini"


def test_no_key_falls_back_to_the_good_fake(settings, monkeypatch):
    """With no key at all, live runs use the Good fake and the trace says so."""
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    trace = Trace()
    model = resolve_model(replace(settings, model="gpt-4.1-mini"), trace)
    assert type(model).__name__ == "GoodModel"
    assert any("LITELLM_API_KEY" in e.detail.get("text", "") for e in trace.events)


def test_placeholder_switch_means_fake_pictures(settings, monkeypatch):
    """LAUNCHKIT_IMAGES=placeholder, the opener's switch, gives fake pictures too."""
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_BASE_URL", "https://proxy.example/v1")
    monkeypatch.setenv("LAUNCHKIT_IMAGES", "placeholder")
    assert isinstance(make_images(replace(settings, image_mode="real")), FakeImages)
    monkeypatch.delenv("LAUNCHKIT_IMAGES")
    assert isinstance(make_images(replace(settings, image_mode="real")), RealImages)


def test_proxy_model_tries_a_401_again(settings, monkeypatch):
    """Through the proxy a 401 is the proxy's upstream key having a bad moment, not our key, so the model tries again. A direct key keeps the normal rule."""
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_BASE_URL", "https://proxy.example/v1")
    bad_key = ModelProviderError("Incorrect API key provided", status_code=401)
    model = resolve_model(replace(settings, model="gpt-4.1-mini"), Trace())
    assert model._is_retryable_error(bad_key)
    assert model.retries >= 2
    assert not OpenAIChat(id="gpt-4.1-mini", api_key="sk-test")._is_retryable_error(bad_key)


def test_pictures_ask_for_medium_quality(settings):
    """Pictures ask for medium quality: the proxy never answers a portrait at the default (high) quality, medium comes back in about 30 seconds."""
    assert settings.image_quality == "medium"


def test_real_pictures_send_the_quality_and_try_a_proxy_401_again(settings, tmp_path, monkeypatch):
    """The real image call sends the quality setting, and a 401 from the proxy is tried again instead of ending the picture phase."""
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_BASE_URL", "https://proxy.example/v1")
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            request = httpx.Request("POST", "https://proxy.example/v1/images/generations")
            raise openai.AuthenticationError("Incorrect API key provided", response=httpx.Response(401, request=request), body=None)
        return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(b"png bytes").decode())])

    real = RealImages(replace(settings, image_mode="real"), tmp_path / "outputs")
    monkeypatch.setattr(real, "client", lambda: SimpleNamespace(images=SimpleNamespace(generate=generate)))
    path = real.generate("a misty lakeshore", {"navy": "#1F3A5F"})
    assert path.read_bytes() == b"png bytes"
    assert len(calls) == 2
    assert calls[0]["quality"] == "medium"
