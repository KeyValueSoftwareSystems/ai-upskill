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


def test_whatever_saves_memory_uses_that_manager(settings, good, monkeypatch):
    """Until ticket 4 the main agent saves after every run, with this manager. From ticket 4 a note goes through
    save_memory, which builds the same manager when Maya allows it."""
    import launchkit.agents.main_agent as main

    ws = load_workspace("harbor", settings, Trace())
    agent = build_main_agent(ws, ContextBuilder(settings.budgets), good, settings, Trace(), build_catalogue(settings, Trace(), NO), user_id="maya")
    if agent.update_memory_on_run:
        assert agent.memory_manager is not None and agent.memory_manager.memory_capture_instructions == CAPTURE
        return
    made = []
    monkeypatch.setattr(main, "memory_manager", lambda *a: made.append(memory_manager(*a)) or made[-1])
    build_catalogue(settings, Trace(), lambda name, inputs: True, model=good).make_run_tool()("save_memory", {"note": "Maya likes the story size first."})
    assert made and made[0].memory_capture_instructions == CAPTURE


def test_the_fake_memory_model_makes_ticket_1s_mistake_until_the_rules_say_otherwise(settings):
    """fake:memory, the chat page's fallback for ticket 1: Agno's default rules save the never-say phrase as a wish;
    the capture rules make it save the rule."""
    from agno.memory import MemoryManager

    from launchkit.adapters.fakes import MemoryModel
    from launchkit.memory.chat_history import session_db

    ask = "Write the headline. Remember: never say lifetime guarantee, it's on our never-say list."
    default = MemoryManager(model=MemoryModel(), db=session_db(settings))
    default.create_user_memories(message=ask, user_id="maya")
    assert [m.memory for m in default.get_user_memories("maya")] == ["Maya wants headlines to mention the lifetime guarantee."]
    ruled = MemoryManager(model=MemoryModel(), memory_capture_instructions="A phrase they quote and tell you never to use is a rule, not a wish.", db=session_db(settings))
    ruled.create_user_memories(message=ask, user_id="sam")
    assert [m.memory for m in ruled.get_user_memories("sam")] == ['Never use "lifetime guarantee".']
