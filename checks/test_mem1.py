"""Hands-on 1, in its three parts: memory switched on, then what earns a write, then whose it is."""

from agno.db.schemas.memory import UserMemory

from launchkit.agents.main_agent import run_main
from launchkit.memory.long_term import KINDS, RULES, memory_db, memories_for

from memory_asks import BREEZE, PHOTO_RULE, TIDAL


def says(keep: bool, everyone: bool = False):
    """Maya's answers once part 3 asks her: yes or no to keeping a row, and yes or no to keeping it for everyone at
    Harbor. No to any other write."""
    return lambda name, inputs: {"keep_in_memory": keep, "keep_for_everyone": everyone}.get(name, False)


def two_launches(settings, request_for, memory, trace, approve):
    for text in TIDAL:
        run_main(request_for(text=text), settings=settings, model=memory, trace=trace, approve=approve)
    return memories_for(memory_db(settings, "harbor", "maya"), "harbor", "maya")


# Part 1 · Switch it on


def test_two_launches_leave_rows_in_the_store(settings, trace, request_for, memory):
    """Part 1: after Maya's two Tidal messages, the store holds rows for her, and the photo rule is one of them."""
    rows = two_launches(settings, request_for, memory, trace, says(True))
    assert rows, "the store is empty: is memory switched on on the main agent?"
    assert PHOTO_RULE in [row.memory for row in rows]


def test_breeze_now_asks_for_the_photo(settings, trace, request_for, memory):
    """Part 1: Breeze in a new chat, after the two launches: no AI picture; the agent asks for Harbor's photo."""
    two_launches(settings, request_for, memory, trace, says(True))
    result = run_main(request_for(text=BREEZE, session_id="breeze"), settings=settings, model=memory, trace=trace, approve=says(True))
    assert not trace.tool_calls("generate_image") and "photo" in result.reply.lower()


# Part 2 · What earns a write


def test_the_agent_decides_to_write(settings, trace, request_for, memory):
    """Part 2: with agentic memory on, the main agent calls update_user_memory itself, and the call is in the trace."""
    two_launches(settings, request_for, memory, trace, says(False))
    assert trace.tool_calls("update_user_memory"), "no update_user_memory call: is enable_agentic_memory on?"


def test_the_rules_name_the_kinds_and_what_never_goes_in():
    """Part 2: memory/write_rules.md names the four kinds of memory and says what is never kept."""
    assert RULES.exists(), "no launchkit/memory/write_rules.md yet"
    text = RULES.read_text(encoding="utf-8").lower()
    assert all(kind in text for kind in KINDS)
    assert "never" in text or "do not" in text


def test_one_row_with_kind_author_and_source(settings, trace, request_for, memory):
    """Part 2: two launches, Maya says yes: one row is kept, the photo rule, with its kind, who said it and where it came from."""
    rows = two_launches(settings, request_for, memory, trace, says(True))
    assert [row.memory for row in rows] == [PHOTO_RULE]
    assert {"preference", "author:maya", "source:conversation"} <= set(rows[0].topics)


# Part 3 · Whose it is


def test_a_no_keeps_nothing(settings, trace, request_for, memory):
    """Part 3: Maya says no: nothing is kept, and the trace says she said no."""
    assert two_launches(settings, request_for, memory, trace, says(False)) == []
    assert any(e.kind == "refused" and "Maya said no" in e.detail["reason"] for e in trace.events)


def test_kept_for_everyone_reaches_sam_and_nothing_else_does(settings, trace, request_for, memory):
    """Part 3: kept for everyone at Harbor, the photo rule reaches Sam's new chat; Maya's own rows stay hers."""
    db = memory_db(settings, "harbor", "maya")
    db.upsert_user_memory(UserMemory(memory="Maya reviews the square feed format first.", topics=["workflow", "review order"], user_id="maya"))
    two_launches(settings, request_for, memory, trace, says(True, everyone=True))
    sams = [row.memory for row in memories_for(db, "harbor", "sam")]
    assert PHOTO_RULE in sams and "Maya reviews the square feed format first." not in sams
    result = run_main(request_for(text=BREEZE, user_id="sam", session_id="breeze"), settings=settings, model=memory, trace=trace, approve=says(False))
    assert not trace.tool_calls("generate_image") and "photo" in result.reply.lower()


def test_a_kept_row_moves_to_everyone_in_the_same_chat(settings, trace, request_for, memory):
    """Part 3: Maya's own photo row, then in the same chat "that goes for everyone at Harbor": the row moves to everyone, and Sam sees it."""
    two_launches(settings, request_for, memory, trace, says(True))
    db = memory_db(settings, "harbor", "maya")
    assert [row.user_id for row in memories_for(db, "harbor", "maya")] == ["maya"]
    share = "Use our own shoot photos, never AI pictures. That goes for everyone at Harbor."
    run_main(request_for(text=share), settings=settings, model=memory, trace=trace, approve=says(True, everyone=True))
    rows = memories_for(db, "harbor", "maya")
    assert [(row.memory, row.user_id) for row in rows] == [(PHOTO_RULE, "harbor:everyone")]
    assert PHOTO_RULE in [row.memory for row in memories_for(db, "harbor", "sam")]
