import re

import pytest

import launchkit.harness.store as store_module
from launchkit.harness.brand import make_get_brand_details
from launchkit.harness.search import TOP_K, cosine, embed
from launchkit.harness.store import BrandStore
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import load_workspace


def refs(result: str) -> list[str]:
    return re.findall(r"^\[([^\]]+)\]", result, flags=re.M)


def first_chunk(result: str) -> str:
    return result.split("\n\n")[1].lower()


def tool_for(workspace_id, settings, trace=None):
    return make_get_brand_details(load_workspace(workspace_id, settings, Trace()), trace or Trace(), settings)


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


def test_next_problem_meaning_ignores_the_owner(settings):
    """The failure step 4 fixes: one shared list, so Ember asking about its next launch gets Harbor's embargoed Tidal launch."""
    result = tool_for("ember", settings)("Write a poster about our next launch.")
    assert any(ref.startswith("harbor/") for ref in refs(result))


def test_the_trace_shows_whose_chunks_came_back(settings):
    """Each returned chunk is traced with its brand, rank and cosine score, so the leak in one shared list is visible."""
    trace = Trace()
    tool_for("ember", settings, trace)("Write a poster about our next launch.")
    lines = [line for line in trace.lines() if line.startswith("chunk")]
    assert len(lines) == 5 and all("score 0." in line for line in lines)
    assert any(" harbor/" in line for line in lines)


def test_the_tool_only_searches(settings, monkeypatch):
    """A lookup embeds the question and nothing else: no brand file is read or embedded during a turn."""
    calls = []
    real = store_module.embed
    monkeypatch.setattr(store_module, "embed", lambda texts: calls.append(len(texts)) or real(texts))
    monkeypatch.setattr(store_module, "load_chunks", lambda root: pytest.fail("the tool read brand files"))
    tool = tool_for("harbor", settings)
    tool("How do I clean the lid?")
    tool("Will it spill in my bag?")
    assert calls == [1, 1]


def test_the_vectors_survive_a_restart(settings, monkeypatch):
    """The vector database keeps the vectors on disk: a new process does not embed the chunks again."""
    calls = []
    real = store_module.embed
    monkeypatch.setattr(store_module, "embed", lambda texts: calls.append(len(texts)) or real(texts))
    root = settings.workspaces_dir / "harbor"
    assert BrandStore(settings.data_dir / "fresh").index("harbor", root) > 20
    calls.clear()
    restarted = BrandStore(settings.data_dir / "fresh")
    assert restarted.index("harbor", root) == 0
    restarted.search("How do I clean the lid?")
    assert calls == [1], "only the question is embedded after a restart"


def test_an_edited_file_embeds_only_what_changed(settings):
    """When a brand file changes and is indexed again, only the changed chunks are embedded; the rest keep their vectors."""
    store = BrandStore(settings.data_dir / "fresh")
    root = settings.workspaces_dir / "harbor"
    store.index("harbor", root)
    facts = root / "facts.md"
    facts.write_text(facts.read_text() + "Ships in a recycled cardboard tube.\n")
    assert store.index("harbor", root) == 1
    assert "cardboard tube" in "".join(c.text for _, c in store.search("what does it ship in"))


def test_onboarding_indexes_the_brand(settings, trace, brand_pdf):
    """Uploading a brand pack is the document processing step: the new brand is in the store straight away."""
    from launchkit.adapters.fakes import ProfileModel
    from launchkit.harness.onboard import onboard_workspace

    onboard_workspace(brand_pdf, settings=settings, model=ProfileModel(), trace=trace)
    assert any(line.startswith("note      indexed moss-and-fern:") for line in trace.lines())
    assert BrandStore(settings.data_dir / "brand-store").indexed("moss-and-fern") > 0


def test_launchkit_index_processes_hand_written_brands(settings, monkeypatch, capsys):
    """`launchkit index` processes brands whose files were written by hand, once; a second run embeds nothing."""
    import shutil

    import launchkit.cli as cli

    shutil.rmtree(settings.data_dir / "brand-store")
    monkeypatch.setattr(cli, "settings", settings)
    assert cli.main(["index", "harbor"]) == 0
    assert "embedded now" in capsys.readouterr().out
    assert cli.main(["index", "harbor"]) == 0
    assert ", 0 embedded now" in capsys.readouterr().out


def test_a_brand_that_was_never_indexed_says_so(settings):
    """A brand whose documents were never processed gets a clear answer and a trace note, not a search."""
    import shutil

    shutil.copytree(settings.workspaces_dir / "ember", settings.workspaces_dir / "newbrand")
    trace = Trace()
    result = tool_for("newbrand", settings, trace)("our next launch")
    assert "has not been indexed" in result and not refs(result)
    assert any("launchkit index newbrand" in line for line in trace.lines())
