"""Build C, which model does each job: ticket 8. These pass once route() and on_failure are built, on the answer branches."""

from dataclasses import replace

import pytest
from agno.exceptions import ModelProviderError

from launchkit.adapters.jobs import DownModel, Jobs
from launchkit.adapters.routing import on_failure, route
from launchkit.settings import settings
from launchkit.trace import Trace

pytestmark = pytest.mark.answer


def test_the_rank_list_decides_when_nothing_else_is_set(ranking_file):
    """build c: with no pick and no pin, route() returns the job's models best first, each with its rank as the reason"""
    current = replace(settings, model="", ranking=ranking_file)
    job, choices = route("long_text", current)
    assert job == "long_text"
    assert [m for m, _ in choices] == ["strong-model", "mid-model", "cheap-model"]
    assert [r for _, r in choices] == ["rank 1", "rank 2", "rank 3"]


def test_the_users_pick_comes_first(ranking_file):
    """build c: a model the user picked is tried before the rank list, and the trace reason says so"""
    current = replace(settings, model="", ranking=ranking_file)
    _, choices = route("long_text", current, pick="mid-model")
    assert choices[0] == ("mid-model", "pick")


def test_a_skills_pin_beats_the_rank_list(ranking_file):
    """build c: a model a skill pins for a job comes before the rank list"""
    current = replace(settings, model="", ranking=ranking_file)
    _, choices = route("vision", current, skill="see-model")
    assert choices[0] == ("see-model", "skill")


def test_a_disabled_model_is_left_out(ranking_file):
    """build c: a model in LAUNCHKIT_DISABLED_MODELS is not on the list at all"""
    current = replace(settings, model="", ranking=ranking_file, disabled_models=("strong-model",))
    _, choices = route("long_text", current)
    assert [m for m, _ in choices] == ["mid-model", "cheap-model"]


@pytest.mark.fork_a
def test_path_a_moves_to_the_next_model_when_one_is_down(ranking_file):
    """build c, fork 2 path A: a failed call moves to the next model on the list and the trace says fallback"""
    current = replace(settings, model="", ranking=ranking_file)
    assert on_failure("long_text", tried=["strong-model"], remaining=["mid-model", "cheap-model"], error=ModelProviderError("down")) == "mid-model"
    trace = Trace()
    jobs = Jobs(current, trace, models={"strong-model": DownModel(), "mid-model": _answers("ok")})
    assert jobs.in_order("long_text", lambda model: model.reply()) == "ok"
    assert any(e.kind == "route" and e.detail["reason"] == "fallback" for e in trace.events)


@pytest.mark.fork_b
def test_path_b_retries_once_then_stops_with_a_clear_error(ranking_file):
    """build c, fork 2 path B: a failed call is retried on the same model once, then the run stops with a clear error"""
    current = replace(settings, model="", ranking=ranking_file)
    assert on_failure("long_text", tried=["strong-model"], remaining=["mid-model"], error=ModelProviderError("down")) == "strong-model"
    assert on_failure("long_text", tried=["strong-model", "strong-model"], remaining=["mid-model"], error=ModelProviderError("down")) is None
    jobs = Jobs(current, Trace(), models={"strong-model": DownModel()})
    with pytest.raises(ModelProviderError, match="strong-model"):
        jobs.in_order("long_text", lambda model: model.reply())


class _answers:
    def __init__(self, text):
        self.id = "mid-model"
        self.text = text

    def reply(self):
        return self.text
