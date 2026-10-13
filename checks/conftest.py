import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from launchkit.adapters.fakes import EchoModel, EndlessModel, GoodModel, MalformedModel
from launchkit.adapters.images import FakeImages
from launchkit.harness.request import Request
from launchkit.harness.trace import Trace
from launchkit.settings import ROOT, settings as base_settings

BRIEF = "Poster for the Tidal launch. The bottle on a misty lakeshore. Headline: Cold for 24 hours."


@pytest.fixture
def settings(tmp_path):
    workspaces = tmp_path / "workspaces"
    shutil.copytree(ROOT / "workspaces", workspaces)
    return replace(base_settings, workspaces_dir=workspaces, data_dir=tmp_path / "data", image_mode="fake")


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
def malformed():
    return MalformedModel()


@pytest.fixture
def endless():
    return EndlessModel()


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
