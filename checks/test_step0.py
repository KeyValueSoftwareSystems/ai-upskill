from launchkit.harness.run import run_request
from launchkit.harness.trace import Trace
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


def test_a_greeting_gets_a_reply_not_a_poster(settings, images, trace, request_for, good):
    """A plain message like "hi" gets a short reply in the brand's voice: no spec, no picture."""
    result = run_request(request_for(text="hi"), settings=settings, model=good, images=images, trace=trace)
    assert result.reply
    assert result.spec is None
    assert result.image is None
    assert not [e for e in trace.events if e.kind == "picture"]


def test_logins_come_from_each_workspace(settings):
    """The sign-in list is built from every workspace's users.yaml, people not ids."""
    from launchkit.harness.users import list_logins

    logins = list_logins(settings)
    labels = {login["label"] for login in logins}
    assert "Maya · Harbor" in labels
    assert "Jonas · Ember Coffee Co." in labels
    maya = next(login for login in logins if login["user_id"] == "maya")
    assert maya["workspace_id"] == "harbor"


def test_conversations_are_per_user_per_workspace(settings, images, trace, request_for, good):
    """Two people at the same brand never share a conversation, even with the same conversation id."""
    run_request(request_for(user_id="maya", session_id="c1"), settings=settings, model=good, images=images)
    sam = run_request(request_for(text="Make the headline shorter.", user_id="sam", session_id="c1"), settings=settings, model=good, images=images, trace=trace)
    assert sam.history_messages == 0
    assert len(sam.spec.headline.split()) == 4


def test_prompt_line_names_only_the_sections_with_text(settings, images, trace, request_for, good):
    """The prompt line on the trace lists the sections that carry text; an empty facts section is not mentioned."""
    run_request(request_for(), settings=settings, model=good, images=images, trace=trace)
    prompt_lines = [line for line in trace.lines() if line.startswith("prompt")]
    assert prompt_lines and "task" in prompt_lines[0]
    assert "facts" not in prompt_lines[0] and "empty" not in prompt_lines[0]


def test_an_unchanged_image_prompt_reuses_the_picture(settings, images, trace, request_for, good, tmp_path):
    """When the new spec's image prompt is the same as the previous turn's, the previous picture is kept and no picture phase runs; a different prompt is not reused."""
    first = run_request(request_for(), settings=settings, model=good, images=images, trace=Trace())
    kept = tmp_path / "kept.png"
    kept.write_bytes(b"png")
    previous = {"image_prompt": first.spec.image_prompt, "image": str(kept)}
    again = run_request(request_for(), settings=settings, model=good, images=images, trace=trace, previous=previous)
    assert again.image == kept
    assert any(e.kind == "picture" and e.detail["status"] == "reused" for e in trace.events)
    assert "reused" in " ".join(trace.lines())
    other = run_request(request_for(), settings=settings, model=good, images=images, trace=Trace(), previous={"image_prompt": "something else", "image": str(kept)})
    assert other.image != kept
