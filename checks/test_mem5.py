"""Session 3, ticket 5: how much is read, and for how long it is kept."""

import time

from launchkit.agents.main_agent import build_catalogue, build_main_agent, run_main
from launchkit.agents.prompt import ContextBuilder
from launchkit.brands.workspace import load_workspace
from launchkit.memory.long_term import memory_manager, user_memories
from launchkit.memory.memory_view import reset_to_snapshot
from launchkit.memory.retention import retain
from launchkit.memory.chat_history import session_db
from launchkit.trace import Trace

NO = lambda name, inputs: False
QUEUE_FILLED = 1793606400  # 2026-11-02 08:00 UTC, the snapshot's morning


def test_the_main_agent_keeps_three_turns_and_a_summary(settings, monkeypatch):
    """The last 3 turns word for word, and a running session summary for the rest, written by the cheaper model."""
    from launchkit.adapters.models import resolve_model

    monkeypatch.setenv("LITELLM_API_KEY", "test")
    monkeypatch.setenv("LITELLM_BASE_URL", "http://localhost:9")
    ws = load_workspace("harbor", settings, Trace())
    agent = build_main_agent(ws, ContextBuilder(settings.budgets), resolve_model(settings, Trace()), settings, Trace(), build_catalogue(settings, Trace(), NO), user_id="maya")
    assert agent.num_history_runs == 3 and agent.enable_session_summaries
    assert agent.session_summary_manager.model.id == settings.memory_model


def test_the_summary_is_put_in_the_prompt(settings, good, request_for):
    """Agno skips the summary when an agent writes its own system message, so LaunchKit adds it to the memory section."""
    from agno.session.summary import SessionSummary
    from agno.session.agent import AgentSession

    session_db(settings).upsert_session(AgentSession(session_id="harbor:maya:t1:main", user_id="maya", summary=SessionSummary(summary="The Tidal brief: four tasks, sizes due Friday.")))
    ws = load_workspace("harbor", settings, Trace())
    agent = build_main_agent(ws, ContextBuilder(settings.budgets), good, settings, Trace(), build_catalogue(settings, Trace(), NO), user_id="maya", session_id="harbor:maya:t1:main")
    assert "sizes due Friday" in agent.system_message


def test_retention_prunes_by_age_and_writes_nothing_without_apply(settings, good):
    """The power user's 600 rows: a dry run reports, writes nothing; --apply deletes the rows older than 90 days."""
    reset_to_snapshot(settings)
    manager = memory_manager(settings, Trace(), good)
    dry = {r["user"]: r for r in retain(manager, 90, 10_000, apply=False, now=QUEUE_FILLED)}
    assert dry["power-user"]["before"] == 600 and 0 < dry["power-user"]["pruned"] < 600
    assert len(user_memories(manager.db, "power-user")) == 600
    retain(manager, 90, 10_000, apply=True, now=QUEUE_FILLED)
    left = user_memories(manager.db, "power-user")
    assert len(left) == 600 - dry["power-user"]["pruned"] and min(m.updated_at for m in left) >= QUEUE_FILLED - 90 * 86_400


def test_retention_never_runs_in_a_turn(settings, good, request_for):
    """A turn reads memory and never prunes it: the job is scheduled, not per run."""
    reset_to_snapshot(settings)
    run_main(request_for(user_id="power-user", text="Morning!"), settings=settings, model=good, approve=NO)
    assert len(user_memories(session_db(settings), "power-user")) == 600


def test_the_memory_tab_shows_a_conversation_with_no_summary_yet(settings, good, request_for):
    """Seen on the chat page: a conversation Agno saved before its first summary broke the Memory tab."""
    from launchkit.memory.memory_view import memory_view

    reset_to_snapshot(settings)
    run_main(request_for(text="Morning!"), settings=settings, model=good, approve=NO)
    view = memory_view(settings, "maya", "harbor")
    assert view["summaries"] == [] and len(view["memories"]) == 39
