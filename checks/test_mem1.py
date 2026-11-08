"""Session 3, ticket 1: what one saved row may hold. Capture rules and a cheaper model on the memory manager."""

from launchkit.adapters.models import resolve_model
from launchkit.agents.main_agent import build_catalogue, build_main_agent
from launchkit.agents.prompt import ContextBuilder
from launchkit.brands.workspace import load_workspace
from launchkit.memory.long_term import CAPTURE, memory_manager
from launchkit.trace import Trace

NO = lambda name, inputs: False


def test_the_capture_rules_say_what_one_row_holds():
    """One fact per row, people's preferences only, a quoted never-say phrase is a rule, no personal data or secrets, update before add."""
    for rule in ("One fact per memory", "are not memories about the person", "is a rule, not a wish", "phone number", "a token", "update it instead of adding"):
        assert rule in CAPTURE


def test_the_memory_manager_runs_on_a_cheaper_model(settings, monkeypatch):
    """The manager sorts one message into rows; it runs on LAUNCHKIT_MEMORY_MODEL, not the main agent's model."""
    monkeypatch.setenv("LITELLM_API_KEY", "test")
    monkeypatch.setenv("LITELLM_BASE_URL", "http://localhost:9")
    manager = memory_manager(settings, Trace(), resolve_model(settings, Trace()))
    assert manager.memory_capture_instructions == CAPTURE
    assert manager.model.id == settings.memory_model != settings.model


def test_the_main_agent_carries_that_manager(settings, good):
    """The main agent's manager is the one with the capture rules."""
    ws = load_workspace("harbor", settings, Trace())
    agent = build_main_agent(ws, ContextBuilder(settings.budgets), good, settings, Trace(), build_catalogue(settings, Trace(), NO), user_id="maya")
    assert agent.memory_manager is not None and agent.memory_manager.memory_capture_instructions == CAPTURE
