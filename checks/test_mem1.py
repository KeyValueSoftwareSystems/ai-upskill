"""Session 3, ticket 1: what one saved row may hold. Capture rules and a cheaper model on the memory manager."""

from launchkit.adapters.models import resolve_model
from launchkit.agents.main_agent import build_catalogue
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


def test_every_saved_note_goes_through_that_manager(settings, good, monkeypatch):
    """A note the marketer allows is sorted into rows by the manager with the capture rules (from ticket 2b, through save_memory)."""
    import launchkit.agents.main_agent as main

    made = []
    monkeypatch.setattr(main, "memory_manager", lambda *a: made.append(memory_manager(*a)) or made[-1])
    catalogue = build_catalogue(settings, Trace(), lambda name, inputs: True, model=good)
    catalogue.make_run_tool()("save_memory", {"note": "Maya likes the story size first."})
    assert made and made[0].memory_capture_instructions == CAPTURE
