from launchkit.agents.main_agent import run_main
from launchkit.memory.long_term import memory_db, memories_for

from memory_asks import BREEZE, PHOTO_RULE, TIDAL


def keep_her_own(name, inputs):
    """Maya's answers once memory step 2 asks her: yes, keep it; no, not for everyone. No to any other write."""
    return name == "keep_in_memory"


def two_launches(settings, request_for, memory, trace):
    for text in TIDAL:
        run_main(request_for(text=text), settings=settings, model=memory, trace=trace, approve=keep_her_own)
    return memories_for(memory_db(settings, "harbor", "maya"), "harbor", "maya")


def test_two_launches_leave_rows_in_the_store(settings, trace, request_for, memory):
    """After Maya's two Tidal messages, the store holds rows for her, and the photo rule is one of them."""
    rows = two_launches(settings, request_for, memory, trace)
    assert rows, "the store is empty: is update_memory_on_run on the main agent?"
    assert PHOTO_RULE in [row.memory for row in rows]


def test_breeze_now_asks_for_the_photo(settings, trace, request_for, memory):
    """Breeze in a new chat, after the two launches: no AI picture; the agent asks for Harbor's photo."""
    two_launches(settings, request_for, memory, trace)
    result = run_main(request_for(text=BREEZE, session_id="breeze"), settings=settings, model=memory, trace=trace, approve=keep_her_own)
    assert not trace.tool_calls("generate_image") and "photo" in result.reply.lower()
