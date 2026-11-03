from agno.db.base import SessionType

from launchkit.agents.main_agent import run_main
from launchkit.memory.long_term import memory_db, memories_for, seed
from launchkit.brands.users import list_logins

from memory_asks import BREEZE


def test_breeze_and_sam_are_at_harbor(settings):
    """Harbor's facts name the Breeze launch, and Sam signs in at Harbor as well as Maya."""
    assert "Breeze" in (settings.workspaces_dir / "harbor" / "facts.md").read_text(encoding="utf-8")
    people = {login["user_id"] for login in list_logins(settings) if login["workspace_id"] == "harbor"}
    assert {"maya", "sam"} <= people


def test_every_run_already_says_who_and_which_thread(settings, trace, request_for, memory):
    """Session 2 already files every run under a person and a thread: the session row is there, the memory table is empty."""
    run_main(request_for(text="Morning!"), settings=settings, model=memory, trace=trace, approve=lambda name, inputs: False)
    db = memory_db(settings, "harbor", "maya")
    session = db.get_session(session_id="harbor:maya:t1:main", session_type=SessionType.AGENT)
    assert session is not None and session.user_id == "maya"
    assert memories_for(db, "harbor", "maya") == []


def test_breeze_in_a_new_chat_buys_a_picture(settings, trace, request_for, memory):
    """Breeze in a fresh chat, no photo, nothing kept: the poster gets a new AI picture, and every check passes."""
    result = run_main(request_for(text=BREEZE), settings=settings, model=memory, trace=trace, approve=lambda name, inputs: False)
    assert result.spec is not None and trace.tool_calls("generate_image")
    assert all(not e.detail["errors"] for e in trace.events if e.kind == "validation")


def test_a_month_of_rows_is_ready_to_seed(settings):
    """samples/memory/harbor_month.yaml seeds thirty rows, Maya's, Sam's and Harbor's."""
    assert seed(settings, "harbor") == 30
    db = memory_db(settings, "harbor", "maya")
    assert len(memories_for(db, "harbor", "maya")) > 0 and len(memories_for(db, "harbor", "sam")) > 0


def test_the_tidal_launch_is_ready_to_recreate():
    """samples/sessions/tidal_launch.txt holds Maya's Tidal messages, and the shoot photo it attaches is in the repo."""
    from launchkit.settings import ROOT

    lines = [line for line in (ROOT / "samples" / "sessions" / "tidal_launch.txt").read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]
    assert len(lines) >= 3 and lines[0].startswith("[attach samples/shoot/tidal-shoot.jpg]")
    assert (ROOT / "samples" / "shoot" / "tidal-shoot.jpg").exists()
