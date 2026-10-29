import json

from PIL import Image

from launchkit.harness.main import build_catalogue, run_main
from launchkit.harness.picture_tools import APPROVED
from launchkit.harness.trace import Trace

NO = lambda name, inputs: False


def test_the_main_agent_holds_the_two_session_1_tools(settings):
    """The main agent starts with the two tools Session 1 built: get_brand_details and generate_image."""
    entries = build_catalogue(settings, Trace(), NO).entries
    assert {"get_brand_details", "generate_image"} <= set(entries)


def test_the_main_agent_answers_a_greeting(settings, trace, request_for):
    """One agent decides what runs: a greeting needs no tool."""
    from launchkit.adapters.fakes import ToolsModel

    result = run_main(request_for(text="Morning!"), settings=settings, model=ToolsModel(), trace=trace, approve=NO)
    assert result.reply and trace.tool_calls() == []


def test_the_approved_poster_and_its_bottle_box_are_ready():
    """The approved Tidal poster is 1200x1200, and the bottle's box is saved next to it for the fakes."""
    assert Image.open(APPROVED).size == (1200, 1200)
    left, top, right, bottom = json.loads(APPROVED.with_suffix(".bottle.json").read_text())["box"]
    assert 0 <= left < right <= 1200 and 0 <= top < bottom <= 1200
