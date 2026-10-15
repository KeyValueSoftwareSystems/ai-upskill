import pytest

from launchkit.harness.run import run_request
from launchkit.harness.spec import PosterSpec, SpecError, validate_spec

RULES = {"banned_claims": ["eco-friendly"]}


def test_word_limits_and_banned_claims():
    """The spec validates: headline up to 6 words, subheadline up to 12, body up to 25, no banned claims."""
    bad = PosterSpec(
        headline="one two three four five six seven eight nine",
        subheadline="short",
        body=" ".join(["word"] * 30) + " and it is eco-friendly",
        image_prompt="a bottle on a lakeshore",
    )
    errors = validate_spec(bad, RULES)
    assert any("headline" in e for e in errors)
    assert any("body" in e for e in errors)
    assert any("eco-friendly" in e for e in errors)
    good = PosterSpec(headline="Cold for 24 hours", subheadline="Tidal, built for the shore", body="Keeps drinks cold all day.", image_prompt="a bottle on a lakeshore")
    assert validate_spec(good, RULES) == []


def test_malformed_spec_gets_one_repair_then_a_typed_error(settings, images, trace, request_for, malformed):
    """A malformed spec gets one repair, then a typed error."""
    with pytest.raises(SpecError):
        run_request(request_for(), settings=settings, model=malformed, images=images, trace=trace)
    attempts = [e.detail["attempt"] for e in trace.events if e.kind == "validation"]
    assert attempts == [1, 2]
    assert [e.kind for e in trace.events].count("model") == 2


def test_copy_never_reaches_the_image_prompt(settings, images, trace, request_for, malformed):
    """The copy never reaches the image prompt: no image call, and the leaked headline is caught."""
    with pytest.raises(SpecError) as raised:
        run_request(request_for(), settings=settings, model=malformed, images=images, trace=trace)
    assert trace.tool_calls("generate_image") == []
    assert images.calls == []
    assert any("image_prompt" in e for e in raised.value.errors)
