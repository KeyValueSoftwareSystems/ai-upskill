from dataclasses import replace

from launchkit.adapters.images import FakeImages, RealImages, make_images
from launchkit.adapters.models import resolve_model
from launchkit.harness.trace import Trace


def test_proxy_key_and_bare_model_id(settings, monkeypatch):
    """With KeyValue's LiteLLM key set, a bare model id like gpt-4.1-mini runs through the proxy."""
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_BASE_URL", "https://proxy.example/v1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    model = resolve_model(replace(settings, model="gpt-4.1-mini"), Trace())
    assert type(model).__name__ == "OpenAIChat"
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
