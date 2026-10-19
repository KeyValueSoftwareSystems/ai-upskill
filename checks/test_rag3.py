import re

import launchkit.harness.search as search
from launchkit.harness.brand import make_get_brand_details
from launchkit.harness.search import TOP_K, cosine, embed
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import load_workspace


def refs(result: str) -> list[str]:
    return re.findall(r"^\[([^\]]+)\]", result, flags=re.M)


def first_chunk(result: str) -> str:
    return result.split("\n\n")[1].lower()


def tool_for(workspace_id, settings):
    return make_get_brand_details(load_workspace(workspace_id, settings, Trace()), Trace())


def test_similar_meanings_sit_close_together():
    """An embedding turns text into numbers that capture its meaning: "clean the lid" is closer to "hand-wash only" than to "750 ml"."""
    lid, hand_wash, size = embed(["clean the lid", "The lid is hand-wash only.", "750 ml"])
    assert len(lid) == 384
    assert cosine(lid, hand_wash) > cosine(lid, size)


def test_the_same_text_gives_the_same_numbers():
    """A local model gives the same result on every run: no keys, no rate limits, no drift in class."""
    assert embed(["leak-proof lid"]) == embed(["leak-proof lid"])


def test_clean_the_lid_finds_the_hand_wash_chunk(settings):
    """"How do I clean the lid?" ranks the hand-wash chunk first."""
    assert "hand-wash only" in first_chunk(tool_for("harbor", settings)("How do I clean the lid?"))


def test_spill_in_my_bag_finds_leak_proof(settings):
    """"Will it spill in my bag?" ranks leak-proof first, though they share no words."""
    assert "leak-proof" in first_chunk(tool_for("harbor", settings)("Will it spill in my bag?"))


def test_warm_on_a_long_shift_finds_hot_for_12_hours(settings):
    """"Warm on a long shift?" finds "hot for 12 hours" in the top 5."""
    assert "hot for 12 hours" in tool_for("harbor", settings)("Warm on a long shift?").lower()


def test_still_at_most_five_chunks(settings):
    """Ranking by meaning still returns at most 5 chunks."""
    assert 0 < len(refs(tool_for("harbor", settings)("poster placement logo headline print file"))) <= TOP_K == 5


def test_chunks_are_embedded_once_and_the_query_each_time(settings, monkeypatch):
    """Every chunk is embedded once; later calls embed only the query."""
    calls = []
    real = search.embed
    monkeypatch.setattr(search, "embed", lambda texts: calls.append(len(texts)) or real(texts))
    search._INDEXES.pop(settings.workspaces_dir, None)
    tool = tool_for("harbor", settings)
    tool("How do I clean the lid?")
    tool("Will it spill in my bag?")
    assert calls[0] > 20 and calls[1:] == [1, 1]


def test_next_problem_meaning_ignores_the_owner(settings):
    """The failure step 4 fixes: one shared list, so Ember asking about its next launch gets Harbor's embargoed Tidal launch."""
    result = tool_for("ember", settings)("Write a poster about our next launch.")
    assert any(ref.startswith("harbor/") for ref in refs(result))


def test_the_trace_shows_whose_chunks_came_back(settings):
    """Each returned chunk is traced with its brand, rank and cosine score, so the leak in one shared list is visible."""
    trace = Trace()
    make_get_brand_details(load_workspace("ember", settings, Trace()), trace)("Write a poster about our next launch.")
    lines = [line for line in trace.lines() if line.startswith("chunk")]
    assert len(lines) == 5 and all("score 0." in line for line in lines)
    assert any(" harbor/" in line for line in lines)
