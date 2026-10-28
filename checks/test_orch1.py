from launchkit.harness.board import Board
from launchkit.harness.catalogue import load_skills
from launchkit.harness.main import build_catalogue, run_main
from launchkit.harness.trace import Trace

ASK = "How are Northline, Ridgeway, Stillwater, Kestrel and Hollowmere launching bottles this season? One paragraph each."
FIVE = ["Northline", "Ridgeway", "Stillwater", "Kestrel", "Hollowmere"]


def test_the_skill_exists_and_says_when_to_pick_it():
    """skills/competitor_research/skill.md exists, and its 'Pick me when:' line is about competitors."""
    skill = load_skills().get("competitor_research")
    assert skill is not None, "no launchkit/skills/competitor_research/skill.md yet"
    assert "competitor" in skill.note.lower()


def test_find_tool_shows_the_skill(settings):
    """find_tool lists the skill with its note, so the main agent can pick it."""
    listing = build_catalogue(settings, Trace(), lambda name, inputs: False, Board()).make_find_tool()("competitors")
    assert "skill competitor_research:" in listing


def test_the_skill_names_the_tool_to_use():
    """The skill's steps name the tool the agent calls, and ask for message, channels and what to avoid copying."""
    text = load_skills()["competitor_research"].text.lower()
    assert "search_web" in text or "research_many" in text
    assert all(word in text for word in ("message", "channels", "avoid"))


def test_the_main_agent_loads_the_skill_and_researches_all_five(settings, trace, request_for, brief):
    """Asked about the five competitors, the main agent loads the skill, every competitor's pages get read, and the answer covers all five."""
    result = run_main(request_for(text=ASK), settings=settings, model=brief, trace=trace, approve=lambda name, inputs: False)
    assert [e.detail["arguments"] for e in trace.tool_calls("run_skill")] == [{"name": "competitor_research"}]
    searched = " ".join(str(e.detail["arguments"]) for e in trace.tool_calls("search_web"))
    assert all(name in searched for name in FIVE)
    assert all(name in result.reply for name in FIVE)
