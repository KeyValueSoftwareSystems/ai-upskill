import yaml

from launchkit.adapters.fakes import ProfileModel
from launchkit.harness.onboard import onboard_workspace
from launchkit.harness.request import UnknownWorkspace
import pytest


def test_pdf_is_stored_and_four_files_are_written(settings, trace, brand_pdf):
    """Uploading a brand pack stores the PDF under assets and writes SOUL.md, AGENTS.md, rules.yaml and facts.md."""
    written = onboard_workspace("moss", brand_pdf, settings=settings, model=ProfileModel(), trace=trace)
    root = settings.workspaces_dir / "moss"
    assert (root / "assets" / "moss-brand-pack.pdf").exists()
    assert {p.name for p in written} >= {"SOUL.md", "AGENTS.md", "rules.yaml", "facts.md", "brand-book.md"}
    assert "Moss and Fern" in (root / "SOUL.md").read_text()
    rules = yaml.safe_load((root / "rules.yaml").read_text())
    assert "cheap" in rules["banned_claims"]
    assert rules["colours"]["Fern"] == "#2f6b4f"


def test_extracted_text_reaches_the_model(settings, trace, brand_pdf):
    """The model receives the PDF text, and the trace shows pages, tokens and every file written."""
    onboard_workspace("moss", brand_pdf, settings=settings, model=ProfileModel(), trace=trace)
    kinds = [e.kind for e in trace.events]
    assert kinds.count("written") == 5
    assert any(e.kind == "model" and e.detail["phase"] == "onboard" for e in trace.events)
    assert any(e.kind == "note" and "1 page" in e.detail["text"] for e in trace.events)


def test_bad_workspace_id_is_refused_before_anything_is_written(settings, trace, brand_pdf):
    """An id outside the allow-list is refused and no folder is created."""
    with pytest.raises(UnknownWorkspace):
        onboard_workspace("../moss", brand_pdf, settings=settings, model=ProfileModel(), trace=trace)
    assert not (settings.workspaces_dir / ".." / "moss").exists()
