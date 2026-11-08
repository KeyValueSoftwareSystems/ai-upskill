"""Checks for the ready-made plumbing of the Session 3 alternative branch.

These pass on the participant branch, where every slot still holds its placeholder. The tests marked
`answer` describe what a slot does once a participant has built it; they pass on the answer branches only.
"""

import pytest
from agno.db.schemas.memory import UserMemory

from launchkit.memory.store import MemoryStore, memory_section, rows_for
from launchkit.trace import Trace


@pytest.fixture
def store_for(tmp_path):
    """A MemoryStore on a fresh SQLite file, opened as one person at one brand."""

    def make(workspace_id="harbor", user_id="maya", trace=None):
        return MemoryStore(str(tmp_path / "s.db"), workspace_id, user_id, trace or Trace())

    return make


def test_the_door_stamps_scope_author_source_and_date(store_for):
    """ready: a row saved through the door carries its scope, who said it, where it came from and when it became true"""
    store = store_for()
    store.upsert_user_memory(UserMemory(memory="prefers own photos, not AI", user_id="maya", topics=["kind:preference"]))
    row = store.get_user_memories(user_id="maya")[0]
    assert {"kind:preference", "scope:user:maya", "author:maya", "source:chat"} <= set(row.topics)
    assert any(t.startswith("valid_from:") for t in row.topics)


def test_the_door_keeps_a_scope_and_source_already_given(store_for):
    """ready: a row that arrives with its own scope and source keeps them"""
    store = store_for(user_id="research-helper")
    store.upsert_user_memory(UserMemory(memory="a lifetime guarantee sells", user_id="harbor:brand", topics=["scope:brand:harbor", "source:web"]))
    row = store.get_user_memories(user_id="harbor:brand")[0]
    assert "scope:brand:harbor" in row.topics and "source:web" in row.topics
    assert "scope:user:research-helper" not in row.topics


def test_the_door_writes_a_trace_line(store_for):
    """ready: every save through the door leaves a line in the trace"""
    trace = Trace()
    store = store_for(trace=trace)
    store.upsert_user_memory(UserMemory(memory="likes navy backgrounds", user_id="maya", topics=[]))
    assert any(e.kind == "memory_kept" for e in trace.events)
    assert trace.lines()[-1].startswith("memory    kept · user:maya")


def test_a_row_with_no_scope_reads_as_the_users_own(store_for):
    """ready: an old row with no scope topic is read as that user's own, never as shared"""
    store = store_for()
    store.insert_raw(UserMemory(memory="old row", user_id="maya", topics=[]))
    maya_rows = rows_for(store, "harbor", "maya")
    assert [r.memory for r in maya_rows] == ["old row"]


@pytest.mark.answer
def test_rows_for_keeps_one_brands_rows_out_of_another(store_for):
    """build a: Dana's Harbor rows do not load in her Alder chat; a brand row loads for everyone at that brand"""
    store = store_for(user_id="dana")
    store.insert_raw(UserMemory(memory="never say lifetime guarantee", user_id="dana", topics=["scope:user:dana", "brand:harbor"]))
    store.insert_raw(UserMemory(memory="Harbor ships Fridays", user_id="harbor:brand", topics=["scope:brand:harbor"]))
    assert [r.memory for r in rows_for(store, "alder", "dana")] == []
    assert "Harbor ships Fridays" in [r.memory for r in rows_for(store, "harbor", "maya")]


def test_memory_section_has_one_line_per_row_with_its_labels():
    """ready: the memory section of the prompt lists each row with its kind, scope and start date"""
    rows = [UserMemory(memory="prefers own photos", user_id="maya", topics=["kind:preference", "scope:user:maya", "valid_from:2026-02-03"])]
    text = memory_section(rows)
    assert text.splitlines() == ["- prefers own photos  (preference · user:maya · since 2026-02-03)"]


def test_the_prompt_has_brand_facts_and_memory_sections():
    """ready: the prompt gains a brand facts section and a memory section, in that order, before the facts"""
    from launchkit.agents.prompt import HEADERS, ORDER

    assert ORDER == ("rules", "task", "brand_facts", "memory", "facts")
    assert HEADERS["memory"] == "# Memory" and HEADERS["brand_facts"] == "# Brand facts"
