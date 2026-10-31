import json

from PIL import Image

from launchkit.harness.main import build_catalogue, run_main
from launchkit.harness.picture_tools import APPROVED
from launchkit.harness.trace import Trace

NO = lambda name, inputs: False


def test_the_main_agent_holds_the_two_session_1_tools(settings):
    """The main agent starts with the two tools Session 1 built: get_brand_details and generate_image."""
    entries = build_catalogue(settings, Trace(), NO).entries
    assert {"get_brand_details", "generate_image"} <= set(entries)


def test_the_main_agent_answers_a_greeting(settings, trace, request_for):
    """One agent decides what runs: a greeting needs no tool."""
    from launchkit.adapters.fakes import ToolsModel

    result = run_main(request_for(text="Morning!"), settings=settings, model=ToolsModel(), trace=trace, approve=NO)
    assert result.reply and trace.tool_calls() == []


def test_the_approved_poster_and_its_bottle_box_are_ready():
    """The approved Tidal poster is 1200x1200, and the bottle's box is saved next to it for the fakes."""
    assert Image.open(APPROVED).size == (1200, 1200)
    left, top, right, bottom = json.loads(APPROVED.with_suffix(".bottle.json").read_text())["box"]
    assert 0 <= left < right <= 1200 and 0 <= top < bottom <= 1200


def test_the_chat_page_runs_the_main_agent(settings, monkeypatch):
    """The chat page talks to the same main agent as `launchkit main`, and shows its reply and how much it had in view."""
    from queue import Queue

    import launchkit.web.app as web

    monkeypatch.setattr(web, "settings", settings)
    queue = Queue()
    web._worker(web.RunBody(workspace_id="harbor", user_id="maya", text="Morning!", model="fake:tools"), queue)
    events = list(queue.queue)
    result = next(e for e in events if isinstance(e, dict) and e.get("type") == "result")
    assert result["reply"] and set(result["view"]) == {"tool_tokens", "history_tokens", "seconds"}


def test_the_chat_page_asks_before_a_write_and_waits_for_the_answer():
    """A write stops the run: the page shows what the agent wants to do, and its Allow or Deny comes back as the answer."""
    import threading
    from queue import Queue

    import launchkit.web.app as web

    queue = Queue()
    approve = web.ask_on_page(queue)
    answers = []
    worker = threading.Thread(target=lambda: answers.append(approve("remove_files", {"card": "tidal"})))
    worker.start()
    ask = queue.get(timeout=5)
    assert ask["type"] == "ask" and ask["name"] == "remove_files" and ask["inputs"] == {"card": "tidal"}
    web.answer(ask["id"], web.Answer(allow=True))
    worker.join(timeout=5)
    assert answers == [True]


def test_the_chat_page_serves_only_pictures_and_sounds_under_data(settings, monkeypatch):
    """Files the agent made are shown on the page; nothing outside data/, and no other kind of file, is served."""
    import pytest
    from fastapi import HTTPException

    import launchkit.web.app as web

    monkeypatch.setattr(web, "settings", settings)
    (settings.data_dir / "sizes").mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "sizes" / "a.png").write_bytes(b"png")
    (settings.data_dir / "notes.json").write_text("{}")
    assert web.new_files(settings, 0) == ["/files/sizes/a.png"]
    assert str(web.data_file("sizes/a.png").path).endswith("a.png")
    for name in ("notes.json", "../pyproject.toml"):
        with pytest.raises(HTTPException):
            web.data_file(name)


def test_the_main_agent_knows_todays_date(settings):
    """A model has no clock: the prompt tells it the date, so "this season" searches look for this year."""
    from datetime import date

    from launchkit.harness.context import ContextBuilder
    from launchkit.harness.main import build_main_agent
    from launchkit.harness.workspace import load_workspace

    ws = load_workspace("harbor", settings, Trace())
    agent = build_main_agent(ws, ContextBuilder(settings.budgets), None, settings, Trace(), build_catalogue(settings, Trace(), NO))
    assert f"Today is {date.today():%-d %B %Y}." in agent.system_message
