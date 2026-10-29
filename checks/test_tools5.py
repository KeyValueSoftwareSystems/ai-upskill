from launchkit.harness.board import LAST_WEEK, Board
from launchkit.harness.main import build_catalogue, run_main
from launchkit.harness.trace import Trace


def test_a_write_asks_maya_and_a_no_stops_it(settings):
    """Every write through run_tool asks Maya first, with what it is about to change. A no means the tool never runs."""
    asked, board, trace = [], Board(), Trace()
    run_tool = build_catalogue(settings, trace, lambda name, inputs: asked.append((name, inputs)) or False, board).make_run_tool()
    answer = run_tool("update_status", {"card": "tidal", "status": "Ready for review"})
    assert asked == [("update_status", {"card": "tidal", "status": "Ready for review"})] and "did not allow" in answer
    assert board.cards["tidal"]["status"] == "Brief ready"
    assert [e.kind for e in trace.tool_calls()] == ["refused"]


def test_a_yes_lets_the_write_through(settings):
    """A yes runs the write."""
    board = Board()
    run_tool = build_catalogue(settings, Trace(), lambda name, inputs: True, board).make_run_tool()
    run_tool("update_status", {"card": "tidal", "status": "Ready for review"})
    assert board.cards["tidal"]["status"] == "Ready for review"


def test_a_read_never_asks(settings):
    """Reads run without asking: the card, a search, a picture tool."""
    asked = []
    run_tool = build_catalogue(settings, Trace(), lambda name, inputs: asked.append(name) or True, Board()).make_run_tool()
    run_tool("read_card", {"card": "tidal"})
    run_tool("detect_focal_point", {})
    assert asked == []


def test_last_weeks_approved_files_survive_the_cleanup(settings, request_for):
    """Put the new sizes on the Tidal card: Maya says yes to attaching and moving the card, no to removing files.
    Last week's approved files stay on the card."""
    from launchkit.adapters.fakes import ToolsModel

    board, trace = Board(), Trace()
    maya = lambda name, inputs: name != "remove_files"
    run_main(request_for(text="Put the new sizes on the Tidal card."), settings=settings, model=ToolsModel(), trace=trace, approve=maya, board=board)
    assert all(f in board.cards["tidal"]["files"] for f in LAST_WEEK)
    assert board.cards["tidal"]["status"] == "Ready for review"
    assert [e.kind for e in trace.tool_calls("remove_files")] == ["refused"]
