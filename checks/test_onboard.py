import yaml

from launchkit.adapters.fakes import ProfileModel
from launchkit.harness.onboard import BrandProfile, Colour, render_files, onboard_workspace
from launchkit.harness.request import UnknownWorkspace
import pytest


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


def test_an_existing_brand_is_never_overwritten(settings, trace, brand_pdf):
    """Onboarding a pack for a brand that already has a workspace is refused, and its files stay as they were."""
    before = (settings.workspaces_dir / "harbor" / "SOUL.md").read_text()
    with pytest.raises(FileExistsError):
        onboard_workspace(brand_pdf, workspace_id="harbor", settings=settings, model=ProfileModel(), trace=trace)
    assert (settings.workspaces_dir / "harbor" / "SOUL.md").read_text() == before


def test_the_chat_page_wires_the_upload_form():
    """The chat page's upload form has a submit handler that posts the PDF to /onboard and shows the drafted files."""
    from launchkit.settings import ROOT

    page = (ROOT / "launchkit" / "web" / "index.html").read_text(encoding="utf-8")
    assert 'id="onboardForm"' in page
    assert '$("onboardForm").onsubmit' in page
    assert 'fetch("/onboard"' in page
    assert "onboardFiles" in page


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
