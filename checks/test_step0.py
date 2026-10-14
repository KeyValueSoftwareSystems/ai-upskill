from launchkit.harness.run import run_request
from launchkit.harness.spec import PosterSpec


def test_skeleton_returns_a_spec(settings, images, trace, request_for, good):
    """The skeleton runs: a request comes back as a typed PosterSpec with a trace."""
    result = run_request(request_for(), settings=settings, model=good, images=images, trace=trace)
    assert isinstance(result.spec, PosterSpec)
    assert [e.kind for e in trace.events].count("model") >= 1


def test_skeleton_skips_the_picture(settings, images, trace, request_for, good):
    """Before step 3 the picture phase is skipped and the trace says so."""
    result = run_request(request_for(), settings=settings, model=good, images=images, trace=trace)
    assert result.image is None
    assert any(e.kind == "picture" and e.detail.get("status") == "skipped" for e in trace.events)


def test_second_turn_remembers_the_first(settings, images, trace, request_for, good):
    """R2: "Make the headline shorter" in the same conversation sees the earlier poster and returns fewer words."""
    first = run_request(request_for(session_id="r2"), settings=settings, model=good, images=images)
    second = run_request(request_for(text="Make the headline shorter.", session_id="r2"), settings=settings, model=good, images=images, trace=trace)
    assert len(second.spec.headline.split()) < len(first.spec.headline.split())
    assert second.history_messages > 0
