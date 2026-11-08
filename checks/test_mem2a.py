"""Session 3, ticket 2a: a fact carries when it was true. Brand facts live in LaunchKit's own table, read in plain code."""

from datetime import date

from launchkit.agents.main_agent import build_catalogue
from launchkit.knowledge.brand_facts import all_brand_facts, get_brand_facts, set_brand_fact
from launchkit.trace import Trace

NO = lambda name, inputs: False


def test_the_warranty_is_two_rows_and_only_one_is_true_today(settings):
    """Two years, closed in March; five years, open. Today only five years comes back."""
    rows = all_brand_facts(settings, "harbor")
    assert [(r["value"], r["valid_to"]) for r in rows if r["subject"] == "warranty"] == [("2 years", "2026-03-31"), ("5 years", None)]
    assert [(r["subject"], r["value"]) for r in get_brand_facts(settings, "harbor")] == [("warranty", "5 years")]


def test_a_date_inside_the_old_window_gets_the_old_value(settings):
    """The table answers "what was true then" as well as "what is true now"."""
    assert get_brand_facts(settings, "harbor", today=date(2026, 2, 1))[0]["value"] == "2 years"


def test_updating_a_fact_closes_the_old_row_and_opens_a_new_one(settings):
    """Nothing is overwritten: the old row gets an end date, the new row starts today."""
    set_brand_fact(settings, "harbor", "warranty", "7 years", source="maya", today=date(2027, 1, 10))
    rows = [r for r in all_brand_facts(settings, "harbor", today=date(2027, 1, 10)) if r["subject"] == "warranty"]
    assert [(r["value"], r["valid_to"], r["true_today"]) for r in rows] == [("2 years", "2026-03-31", False), ("5 years", "2027-01-09", False), ("7 years", None, True)]


def test_get_brand_facts_is_a_read_tool_bound_to_the_request_brand(settings):
    """The model never names the brand: the tool takes no inputs and reads the request's workspace."""
    entry = build_catalogue(settings, Trace(), NO).entries["get_brand_facts"]
    assert entry.kind == "read"
    assert "[brand_facts/harbor/warranty] warranty: 5 years" in entry.fn()
