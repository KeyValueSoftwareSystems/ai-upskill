import yaml

from launchkit.adapters.fakes import ProfileModel
from launchkit.harness.library import read_library
from launchkit.harness.onboard import BrandProfile, Colour, render_files, onboard_workspace
from launchkit.harness.request import UnknownWorkspace
import pytest

from checks.conftest import minimal_pdf


def test_pdf_is_stored_and_four_files_are_written(settings, trace, brand_pdf):
    """Uploading a brand pack names the workspace after the brand, stores the PDF under assets and writes the files."""
    written = onboard_workspace(brand_pdf, settings=settings, model=ProfileModel(), trace=trace)
    root = settings.workspaces_dir / "moss-and-fern"
    assert (root / "assets" / "moss-brand-pack.pdf").exists()
    assert {p.name for p in written} >= {"SOUL.md", "AGENTS.md", "rules.yaml", "facts.md", "brand-book.md", "users.yaml"}
    assert "Moss and Fern" in (root / "SOUL.md").read_text()
    rules = yaml.safe_load((root / "rules.yaml").read_text())
    assert "cheap" in rules["banned_claims"]
    assert rules["colours"]["Fern"] == "#2f6b4f"


def test_extracted_text_reaches_the_model(settings, trace, brand_pdf):
    """The model receives the PDF text, and the trace shows pages, tokens and every file written."""
    onboard_workspace(brand_pdf, settings=settings, model=ProfileModel(), trace=trace)
    kinds = [e.kind for e in trace.events]
    assert kinds.count("written") == 6
    assert any(e.kind == "model" and e.detail["phase"] == "onboard" for e in trace.events)
    assert any(e.kind == "note" and "1 page" in e.detail["text"] for e in trace.events)


def test_bad_workspace_id_is_refused_before_anything_is_written(settings, trace, brand_pdf):
    """A forced id outside the allow-list is refused and no folder is created."""
    with pytest.raises(UnknownWorkspace):
        onboard_workspace(brand_pdf, workspace_id="../moss", settings=settings, model=ProfileModel(), trace=trace)
    assert not (settings.workspaces_dir / ".." / "moss").exists()


def test_a_pack_uploaded_into_a_brand_replaces_its_drafted_files(settings, trace, brand_pdf):
    """A pack uploaded into an existing brand goes into that brand's folder, whatever name the pack gives: no second folder."""
    users_before = (settings.workspaces_dir / "ember" / "users.yaml").read_text()
    folders_before = sorted(p.name for p in settings.workspaces_dir.iterdir())
    onboard_workspace(brand_pdf, workspace_id="ember", settings=settings, model=ProfileModel(), trace=trace)
    root = settings.workspaces_dir / "ember"
    assert sorted(p.name for p in settings.workspaces_dir.iterdir()) == folders_before
    assert "Moss and Fern" in (root / "SOUL.md").read_text()
    assert (root / "users.yaml").read_text() == users_before, "the brand's people are kept"
    assert (root / "assets" / "moss-brand-pack.pdf").exists()


def test_only_the_latest_pack_is_kept(settings, trace, brand_pdf, tmp_path):
    """Uploading a second pack into a brand processes the new one and replaces the older PDF under assets."""
    onboard_workspace(brand_pdf, workspace_id="ember", settings=settings, model=ProfileModel(), trace=trace)
    newer = tmp_path / "ember-v2.pdf"
    newer.write_bytes(minimal_pdf(["Ember Coffee Co. brand pack", "Warm, playful."]))
    onboard_workspace(newer, workspace_id="ember", settings=settings, model=ProfileModel(), trace=trace)
    root = settings.workspaces_dir / "ember"
    assert sorted(p.name for p in (root / "assets").iterdir()) == ["ember-v2.pdf"]
    assert "Ember Coffee Co." in (root / "SOUL.md").read_text()


def test_a_new_brand_named_like_an_existing_one_reuses_its_folder(settings, trace, brand_pdf):
    """Onboarding as a new brand twice does not fail the second time: the same folder gets the newer drafts."""
    onboard_workspace(brand_pdf, settings=settings, model=ProfileModel(), trace=trace)
    onboard_workspace(brand_pdf, settings=settings, model=ProfileModel(), trace=trace)
    assert (settings.workspaces_dir / "moss-and-fern" / "SOUL.md").exists()


def test_the_library_shows_the_brand_as_categories(settings, trace, brand_pdf):
    """The brand library shows what was extracted as readable categories, not raw files: voice, rules, banned words, colours, facts, people."""
    onboard_workspace(brand_pdf, workspace_id="ember", settings=settings, model=ProfileModel(), trace=trace)
    lib = read_library("ember", settings)
    details = {d["category"]: [i["text"] for i in d["items"]] for d in lib["details"]}
    assert details["Brand"] == ["Ember Coffee Co."]
    assert details["Voice and tone"] == ["Warm, green, patient.", "Short lines. Talk to one person."], "the template's opening line is not a brand detail"
    assert "Mention the plant's name once." in details["Copy rules"]
    assert details["Words and claims to avoid"] == ["cheap", "guaranteed"]
    assert details["Product and company facts"] == ["Pots ship in 3 days."]
    assert details["People"] == ["Jonas (marketer)"]
    colours = next(d for d in lib["details"] if d["category"] == "Colours")["items"]
    assert {"text": "Fern", "hex": "#2f6b4f"} in colours
    assert [u["name"] for u in lib["uploads"]] == ["moss-brand-pack.pdf"]
    assert not any("## " in text for items in details.values() for text in items), "no markdown leaks into the table"


def test_the_library_reads_hand_written_files_too(settings):
    """A brand whose files were written by hand still shows its colours and rules, and no uploads."""
    lib = read_library("ember", settings)
    details = {d["category"]: d["items"] for d in lib["details"]}
    assert {"text": "Ember orange", "hex": "#c2541c"} in details["Colours"]
    assert any("cheap" in i["text"] for i in details["Copy rules"])
    assert lib["uploads"] == []


def test_the_library_refuses_an_unknown_brand(settings):
    """A library request for a folder outside the allow-list or that does not exist is refused."""
    with pytest.raises(UnknownWorkspace):
        read_library("../ember", settings)
    with pytest.raises(UnknownWorkspace):
        read_library("nobody", settings)


def test_the_chat_page_wires_the_upload_form():
    """The chat page's upload form has a submit handler that posts the PDF to /onboard and shows the drafted files."""
    from launchkit.settings import ROOT

    page = (ROOT / "launchkit" / "web" / "index.html").read_text(encoding="utf-8")
    assert 'id="onboardForm"' in page
    assert '$("onboardForm").onsubmit' in page
    assert 'fetch("/onboard"' in page
    assert "onboardFiles" in page
    assert 'id="onboardClose"' in page and '$("onboardClose").onclick' in page, "the panel needs a Close control"
    assert 'id="onboardTarget"' in page and 'fd.append("workspace_id"' in page, "the upload says which brand it is for"


def test_the_chat_page_has_a_brand_library():
    """The header has a Brand library button; its panel uploads a brand file for the selected brand and shows a read-only table."""
    from launchkit.settings import ROOT

    page = (ROOT / "launchkit" / "web" / "index.html").read_text(encoding="utf-8")
    assert 'id="libraryToggle"' in page and 'id="library"' in page
    assert "fetch(`/library/" in page and 'id="libraryForm"' in page and '$("libraryForm").onsubmit' in page
    assert "brand-table" in page and "textarea" not in page and '"PUT"' not in page



def test_agents_md_states_each_rule_once():
    """AGENTS.md states the word limits and the no-words rule once, even when the pack's own rules repeat them."""
    profile = BrandProfile(
        brand_name="Moss and Fern", voice=["You are warm."],
        rules=["Headline up to 6 words.", "Subheadline up to 12 words.", "Body copy up to 25 words.", "Picture never contains words.", "Talk to one person."],
        banned_claims=["cheap"], colours=[Colour(name="Fern", hex="#2f6b4f")], facts=["Pots ship in 3 days."],
    )
    lines = [line for line in render_files(profile, "pack text")["AGENTS.md"].splitlines() if line.startswith("- ")]
    assert len(lines) == len(set(lines))
    assert sum(("headline" in line.lower() or "body" in line.lower()) and "words" in line.lower() for line in lines) == 1
    assert sum("contains words" in line.lower() for line in lines) == 1
    assert "- Talk to one person." in lines


def test_the_chat_page_shows_a_working_state():
    """While a run is in flight the chat shows a Working bubble with the elapsed time; it goes away on the answer, an error, or a lost connection."""
    from launchkit.settings import ROOT

    page = (ROOT / "launchkit" / "web" / "index.html").read_text(encoding="utf-8")
    assert 'add("pending"' in page and "Working" in page
    assert "setInterval" in page and "clearInterval" in page
    assert "lost the connection" in page.lower()


def test_an_id_with_a_trailing_newline_is_refused(settings, trace, brand_pdf):
    """The allow-list is matched in full for onboarding too: 'moss' plus a newline makes no folder."""
    with pytest.raises(UnknownWorkspace):
        onboard_workspace(brand_pdf, workspace_id="moss\n", settings=settings, model=ProfileModel(), trace=trace)
    assert not any(p.name.startswith("moss") for p in settings.workspaces_dir.iterdir())
