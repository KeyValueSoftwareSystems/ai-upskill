import yaml

from launchkit.agents.main_agent import run_main
from launchkit.memory.long_term import memory_db, memories_for
from launchkit.settings import ROOT

from memory_asks import BREEZE, PHOTO_RULE, PLACES, TIDAL

LAYER_MAP = ROOT / "launchkit" / "memory" / "layer_map.yaml"


def two_launches(settings, request_for, memory, trace):
    for text in TIDAL:
        run_main(request_for(text=text), settings=settings, model=memory, trace=trace, approve=lambda name, inputs: False)
    return memories_for(memory_db(settings, "harbor", "maya"), "harbor", "maya")


def test_two_launches_leave_rows_in_the_store(settings, trace, request_for, memory):
    """After Maya's two Tidal messages, the store holds rows for her, and the photo rule is one of them."""
    rows = two_launches(settings, request_for, memory, trace)
    assert rows, "the store is empty: is update_memory_on_run on the main agent?"
    assert PHOTO_RULE in [row.memory for row in rows]


def test_every_row_is_placed_on_the_map(settings, trace, request_for, memory):
    """layer_map.yaml places every row the store kept, each with where it belonged and why."""
    rows = two_launches(settings, request_for, memory, trace)
    placed = {entry["kept"]: entry for entry in yaml.safe_load(LAYER_MAP.read_text(encoding="utf-8")) or []}
    assert rows, "the store is empty: is update_memory_on_run on the main agent?"
    for row in rows:
        assert row.memory in placed, f"not on the map yet: {row.memory}"
        assert placed[row.memory].get("belongs") in PLACES and placed[row.memory].get("why")


def test_only_the_photo_rule_belongs_in_memory():
    """Of everything it kept, only the photo rule belongs in memory."""
    entries = yaml.safe_load(LAYER_MAP.read_text(encoding="utf-8")) or []
    assert [e["kept"] for e in entries if e.get("belongs") == "memory"] == [PHOTO_RULE]


def test_breeze_now_asks_for_the_photo(settings, trace, request_for, memory):
    """Breeze in a new chat, after the two launches: no AI picture; the agent asks for Harbor's photo."""
    two_launches(settings, request_for, memory, trace)
    result = run_main(request_for(text=BREEZE, session_id="breeze"), settings=settings, model=memory, trace=trace, approve=lambda name, inputs: False)
    assert not trace.tool_calls("generate_image") and "photo" in result.reply.lower()
