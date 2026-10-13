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
