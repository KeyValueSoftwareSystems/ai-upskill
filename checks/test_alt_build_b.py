"""Build B, who writes, who reads, how long: tickets 4, 5 and 6. These pass once the slots are built, on the answer branches.

The fork tests select the path the answer branch took through FORK in conftest.
"""

import pytest
from agno.db.schemas.memory import UserMemory

from launchkit.memory.store import MemoryStore
from launchkit.memory.write_door import decide_save
from launchkit.settings import settings
from launchkit.trace import Trace

pytestmark = pytest.mark.answer


def test_a_row_from_a_web_page_never_reaches_memory(tmp_path):
    """build b, ticket 4: a save whose source is a web page is refused at the door and leaves a trace line"""
    trace = Trace()
    store = MemoryStore(str(tmp_path / "s.db"), "harbor", "research-helper", trace, decide=lambda text, topics: decide_save(text, topics, approve=lambda n, i: "Just me", settings=settings))
    store.upsert_user_memory(UserMemory(memory="a lifetime guarantee sells", user_id="harbor:brand", topics=["scope:brand:harbor", "source:web"]))
    assert store.get_user_memories(user_id="harbor:brand") == []
    assert any(e.kind == "memory_refused" for e in trace.events)


def test_the_research_helper_has_no_save_tool(tmp_path):
    """build b, ticket 4: the helper keeps search_web and loses its save tool"""
    from dataclasses import replace

    from launchkit.adapters.fakes import GoodModel
    from launchkit.orchestration.research_team import build_research_agent

    store = MemoryStore(str(tmp_path / "s.db"), "harbor", "research-helper", Trace())
    agent = build_research_agent(GoodModel(), replace(settings, search="saved"), Trace(), store=store)
    assert [getattr(t, "__name__", "") for t in agent.tools] == ["search_web"]


@pytest.mark.fork_a
def test_the_ask_door_maps_the_three_answers():
    """build b, fork 1 path A: Just me keeps it for the person, Everyone keeps it for the brand, Don't keep refuses"""
    answers = iter(["Just me", "Everyone at the brand", "Don't keep"])
    approve = lambda name, inputs: next(answers)  # noqa: E731
    assert decide_save("prefers own photos", ["kind:preference"], approve, settings) == (True, "user")
    assert decide_save("we never say lifetime guarantee", ["kind:preference"], approve, settings) == (True, "brand")
    assert decide_save("yes, attach them", ["kind:fact"], approve, settings) == (False, None)


@pytest.mark.fork_b
def test_the_confidence_door_keeps_a_row_at_point_seven(monkeypatch):
    """build b, fork 1 path B: a row the model is at least 0.7 sure of is kept without asking; a less sure one is not"""
    from launchkit.memory import write_door

    monkeypatch.setattr(write_door, "confidence", lambda text, settings: 0.9 if "never" in text or "prefer" in text else 0.4)
    never_asked = lambda name, inputs: pytest.fail("the confidence door must not ask")  # noqa: E731
    assert decide_save("prefers own photos", ["kind:preference"], never_asked, settings).keep is True
    assert decide_save("yes, attach them", ["kind:fact"], never_asked, settings).keep is False


def test_the_index_has_one_line_per_topic_and_is_shorter(tmp_path):
    """build b, ticket 5: the index names each topic once with its count and recall call, and costs less than the full list"""
    from launchkit.memory.index import memory_index
    from launchkit.memory.store import memory_section, memory_tokens, rows_for

    store = MemoryStore(str(tmp_path / "s.db"), "harbor", "maya", Trace())
    for n in range(6):
        store.insert_raw(UserMemory(memory=f"navy background for size {n}", user_id="maya", topics=["kind:preference", "topic:navy", "valid_from:2026-05-01"]))
    store.insert_raw(UserMemory(memory="prefers own shoot photos", user_id="maya", topics=["kind:preference", "topic:photography", "valid_from:2026-04-22"]))
    rows = rows_for(store, "harbor", "maya")
    index = memory_index(rows)
    assert index.splitlines() == ['- navy: 6 rows · recall("navy")', '- photography: 1 row · recall("photography")']
    assert all(len(line) <= 80 for line in index.splitlines())
    assert memory_tokens(index) < memory_tokens(memory_section(rows))


def test_recall_returns_one_topics_rows_in_full(tmp_path):
    """build b, ticket 5: recall("photography") returns only that topic's rows, and an unknown topic lists the topics that exist"""
    from launchkit.memory.index import recall

    store = MemoryStore(str(tmp_path / "s.db"), "harbor", "maya", Trace())
    store.insert_raw(UserMemory(memory="prefers own shoot photos", user_id="maya", topics=["kind:preference", "topic:photography"]))
    store.insert_raw(UserMemory(memory="navy backgrounds", user_id="maya", topics=["kind:preference", "topic:navy"]))
    rows = store.get_user_memories(user_id="maya")
    assert recall(rows, "photography") == "- prefers own shoot photos  (preference)"
    assert recall(rows, "lids") == "No rows about lids. Topics that exist: navy, photography."


def test_forget_reaches_every_copy_and_nobody_elses_rows(tmp_path):
    """build b, ticket 6: forgetting a customer's number clears the row, the chat summary and the shared learning that hold it, and leaves other people's rows alone"""
    import shutil
    from datetime import datetime

    from agno.session.agent import AgentSession
    from agno.session.summary import SessionSummary

    from launchkit.memory.forget import forget
    from launchkit.settings import ROOT

    copy = tmp_path / "s.db"
    shutil.copyfile(ROOT / "samples" / "memory" / "seed.db", copy)
    store = MemoryStore(str(copy), "harbor", "maya", Trace())
    store.insert_raw(UserMemory(memory="the launch customer, 555-0142, prefers mornings", user_id="harbor:brand", topics=["scope:brand:harbor", "source:chat"]))
    store.upsert_session(AgentSession(session_id="harbor:dana:x:main", user_id="dana", agent_id="main", summary=SessionSummary(summary="Dana asked about 555-0142 too", updated_at=datetime(2026, 10, 3))))
    dana_before = len(store.get_user_memories(user_id="dana"))
    result = forget(store, "harbor", "maya", "555-0142")
    assert result == {"memories": 1, "summaries": 2, "learnings": 1}
    assert not any("555-0142" in (s.summary.summary if s.summary else "") for s in store.get_sessions())
    assert store.get_user_memories(user_id="harbor:brand") == [] or not any("555-0142" in r.memory for r in store.get_user_memories(user_id="harbor:brand"))
    assert len(store.get_user_memories(user_id="dana")) == dana_before


def test_retention_prunes_rows_older_than_the_limit(tmp_path):
    """build b, ticket 5: rows older than the limit go; newer rows and brand rows stay"""
    from datetime import date

    from launchkit.memory.retention import prune

    store = MemoryStore(str(tmp_path / "s.db"), "harbor", "maya", Trace())
    store.insert_raw(UserMemory(memory="old", user_id="maya", topics=["valid_from:2025-01-01", "scope:user:maya"]))
    store.insert_raw(UserMemory(memory="new", user_id="maya", topics=["valid_from:2026-10-01", "scope:user:maya"]))
    store.insert_raw(UserMemory(memory="brand rule", user_id="harbor:brand", topics=["valid_from:2025-01-01", "scope:brand:harbor"]))
    assert prune(store, "harbor", date(2026, 11, 1), max_age_days=180) == 1
    assert [r.memory for r in store.get_user_memories(user_id="maya")] == ["new"]
    assert len(store.get_user_memories(user_id="harbor:brand")) == 1
