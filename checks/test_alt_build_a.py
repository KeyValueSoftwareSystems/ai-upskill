"""Build A, what one fact holds: tickets 1, 2 and 3. These pass once the slots are built, on the answer branches."""

from datetime import date

import pytest
from agno.db.schemas.memory import UserMemory

from launchkit.memory.brand_facts import BrandFacts
from launchkit.memory.store import MemoryStore, capture_rules, rows_for
from launchkit.trace import Trace

pytestmark = pytest.mark.answer


def test_a_new_value_closes_the_old_row(tmp_path):
    """build a: recording a 5-year warranty closes the 2-year row, and current() returns one row"""
    facts = BrandFacts(str(tmp_path / "f.db"))
    facts.record("harbor", "warranty", "2 years", source="chat", valid_from=date(2026, 2, 1))
    facts.record("harbor", "warranty", "5 years", source="chat", valid_from=date(2026, 10, 1))
    current = [f for f in facts.current("harbor", date(2026, 11, 1)) if f.subject == "warranty"]
    assert [(f.value, f.valid_to) for f in current] == [("5 years", None)]
    closed = [f for f in facts.history("harbor", "warranty") if f.valid_to is not None]
    assert [(f.value, f.valid_to) for f in closed] == [("2 years", date(2026, 10, 1))]


def test_as_of_an_earlier_date_the_old_value_is_current(tmp_path):
    """build a: asked as of September, the 2-year warranty is the current one"""
    facts = BrandFacts(str(tmp_path / "f.db"))
    facts.record("harbor", "warranty", "2 years", source="chat", valid_from=date(2026, 2, 1))
    facts.record("harbor", "warranty", "5 years", source="chat", valid_from=date(2026, 10, 1))
    assert [f.value for f in facts.current("harbor", date(2026, 9, 1))] == ["2 years"]


def test_capture_rules_name_the_three_things_never_saved():
    """build a: the capture rules say one fact per row, no quoted never-say phrase, no personal data"""
    text = capture_rules().lower()
    assert "one fact" in text and "never-say" in text and "personal" in text


def test_rows_for_keeps_brands_apart(tmp_path):
    """build a: Dana's Harbor rows stay out of her Alder chat; a brand row reaches everyone at that brand"""
    store = MemoryStore(str(tmp_path / "s.db"), "harbor", "dana", Trace())
    store.insert_raw(UserMemory(memory="never say lifetime guarantee", user_id="dana", topics=["scope:user:dana", "brand:harbor"]))
    store.insert_raw(UserMemory(memory="Harbor ships Fridays", user_id="harbor:brand", topics=["scope:brand:harbor"]))
    assert [r.memory for r in rows_for(store, "alder", "dana")] == []
    assert "Harbor ships Fridays" in [r.memory for r in rows_for(store, "harbor", "maya")]
