"""The answer code run against the seeded database, ticket by ticket. These pass on the answer branches only.

The other build tests build their own rows. These start from samples/memory/seed.db, the database the room
inherits, and assert each ticket's own "done when" lines.
"""

import shutil
from datetime import date

import pytest

from launchkit.memory.brand_facts import BrandFacts
from launchkit.memory.store import MemoryStore, rows_for
from launchkit.settings import ROOT
from launchkit.trace import Trace

pytestmark = pytest.mark.answer


@pytest.fixture
def seed(tmp_path):
    copy = tmp_path / "sessions.db"
    shutil.copyfile(ROOT / "samples" / "memory" / "seed.db", copy)
    return copy


def test_ticket_2_one_warranty_is_current_on_the_seed(seed):
    """build a on the seed: the brand facts table shows the 5-year warranty as current and the 2-year one is not"""
    current = [f for f in BrandFacts(str(seed)).current("harbor", date(2026, 11, 8)) if f.subject == "warranty"]
    assert [f.value for f in current] == ["5 years"]
    BrandFacts(str(seed)).record("harbor", "warranty", "6 years", source="chat", valid_from=date(2026, 11, 8))
    history = {f.value: f.valid_to for f in BrandFacts(str(seed)).history("harbor", "warranty")}
    assert history["5 years"] == date(2026, 11, 8) and history["2 years"] == date(2026, 11, 8) and history["6 years"] is None


def test_ticket_3_dana_at_alder_sees_none_of_her_harbor_rows_on_the_seed(seed):
    """build a on the seed: Dana at Alder loads none of her Harbor rows; at Harbor she still has them"""
    store = MemoryStore(str(seed), "alder", "dana", Trace())
    assert rows_for(store, "alder", "dana") == []
    assert len(rows_for(MemoryStore(str(seed), "harbor", "dana", Trace()), "harbor", "dana")) >= 3


def test_ticket_5_the_index_names_photography_and_recall_finds_the_rule_on_the_seed(seed):
    """build b on the seed: the memory index has a photography line, and recall("photography") returns the photo rule"""
    from launchkit.memory.index import memory_index, recall

    rows = rows_for(MemoryStore(str(seed), "harbor", "maya", Trace()), "harbor", "maya")
    index = memory_index(rows)
    assert '- photography: 1 row · recall("photography")' in index.splitlines()
    assert "own shoot photos" in recall(rows, "photography")
    assert all(len(line) <= 80 for line in index.splitlines())


def test_ticket_5_retention_keeps_the_photo_rule_on_the_seed(seed):
    """build b on the seed: pruning at 180 days keeps the photo rule and the brand's rows"""
    from launchkit.memory.retention import prune

    store = MemoryStore(str(seed), "harbor", "maya", Trace())
    prune(store, "harbor", date(2026, 11, 8), max_age_days=180)
    texts = [r.memory for r in store.get_user_memories(user_id="maya")]
    assert any("own shoot photos" in t for t in texts)
    assert len(store.get_user_memories(user_id="harbor:brand")) == 2


def test_ticket_6_forget_leaves_no_trace_of_the_number_in_the_file(seed):
    """build b on the seed: forgetting the number clears Maya's row, the summary and the brand learning, and the file holds no copy"""
    from launchkit.memory.forget import forget

    store = MemoryStore(str(seed), "harbor", "maya", Trace())
    result = forget(store, "harbor", "maya", "555-0142")
    assert result == {"memories": 1, "summaries": 1, "learnings": 1}
    assert forget(store, "harbor", "maya", "555-0142") == {"memories": 0, "summaries": 0, "learnings": 0}
    assert b"555-0142" not in seed.read_bytes()
    assert len(store.get_user_memories(user_id="dana")) == 3


def test_ticket_8_a_down_top_model_falls_to_the_next_on_path_a(seed, monkeypatch):
    """build c, path A: with the top model down, route still lists it first, the call fails, and the next model answers with a fallback line"""
    from dataclasses import replace

    from launchkit.adapters.jobs import Jobs
    from launchkit.adapters.routing import on_failure
    from launchkit.settings import settings

    if on_failure("long_text", ["x"], ["y"], Exception()) != "y":
        pytest.skip("path B branch")
    current = replace(settings, model="", down_models=("gpt-5.5",))
    trace = Trace()
    jobs = Jobs(current, trace)
    answered = jobs.in_order("long_text", lambda model: model.id if not hasattr(model, "reply") else model.reply())
    assert answered != "gpt-5.5"
    assert any(e.kind == "route" and e.detail["reason"] == "fallback" for e in trace.events)
