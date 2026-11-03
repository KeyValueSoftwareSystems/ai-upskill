import yaml

from launchkit.agents.main_agent import run_main
from launchkit.memory.long_term import memory_db, memories_for
from launchkit.settings import ROOT

from memory_asks import BREEZE, PHOTO_RULE, PLACES, TIDAL

LAYER_MAP = ROOT / "launchkit" / "memory" / "layer_map.yaml"


def keep_her_own(name, inputs):
    """Maya's answers once memory step 2 asks her: yes, keep it; no, not for everyone. No to any other write."""
    return name == "keep_in_memory"


def two_launches(settings, request_for, memory, trace):
    for text in TIDAL:
        run_main(request_for(text=text), settings=settings, model=memory, trace=trace, approve=keep_her_own)
    return memories_for(memory_db(settings, "harbor", "maya"), "harbor", "maya")


def the_map() -> list[dict]:
    return yaml.safe_load(LAYER_MAP.read_text(encoding="utf-8")) or []


def test_two_launches_leave_rows_in_the_store(settings, trace, request_for, memory):
    """After Maya's two Tidal messages, the store holds rows for her, and the photo rule is one of them."""
    rows = two_launches(settings, request_for, memory, trace)
    assert rows, "the store is empty: is update_memory_on_run on the main agent?"
    assert PHOTO_RULE in [row.memory for row in rows]


def test_every_row_on_the_map_has_a_place_and_a_reason():
    """layer_map.yaml sorts the dump: at least five rows, each in one of the seven places, each with why."""
    entries = the_map()
    assert len(entries) >= 5, "sort every row your store kept into layer_map.yaml"
    for entry in entries:
        assert entry.get("kept") and entry.get("belongs") in PLACES and entry.get("why"), f"needs kept, belongs and why: {entry}"


def test_only_the_photo_rule_belongs_in_memory():
    """Of everything it kept, only the photo rule belongs in memory."""
    memory = [e["kept"] for e in the_map() if e.get("belongs") == "memory"]
    assert len(memory) == 1 and "photo" in memory[0].lower(), f"in memory: {memory}"


def test_breeze_now_asks_for_the_photo(settings, trace, request_for, memory):
    """Breeze in a new chat, after the two launches: no AI picture; the agent asks for Harbor's photo."""
    two_launches(settings, request_for, memory, trace)
    result = run_main(request_for(text=BREEZE, session_id="breeze"), settings=settings, model=memory, trace=trace, approve=keep_her_own)
    assert not trace.tool_calls("generate_image") and "photo" in result.reply.lower()
