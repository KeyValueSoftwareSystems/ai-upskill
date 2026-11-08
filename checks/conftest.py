import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from launchkit.adapters.fakes import BriefModel, EchoModel, EndlessModel, GoodModel, LookupModel, MalformedModel
from launchkit.adapters.image_providers import FakeImages
from launchkit.brands.request import Request
from launchkit.settings import ROOT, settings as base_settings
from launchkit.trace import Trace

BRIEF = "Poster for the Tidal bottle on a misty lakeshore at dawn. Headline idea: cold for 24 hours."


@pytest.fixture(scope="session")
def indexed_store(tmp_path_factory):
    """The brands' documents processed once per test session: chunked, embedded and stored, as `launchkit index` does."""
    from launchkit.knowledge.brand_index import BrandStore

    path = tmp_path_factory.mktemp("index") / "brand-store"
    store = BrandStore(path)
    for folder in sorted(p for p in (ROOT / "workspaces").iterdir() if p.is_dir()):
        store.index(folder.name, folder)
    return path


@pytest.fixture
def settings(tmp_path, indexed_store):
    workspaces = tmp_path / "workspaces"
    shutil.copytree(ROOT / "workspaces", workspaces)
    shutil.copytree(indexed_store, tmp_path / "data" / "brand-store")
    return replace(base_settings, workspaces_dir=workspaces, data_dir=tmp_path / "data", image_mode="fake", search="saved", board="local")


@pytest.fixture
def images(tmp_path):
    return FakeImages(tmp_path / "outputs")


@pytest.fixture
def trace():
    return Trace()


@pytest.fixture
def request_for():
    def make(workspace_id="harbor", text=BRIEF, user_id="maya", session_id="t1"):
        return Request(workspace_id=workspace_id, user_id=user_id, session_id=session_id, text=text)

    return make


@pytest.fixture
def echo():
    return EchoModel()


@pytest.fixture
def good():
    return GoodModel()


@pytest.fixture
def lookup():
    return LookupModel()


@pytest.fixture
def malformed():
    return MalformedModel()


@pytest.fixture
def endless():
    return EndlessModel()


@pytest.fixture
def brief():
    return BriefModel()


@pytest.fixture
def slow_search(settings):
    """Every search_web call takes 0.4 seconds, like a slow page, so one-after-another and side-by-side differ in time."""
    return replace(settings, search_delay=0.4)


def pytest_runtest_logreport(report):
    if report.when != "call":
        return
    doc = (report.head_line or "").strip()
    item_doc = getattr(report, "_launchkit_doc", None)
    label = item_doc or doc
    mark = "PASS" if report.passed else "FAIL"
    print(f"\n{mark}  {label}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    doc = (item.function.__doc__ or item.name).strip().splitlines()[0]
    callspec = getattr(item, "callspec", None)
    report._launchkit_doc = f"{doc}  [{callspec.id}]" if callspec else doc


def minimal_pdf(lines: list[str]) -> bytes:
    content = "BT /F1 12 Tf 40 760 Td 16 TL " + " ".join(f"({line}) Tj T*" for line in lines) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = "%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out.encode()))
        out += f"{i} 0 obj\n{obj}\nendobj\n"
    xref = len(out.encode())
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode()


@pytest.fixture
def brand_pdf(tmp_path):
    path = tmp_path / "moss-brand-pack.pdf"
    path.write_bytes(minimal_pdf(["Moss and Fern brand pack", "Voice: warm, green, patient.", "Never say cheap or guaranteed.", "Colour: Fern 2f6b4f. Pots ship in 3 days."]))
    return path


@pytest.fixture(autouse=True)
def no_gpu_pictures(monkeypatch):
    """Checks never call the GPU picture service, even when a trainee's .env points at it: real-picture checks stand in for LiteLLM."""
    monkeypatch.delenv("IMAGESVC_URL", raising=False)
    monkeypatch.setenv("LAUNCHKIT_IMAGE_PROVIDER", "litellm")


@pytest.fixture
def ranking_file(tmp_path):
    """A small rank file with the design page's numbers: strong 0.92/0.20/0.40, mid 0.80/0.60/0.70, cheap 0.70/0.95/0.90."""
    import json

    path = tmp_path / "ranking.json"
    models = {
        "strong-model": {"eval": 0.92, "cost": 0.20, "latency": 0.40},
        "mid-model": {"eval": 0.80, "cost": 0.60, "latency": 0.70},
        "cheap-model": {"eval": 0.70, "cost": 0.95, "latency": 0.90},
    }
    path.write_text(json.dumps({
        "about": "test numbers",
        "jobs": {
            "long_text": {"about": "launch copy", "weights": {"eval": 0.8, "cost": 0.1, "latency": 0.1}, "models": models},
            "short_text": {"about": "a short answer", "weights": {"eval": 0.2, "cost": 0.6, "latency": 0.2}, "models": models},
            "research": {"about": "three lines from pages", "weights": {"eval": 0.5, "cost": 0.3, "latency": 0.2}, "models": models},
            "memory_write": {"about": "the extractor", "weights": {"eval": 0.3, "cost": 0.5, "latency": 0.2}, "models": models},
            "vision": {"about": "reading a photo", "weights": {"eval": 0.7, "cost": 0.2, "latency": 0.1}, "models": {**models, "see-model": {"eval": 0.95, "cost": 0.3, "latency": 0.5}}},
        },
    }))
    return path
