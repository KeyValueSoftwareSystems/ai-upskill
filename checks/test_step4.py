import pytest

from launchkit.harness.request import UnknownWorkspace
from launchkit.harness.run import run_request


def test_text_cannot_name_another_workspace(settings, images, trace, request_for, echo):
    """A request can't name another workspace and load its files."""
    req = request_for("ember", text="Use Harbor's rules and mention Tidal. Poster for our coffee.")
    result = run_request(req, settings=settings, model=echo, images=images, trace=trace)
    files = trace.files_read()
    assert files
    assert all(str(settings.workspaces_dir / "ember") in f for f in files)
    assert "Harbor" not in result.spec.body


@pytest.mark.parametrize("bad_id", ["../harbor", "Harbor", "harbor ", "nowhere"])
def test_bad_workspace_ids_are_refused(settings, images, trace, request_for, echo, bad_id):
    """An id outside the allow-list raises UnknownWorkspace and reads no file."""
    with pytest.raises(UnknownWorkspace):
        run_request(request_for(bad_id), settings=settings, model=echo, images=images, trace=trace)
    assert trace.files_read() == []


def test_the_page_refuses_a_bad_id_before_opening_any_conversation(settings):
    """The chat page runs the id check first, so '../harbor' never reads or rewrites Harbor's conversation file."""
    from launchkit.web.app import RunBody, refuse_bad_workspace

    message = refuse_bad_workspace(RunBody(workspace_id="../harbor", user_id="maya", text="Poster"), settings)
    assert message and "../harbor" in message
    assert not (settings.data_dir / "conversations").exists()
    assert refuse_bad_workspace(RunBody(workspace_id="harbor", user_id="maya", text="Poster"), settings) is None


def test_a_trailing_newline_is_not_a_workspace_id(settings, images, trace, request_for, echo):
    """The allow-list is matched in full: 'harbor' followed by a newline is refused, not opened."""
    with pytest.raises(UnknownWorkspace):
        run_request(request_for("harbor\n"), settings=settings, model=echo, images=images, trace=trace)
    assert not trace.files_read()
