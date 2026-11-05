import json
from dataclasses import replace

from launchkit.adapters.ranking import JOBS, rank_list, ranking, total
from launchkit.agents.main_agent import run_main
from launchkit.settings import ROOT, Settings
from launchkit.tools.catalogue import load_skills
from launchkit.trace import Trace

BREEZE = "Breeze launches next month. Same as Tidal: concepts, then every size."


def test_every_job_has_a_ranked_list(settings):
    """launchkit/ranking.json has a list for each routed job, every score from 0 to 1, and each job's weights."""
    lists = ranking(settings)
    assert set(JOBS) <= set(lists)
    for job in JOBS:
        assert set(lists[job]["weights"]) == {"eval", "latency", "cost"}
        for scores in lists[job]["models"].values():
            assert all(0 <= scores[k] <= 1 for k in ("eval", "latency", "cost"))


def test_the_rank_list_is_best_total_first(settings):
    """A job's rank list is its models by weighted total, highest first, so the same models rank differently per job."""
    for job in JOBS:
        entry = ranking(settings)[job]
        totals = [total(entry["models"][name], entry["weights"]) for name in rank_list(job, settings)]
        assert totals == sorted(totals, reverse=True)
    assert rank_list("long_text", settings)[0] != rank_list("short_text", settings)[0]


def test_ingest_image_pins_a_vision_model(settings):
    """ingest_image's skill.md pins the vision job, in one line, to a model on the vision list."""
    pins = dict(load_skills()["ingest_image"].pins)
    assert pins.get("vision") in ranking(settings)["vision"]["models"]


def test_the_cap_photo_is_ready():
    """samples/shoot/breeze-cap.jpg, the Breeze shoot with another brand's logo on a cap, is in the repo with its saved answers."""
    shoot = ROOT / "samples" / "shoot"
    assert (shoot / "breeze-cap.jpg").exists()
    assert json.loads((shoot / "breeze-cap.describe.json").read_text())["other_brand"] is True
    assert "box" in json.loads((shoot / "breeze-cap.bottle.json").read_text())


def test_switched_off_models_are_read_from_env(monkeypatch):
    """LAUNCHKIT_DISABLED_MODELS is a comma-separated list of models switched off inside LaunchKit."""
    monkeypatch.setenv("LAUNCHKIT_DISABLED_MODELS", "gpt-5.5, gpt-4.1-mini")
    assert Settings().disabled_models == {"gpt-5.5", "gpt-4.1-mini"}


def test_the_scoreboard_adds_up_by_model():
    """Trace.bill() groups every call by model, with its jobs, calls, tokens, seconds and dollars when priced."""
    trace = Trace()
    trace.call("long_text", "gpt-5.5", 4.0, 3000, 0, 400)
    trace.call("memory_write", "gpt-5.5", 1.0, 900, 0, 50)
    trace.call("short_text", "gpt-5-nano", 0.8, 700, 0, 30)
    rows = {row["model"]: row for row in trace.bill()}
    assert rows["gpt-5.5"]["jobs"] == ["long_text", "memory_write"] and rows["gpt-5.5"]["calls"] == 2
    assert rows["gpt-5.5"]["seconds"] == 5.0 and rows["gpt-5.5"]["usd"] > rows["gpt-5-nano"]["usd"] > 0


def test_before_routing_every_job_runs_on_one_model(settings, request_for):
    """Before route() is built, the whole Breeze turn runs on one model: no route lines, one scoreboard row."""
    from launchkit.adapters.routing import route

    if not getattr(route, "todo", False):
        return  # route() is built on this branch: routing1 checks it
    offline = replace(settings, model="", fake_models=True, disabled_models=frozenset())
    trace = Trace()
    run_main(request_for(text=BREEZE), settings=offline, trace=trace, approve=lambda name, inputs: False)
    assert not [e for e in trace.events if e.kind == "route"]
    assert len([e for e in trace.events if e.kind == "score"]) == 1
