"""Hands-on 2, in its two parts: read memory back cheaply, then keep one long conversation short."""

import re

from agno.db.base import SessionType

from launchkit.agents.main_agent import run_main
from launchkit.agents.prompt import approx_tokens
from launchkit.memory.compaction import conversation_text, must_keep
from launchkit.memory.index import LINE_CAP, memory_index, recall
from launchkit.memory.long_term import memory_db, memories_for, memory_text, seed, topic_of
from launchkit.settings import ROOT

from memory_asks import BREEZE, PHOTO_RULE

WEEK = [line.strip() for line in (ROOT / "samples" / "sessions" / "breeze_week.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")]
SESSION = "harbor:maya:week:main"


def says_no(name, inputs):
    return False


def seeded(settings):
    seed(settings, "harbor")
    return memories_for(memory_db(settings, "harbor", "maya"), "harbor", "maya")


def the_week(settings, request_for, memory, trace):
    """Maya's Breeze week, one message per turn, in one conversation. The last reply is the three headlines."""
    for text in WEEK:
        result = run_main(request_for(text=text, session_id="week"), settings=settings, model=memory, trace=trace, approve=says_no)
    return result, memory_db(settings, "harbor", "maya")


# Part A · Read it back cheaply


def test_one_short_line_per_topic(settings):
    """Part A: the index has one line per topic, each under the line cap, each naming the recall call for its topic."""
    rows = seeded(settings)
    lines = [line for line in memory_index(rows).splitlines() if line.startswith("- ")]
    topics = {topic_of(row) for row in rows}
    assert len(lines) == len(topics)
    assert all(len(line) <= LINE_CAP for line in lines)
    assert {t for line in lines for t in re.findall(r'recall\("([^"]+)"\)', line)} == topics


def test_recall_returns_one_topic_in_full(settings):
    """Part A: recall("photography") returns every photography fact, in full, and nothing from another topic."""
    rows = seeded(settings)
    found = recall(rows, "photography")
    assert PHOTO_RULE in found
    assert all(row.memory in found for row in rows if topic_of(row) == "photography")
    assert all(row.memory not in found for row in rows if topic_of(row) != "photography")


def test_the_prompt_carries_the_index_not_the_store(settings, trace, request_for, memory):
    """Part A: with a month of rows, the prompt carries the index, not every row: the memory section is the index, and smaller."""
    rows = seeded(settings)
    result = run_main(request_for(text=BREEZE), settings=settings, model=memory, trace=trace, approve=says_no)
    assert 0 < result.memory_tokens < approx_tokens(memory_text(rows))
    assert result.memory_tokens == approx_tokens(memory_index(rows))


def test_breeze_recalls_the_photo_topic_once(settings, trace, request_for, memory):
    """Part A: Breeze, with a month of rows: the agent recalls the photography topic once, then asks for Harbor's photo."""
    seeded(settings)
    result = run_main(request_for(text=BREEZE), settings=settings, model=memory, trace=trace, approve=says_no)
    assert [e.detail["arguments"] for e in trace.tool_calls("recall")] == [{"topic": "photography"}]
    assert not trace.tool_calls("generate_image") and "photo" in result.reply.lower()


# Part B · One long conversation


def test_the_week_gets_a_summary_in_the_prompt(settings, trace, request_for, memory):
    """Part B: with session summaries on, the week has a summary, and the prompt's conversation section carries it."""
    _, db = the_week(settings, request_for, memory, trace)
    session = db.get_session(session_id=SESSION, session_type=SessionType.AGENT)
    assert session.summary is not None, "no summary: is enable_session_summaries on?"
    assert session.summary.summary in conversation_text(db, SESSION)


def test_must_keep_picks_out_the_rules_she_stated():
    """Part B: must_keep picks out the rule Maya stated in the week, and none of her questions."""
    kept = must_keep(WEEK)
    assert any("never mention the lid" in rule.lower() for rule in kept)
    assert not any(rule.endswith("?") for rule in kept)


def test_the_lid_rule_survives_the_week(settings, trace, request_for, memory):
    """Part B: the summary leaves the lid rule out, the window has dropped it, and the headlines still never mention the lid."""
    result, db = the_week(settings, request_for, memory, trace)
    assert "lid" not in db.get_session(session_id=SESSION, session_type=SessionType.AGENT).summary.summary.lower()
    assert "lid" not in result.reply.lower()
