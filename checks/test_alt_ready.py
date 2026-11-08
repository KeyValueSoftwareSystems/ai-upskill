"""Checks for the ready-made plumbing of the Session 3 alternative branch.

These pass on the participant branch, where every slot still holds its placeholder. The tests marked
`placeholder` pin how an unbuilt slot behaves and are left out on the answer branches; the tests marked
`answer` (in the build files) describe what a slot does once built and pass on the answer branches only.
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


@pytest.fixture
def facts_for(tmp_path):
    """A BrandFacts table on a fresh SQLite file."""
    from launchkit.memory.brand_facts import BrandFacts

    return BrandFacts(str(tmp_path / "f.db"))


def test_a_brand_fact_is_read_back_for_its_brand_only(facts_for):
    """ready: a recorded brand fact comes back for its own brand and for no other"""
    from datetime import date

    facts_for.record("harbor", "warranty", "5 years", source="chat", valid_from=date(2026, 10, 1))
    today = date(2026, 11, 1)
    assert [(f.subject, f.value) for f in facts_for.current("harbor", today)] == [("warranty", "5 years")]
    assert facts_for.current("alder", today) == []


@pytest.mark.placeholder
def test_placeholder_keeps_both_warranty_rows_open(facts_for):
    """ready: on the participant branch two rows for one subject both stay current, which is ticket 2 as the room sees it"""
    from datetime import date

    facts_for.record("harbor", "warranty", "2 years", source="chat", valid_from=date(2026, 2, 1))
    facts_for.record("harbor", "warranty", "5 years", source="chat", valid_from=date(2026, 10, 1))
    values = sorted(f.value for f in facts_for.current("harbor", date(2026, 11, 1)) if f.subject == "warranty")
    assert values == ["2 years", "5 years"]


def test_brand_facts_section_lists_each_fact_with_its_date(facts_for):
    """ready: the brand facts section of the prompt has one line per fact with the date it became true"""
    from datetime import date

    from launchkit.memory.brand_facts import brand_facts_section

    facts_for.record("harbor", "warranty", "5 years", source="chat", valid_from=date(2026, 10, 1))
    assert brand_facts_section(facts_for.current("harbor", date(2026, 11, 1))) == "- warranty: 5 years  (since 2026-10-01)"


@pytest.fixture
def page(tmp_path, monkeypatch):
    """The chat page's app, pointed at a copy of the seeded database."""
    import shutil
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from launchkit.settings import ROOT, settings
    from launchkit.web import app as web

    data = tmp_path / "data"
    data.mkdir()
    shutil.copyfile(ROOT / "samples" / "memory" / "seed.db", data / "sessions.db")
    monkeypatch.setattr(web, "settings", replace(settings, data_dir=data))
    return TestClient(web.app)


def test_the_memory_panel_lists_a_persons_rows_with_their_labels(page):
    """ready: GET /memories/{brand}/{person} returns each row with its kind, scope, source and date, the brand facts, and the token count"""
    body = page.get("/memories/harbor/maya").json()
    row = next(r for r in body["rows"] if "shoot photos" in r["memory"])
    assert row["kind"] == "preference" and row["scope"] == "user:maya" and row["source"] == "chat" and row["since"] == "2026-04-22"
    assert {"id", "memory", "kind", "scope", "source", "since", "author"} <= set(row)
    assert any(f["subject"] == "warranty" for f in body["brand_facts"])
    assert body["tokens"] > 0


def test_forget_removes_one_row_from_the_panel(page):
    """ready: DELETE /memories/{brand}/{id} removes that row and nothing else"""
    before = page.get("/memories/harbor/maya").json()["rows"]
    target = next(r for r in before if "555-0142" in r["memory"])
    assert page.delete(f"/memories/harbor/{target['id']}").json() == {"deleted": True}
    after = page.get("/memories/harbor/maya").json()["rows"]
    assert len(after) == len(before) - 1 and all(r["id"] != target["id"] for r in after)


def test_an_answer_can_carry_a_choice(page):
    """ready: POST /answer/{id} accepts a choice, and the page's question gets that choice back"""
    import threading

    from launchkit.web import app as web

    ask_id = "t1"
    answered, answer = threading.Event(), {"allow": False, "choice": None}
    web.ASKS[ask_id] = (answered, answer)
    assert page.post(f"/answer/{ask_id}", json={"allow": True, "choice": "Everyone at the brand"}).json() == {"ok": True}
    assert answer == {"allow": True, "choice": "Everyone at the brand"}


@pytest.mark.placeholder
def test_the_placeholder_door_keeps_everything():
    """ready: on the participant branch the write door keeps every row and never asks"""
    from launchkit.memory.write_door import decide_save
    from launchkit.settings import settings

    asked = []
    decision = decide_save("the customer is on 555-0142", ["kind:fact"], approve=lambda name, inputs: asked.append(name) or "Don't keep", settings=settings)
    assert decision.keep is True and decision.scope is None and asked == []


@pytest.mark.placeholder
def test_the_research_helper_can_save_a_learning_everyone_reads(tmp_path):
    """ready: the research helper has a save tool, and what it saves lands as a brand row from the web"""
    from launchkit.adapters.fakes import GoodModel
    from launchkit.memory.store import MemoryStore
    from launchkit.orchestration.research_team import build_research_agent
    from launchkit.settings import settings as base
    from dataclasses import replace

    store = MemoryStore(str(tmp_path / "s.db"), "harbor", "research-helper", Trace())
    agent = build_research_agent(GoodModel(), replace(base, search="saved"), Trace(), store=store)
    save = next(t for t in agent.tools if getattr(t, "__name__", "") == "save_learning")
    save("a lifetime guarantee sells")
    row = store.get_user_memories(user_id="harbor:brand")[0]
    assert row.memory == "a lifetime guarantee sells"
    assert {"scope:brand:harbor", "source:web", "author:research-helper"} <= set(row.topics)


@pytest.mark.placeholder
def test_the_placeholder_index_is_every_row_in_full(store_for):
    """ready: on the participant branch the memory index is the full list of rows, so the prompt grows with every save"""
    from launchkit.memory.index import memory_index

    store = store_for()
    for n in range(3):
        store.insert_raw(UserMemory(memory=f"row {n}", user_id="maya", topics=["kind:fact", "topic:navy", "valid_from:2026-05-01"]))
    rows = rows_for(store, "harbor", "maya")
    assert memory_index(rows) == memory_section(rows)


def test_recall_is_a_read_tool_in_the_catalogue(tmp_path):
    """ready: the main agent can call recall(topic) through run_tool; it is a read, so nobody is asked"""
    from launchkit.memory.index import recall_entry

    store = MemoryStore(str(tmp_path / "s.db"), "harbor", "maya", Trace())
    entry = recall_entry(store, "harbor", "maya")
    assert entry.name == "recall" and entry.kind == "read"
    assert "no rows" in entry.fn("photography").lower()


@pytest.mark.placeholder
def test_the_placeholder_retention_prunes_nothing(store_for):
    """ready: on the participant branch retention removes no row, however old"""
    from datetime import date

    from launchkit.memory.retention import prune

    store = store_for()
    store.insert_raw(UserMemory(memory="old row", user_id="maya", topics=["valid_from:2025-01-01"]))
    assert prune(store, "harbor", date(2026, 11, 1), max_age_days=180) == 0
    assert len(store.get_user_memories(user_id="maya")) == 1


@pytest.mark.placeholder
def test_the_placeholder_forget_misses_the_copies(page, tmp_path):
    """ready: on the participant branch forgetting a phone number removes Maya's row and leaves the copy in the chat summary"""
    from launchkit.memory.forget import forget
    from launchkit.memory.store import MemoryStore
    from launchkit.web import app as web

    store = MemoryStore(str(web.settings.data_dir / "sessions.db"), "harbor", "maya", Trace())
    result = forget(store, "harbor", "maya", "555-0142")
    assert result["memories"] == 1 and result["summaries"] == 0
    assert not any("555-0142" in r.memory for r in store.get_user_memories(user_id="maya"))
    assert any(s.summary and "555-0142" in s.summary.summary for s in store.get_sessions(user_id="maya"))


def test_a_models_total_is_its_weighted_scores(ranking_file):
    """ready: a model's total weighs quality up and cost and time down, so the same three models rank differently per job"""
    from dataclasses import replace

    from launchkit.adapters.ranking import rank_list, total
    from launchkit.settings import settings

    weights = {"eval": 0.8, "cost": 0.1, "latency": 0.1}
    assert abs(total({"eval": 0.92, "cost": 0.20, "latency": 0.40}, weights) - 0.796) < 1e-9
    assert abs(total({"eval": 0.80, "cost": 0.60, "latency": 0.70}, weights) - 0.770) < 1e-9
    assert abs(total({"eval": 0.70, "cost": 0.95, "latency": 0.90}, weights) - 0.745) < 1e-9
    current = replace(settings, ranking=ranking_file)
    assert rank_list("long_text", current) == ["strong-model", "mid-model", "cheap-model"]
    assert rank_list("short_text", current) == ["cheap-model", "mid-model", "strong-model"]


@pytest.mark.placeholder
def test_the_placeholder_route_returns_one_model_even_with_no_setting(ranking_file):
    """ready: on the participant branch every job gets the one configured model, and with LAUNCHKIT_MODEL empty the default"""
    from dataclasses import replace

    from launchkit.adapters.routing import route
    from launchkit.settings import DEFAULT_MODEL, settings

    current = replace(settings, model="", ranking=ranking_file)
    assert route("long_text", current) == ("long_text", [(DEFAULT_MODEL, "the one setting")])
    assert route("vision", replace(current, model="gpt-5.5")) == ("vision", [("gpt-5.5", "the one setting")])


def test_the_scoreboard_groups_calls_by_model():
    """ready: the scoreboard adds up calls, tokens, seconds and dollars per model"""
    trace = Trace()
    trace.route("long_text", "gpt-5.5", "the one setting")
    trace.call("long_text", "gpt-5.5", seconds=4.0, input_tokens=1000, cached_tokens=0, output_tokens=200, usd=0.011)
    trace.call("short_text", "gpt-5.5", seconds=2.0, input_tokens=500, cached_tokens=100, output_tokens=50, usd=0.004)
    trace.call("research", "gpt-5-nano", seconds=1.0, input_tokens=300, cached_tokens=0, output_tokens=60, usd=None)
    rows = {r["model"]: r for r in trace.bill()}
    assert rows["gpt-5.5"]["calls"] == 2 and rows["gpt-5.5"]["seconds"] == 6.0 and round(rows["gpt-5.5"]["usd"], 3) == 0.015
    assert rows["gpt-5.5"]["jobs"] == ["long_text", "short_text"]
    assert rows["gpt-5-nano"]["usd"] is None
    lines = trace.lines()
    assert any(l.startswith("route     long_text · gpt-5.5 · the one setting") for l in lines)
    assert any(l.startswith("call      long_text · gpt-5.5 · 4.0 s") for l in lines)


def test_the_models_route_lists_every_job_with_its_rank_list(page, ranking_file, monkeypatch):
    """ready: GET /models shows each job's models in rank order, with their scores, so the room can read the rank file"""
    from dataclasses import replace

    from launchkit.web import app as web

    monkeypatch.setattr(web, "settings", replace(web.settings, ranking=ranking_file))
    body = page.get("/models").json()
    assert [m["model"] for m in body["jobs"]["long_text"]["models"]] == ["strong-model", "mid-model", "cheap-model"]
    assert body["jobs"]["long_text"]["weights"] == {"eval": 0.8, "cost": 0.1, "latency": 0.1}
