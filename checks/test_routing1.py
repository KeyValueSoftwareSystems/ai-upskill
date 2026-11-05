import json
from dataclasses import replace

import pytest

from launchkit.adapters.models import Jobs
from launchkit.adapters.ranking import JOBS, rank_list
from launchkit.adapters.routing import route
from launchkit.agents.main_agent import run_main
from launchkit.orchestration.research_team import make_research_entries
from launchkit.tools.catalogue import Skill
from launchkit.trace import Trace


@pytest.fixture
def routed(settings):
    """No pick, nothing switched off, every model a script: the rank list decides."""
    return replace(settings, model="", fake_models=True, disabled_models=frozenset())


def test_a_short_question_becomes_short_text(routed):
    """A long_text ask that ends with a question mark and has twelve words or fewer becomes short_text."""
    assert route("long_text", routed, ask="How many ml is the Breeze?")[0] == "short_text"
    assert route("long_text", routed, ask="Write three headlines for the Breeze feed post.")[0] == "long_text"
    assert route("long_text", routed, ask="Can you write three headlines for the Breeze feed post?")[0] == "short_text"
    assert route("research", routed, ask="What are hikers talking about this week?")[0] == "research"


def test_no_pick_no_pin_means_the_rank_list(routed):
    """With no pick and no pin, the models come in rank order: rank 1 first. That is Auto."""
    job, options = route("research", routed)
    assert [name for name, _ in options] == rank_list("research", routed)
    assert options[0][1] == "rank 1"


def test_mayas_pick_comes_first(routed):
    """Maya's pick goes first, and the trace reason is pick."""
    job, options = route("long_text", routed, pick="gpt-4.1-mini")
    assert options[0] == ("gpt-4.1-mini", "pick")
    assert [name for name, _ in options].count("gpt-4.1-mini") == 1


def test_a_skills_pin_beats_the_rank_list(routed):
    """A skill that pins a model for the job puts it before the rank list, and the reason is skill."""
    skill = Skill("ingest_image", "", "", (), (("vision", "gpt-5.5"),))
    job, options = route("vision", routed, skill=skill)
    assert options[0] == ("gpt-5.5", "skill")
    assert rank_list("vision", routed)[0] != "gpt-5.5"


def test_a_switched_off_model_is_skipped_pick_included(routed):
    """A model that is not enabled is skipped wherever it comes from, Maya's pick included; the next one's reason is fallback."""
    top = rank_list("research", routed)[0]
    job, options = route("research", replace(routed, disabled_models=frozenset({top})))
    assert top not in [name for name, _ in options] and options[0][1] == "fallback"
    job, options = route("long_text", replace(routed, disabled_models=frozenset({"gpt-4.1-mini"})), pick="gpt-4.1-mini")
    assert options[0] == (rank_list("long_text", routed)[0], "fallback")


def test_every_job_gets_a_model(routed):
    """Every routed job gets at least one model to try."""
    for job in JOBS:
        assert route(job, routed)[1]


def test_a_failed_call_moves_to_the_next_model(routed, tmp_path):
    """When the first model's call fails, the caller tries the next one, and the trace says fallback."""
    route("research", routed)  # fails here, at once, until route() is built
    ranks = tmp_path / "ranking.json"
    scores = lambda e: {"eval": e, "latency": 0.5, "cost": 0.5}
    ranks.write_text(json.dumps({"jobs": {"research": {"weights": {"eval": 1, "latency": 0, "cost": 0},
                                                      "models": {"fake:down": scores(0.9), "fake:brief": scores(0.5)}}}}))
    trace = Trace()
    jobs = Jobs(replace(routed, ranking=ranks, fake_models=False), trace)
    research = {e.name: e for e in make_research_entries(None, jobs.settings, trace, jobs)}["research"].fn
    research("How are bottle brands launching this season?")
    routes = [(e.detail["model"], e.detail["reason"]) for e in trace.events if e.kind == "route"]
    assert routes == [("fake:down", "rank 1"), ("fake:brief", "fallback")]


def test_a_launch_turn_routes_each_job(routed, request_for):
    """On the chat path, "How many ml is the Breeze?" runs as short_text, the memory write has its own model, and the scoreboard is in the trace."""
    trace = Trace()
    run_main(request_for(text="How many ml is the Breeze?"), settings=routed, trace=trace, approve=lambda name, inputs: False)
    jobs = {e.detail["job"] for e in trace.events if e.kind == "route"}
    assert {"short_text", "memory_write"} <= jobs and "long_text" not in jobs
    assert [e for e in trace.events if e.kind == "score"] and [e for e in trace.events if e.kind == "quality"]
