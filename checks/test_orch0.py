from launchkit.adapters.fakes import COMPETITORS
from launchkit.harness.agent import RESEARCH_TASK
from launchkit.harness.board import Board
from launchkit.harness.main import build_catalogue, run_main
from launchkit.harness.trace import Trace
from launchkit.harness.web import PAGES_DIR, make_search_web


def test_the_catalogue_holds_search_and_the_board(settings):
    """The main agent's catalogue holds search_web and Maya's board, each marked read or write."""
    entries = build_catalogue(settings, Trace(), lambda name, inputs: False, Board()).entries
    assert {"search_web", "read_card", "attach_files", "update_status"} <= set(entries)


def test_every_competitor_has_two_saved_pages(settings):
    """Every competitor on the Tidal card has two saved pages, and search_web finds both."""
    search_web = make_search_web(settings)
    for name in COMPETITORS[:5]:
        found = search_web(f"{name} bottle launch")
        assert found.count("Address: ") == 2 and found.count(name) >= 2
    assert len(list(PAGES_DIR.glob("*.md"))) == 10


def test_the_main_agent_answers(settings, trace, request_for, brief):
    """The main agent runs on the fakes and answers a greeting without any tool."""
    result = run_main(request_for(text="Morning!"), settings=settings, model=brief, trace=trace, approve=lambda name, inputs: False)
    assert result.reply and trace.tool_calls() == []


def test_the_research_instructions_are_ready_made():
    """RESEARCH_TASK is written: search, read, reply with a short report and its sources."""
    assert "search_web" in RESEARCH_TASK and "report" in RESEARCH_TASK
