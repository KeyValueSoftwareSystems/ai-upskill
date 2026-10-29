import json

from launchkit.harness.main import build_catalogue, run_main
from launchkit.harness.trace import Trace

NO = lambda name, inputs: False


def catalogue(settings, trace=None):
    return build_catalogue(settings, trace or Trace(), NO)


def test_run_tool_runs_a_catalogue_tool_by_name(settings):
    """run_tool finds a tool by name, runs it with its inputs and records it on the trace."""
    trace = Trace()
    answer = catalogue(settings, trace).make_run_tool()("check_copy", {"headline": "Cold for 24 hours"})
    assert json.loads(answer)["ok"] is True
    assert [e.detail["name"] for e in trace.tool_calls()] == ["check_copy"]


def test_an_unknown_tool_is_named_back(settings):
    """A tool the catalogue does not hold is not guessed at: run_tool says so and points at find_tool."""
    assert "find_tool" in catalogue(settings).make_run_tool()("delete_everything", {})


def test_wrong_inputs_are_named_back_and_nothing_runs(settings):
    """Inputs that do not match the tool's schema come back as a message; the tool never runs."""
    trace = Trace()
    answer = catalogue(settings, trace).make_run_tool()("check_copy", {"tagline": "Cold"})
    assert "Wrong inputs" in answer and trace.tool_calls() == []


def test_every_entry_has_a_note_and_a_read_or_write_flag(settings):
    """Every catalogue entry says when to pick it and whether it reads or writes."""
    assert all(e.note and e.kind in ("read", "write") for e in catalogue(settings).entries.values())


def test_find_tool_gives_back_the_best_few_with_their_notes(settings):
    """find_tool matches each note against the query and gives back only the best few, each with when to pick it."""
    listing = catalogue(settings).make_find_tool()("all the sizes of the approved poster")
    lines = listing.splitlines()
    assert 1 <= len(lines) <= 5
    assert lines[0].startswith("skill resize_image:")


def test_find_tool_hides_the_raw_tools_a_skill_prefers_over(settings):
    """resize_image hides the raw picture tools, so find_tool shows the skill, not crop or scale."""
    listing = catalogue(settings).make_find_tool()("crop or scale the poster to a new size")
    assert "skill resize_image" in listing
    assert "tool crop" not in listing and "tool scale" not in listing


def test_the_main_agent_holds_three_doors(settings):
    """With run_tool built, the main agent holds find_tool, run_skill and run_tool, not every tool."""
    tools = [t.__name__ for t in catalogue(settings).agent_tools()]
    assert tools == ["find_tool", "run_skill", "run_tool"]


def test_the_fixed_note_picks_the_photo_skill(settings, trace, request_for):
    """"Use our shoot photo": with generate_image's note fixed, the main agent loads ingest_image and pays for no picture."""
    from launchkit.adapters.fakes import ToolsModel

    run_main(request_for(text="Use our shoot photo for the story size."), settings=settings, model=ToolsModel(), trace=trace, approve=NO)
    assert [e.detail["arguments"] for e in trace.tool_calls("run_skill")] == [{"name": "ingest_image"}]
    assert trace.tool_calls("generate_image") == []
    assert trace.tool_calls("describe_image") and trace.tool_calls("crop")


def test_the_picture_budget_holds_through_run_tool(settings):
    """The leash still counts generate_image when it runs through run_tool: the 4th picture in a run is refused."""
    trace = Trace()
    run_tool = catalogue(settings, trace).make_run_tool()
    answers = [run_tool("generate_image", {"image_prompt": "a lakeshore at dawn"}) for _ in range(4)]
    assert "refused" in answers[-1] and len(trace.tool_calls("generate_image")) == 4


def test_the_new_asks_work_through_their_skills(settings, request_for):
    """Ready-made: trends come back with addresses through market_research; a voice-over file through voice_over."""
    from launchkit.adapters.fakes import ToolsModel

    trace = Trace()
    run_main(request_for(text="What are hikers talking about this season?"), settings=settings, model=ToolsModel(), trace=trace, approve=NO)
    assert "Address:" in str(trace.tool_calls("search_web")[0].detail["result"])
    trace = Trace()
    run_main(request_for(text="A 10-second voice-over for the story ad.", session_id="t2"), settings=settings, model=ToolsModel(), trace=trace, approve=NO)
    assert trace.tool_calls("check_copy") and "voice-over" in str(trace.tool_calls("text_to_speech")[0].detail["result"])
