import json
from dataclasses import replace
from pathlib import Path

from PIL import Image

from launchkit.agents.main_agent import build_catalogue, run_main
from launchkit.guardrails.limits import Limits, make_leash
from launchkit.tools.resize_poster import APPROVED
from launchkit.trace import Trace

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

    from launchkit.agents.prompt import ContextBuilder
    from launchkit.agents.main_agent import build_main_agent
    from launchkit.brands.workspace import load_workspace

    ws = load_workspace("harbor", settings, Trace())
    agent = build_main_agent(ws, ContextBuilder(settings.budgets), None, settings, Trace(), build_catalogue(settings, Trace(), NO))
    assert f"Today is {date.today():%-d %B %Y}." in agent.system_message


class BannedWordModel:
    """Writes a poster with a banned claim, and keeps it when asked to repair."""

    @staticmethod
    def make(fixed: bool):
        from launchkit.adapters.fakes import FakeModel, poster_turn, text_response

        class Model(FakeModel):
            def __init__(self):
                super().__init__("banned")
                self.turns = 0

            def answer(self, messages, tools):
                self.turns += 1
                body = "Keeps drinks cold all day." if fixed and self.turns > 1 else "The unbreakable bottle for every trail."
                return text_response(poster_turn({"headline": "Cold for 24 hours", "subheadline": "Tidal, built for the shore",
                                                  "body": body, "image_prompt": "a bottle on a lakeshore"}), messages)

        return Model()


def test_the_main_agent_checks_poster_words_repairs_once_then_stops(settings, trace, request_for):
    """Session 1's check still holds: poster words are checked in code, repaired once, then refused with a typed error."""
    import pytest
    from launchkit.guardrails.poster_check import SpecError

    with pytest.raises(SpecError) as raised:
        run_main(request_for(text="A Tidal poster, please."), settings=settings, model=BannedWordModel.make(fixed=False), trace=trace, approve=NO)
    assert [e.detail["attempt"] for e in trace.events if e.kind == "validation"] == [1, 2]
    assert any("unbreakable" in e for e in raised.value.errors)


def test_a_repaired_poster_passes(settings, trace, request_for):
    """When the repair fixes the words, the poster goes out with its spec."""
    result = run_main(request_for(text="A Tidal poster, please."), settings=settings, model=BannedWordModel.make(fixed=True), trace=trace, approve=NO)
    assert result.spec is not None and "unbreakable" not in result.spec.body
    assert "Cold for 24 hours" in result.reply


def test_a_new_conversation_has_no_picture_until_one_is_attached(settings, request_for):
    """The picture tools work on the newest picture in this conversation. A new conversation has none, and the tool
    says so; nothing is read from a saved file."""
    from launchkit.tools.resize_poster import PictureDesk, needs_picture
    from launchkit.memory.attached_pictures import NO_PICTURE, Pictures

    pictures = Pictures(settings, "harbor", "maya", "t1")
    desk = PictureDesk(settings, {}, Trace(), None, pictures.newest)
    size_of = needs_picture(lambda: desk.open().size)
    assert size_of() == {"status": "no picture", "reason": NO_PICTURE}
    pictures.attach(APPROVED)
    assert size_of() == (1200, 1200)
    assert "tidal-poster.jpg (attached by the marketer)" in pictures.describe()


def test_a_picture_the_agent_makes_joins_the_conversation(settings):
    """generate_image's picture becomes the newest one, so "now all the sizes" works on the poster made in this chat."""
    from launchkit.memory.attached_pictures import Pictures

    pictures = Pictures(settings, "harbor", "maya", "t1")
    made = build_catalogue(settings, Trace(), NO, pictures=pictures).entries["generate_image"].fn("a bottle on a lakeshore")
    assert str(pictures.newest()) == made["file"]
    assert "(made by you)" in pictures.describe()


def test_the_main_agent_is_told_what_pictures_the_conversation_holds(settings, request_for):
    """--attach (and the page's attach button) put the picture in this conversation, and the prompt names it."""
    from launchkit.adapters.fakes import ToolsModel

    trace = Trace()
    run_main(request_for(text="Morning!"), settings=settings, model=ToolsModel(), trace=trace, approve=NO, attach=[APPROVED])
    assert any(e.kind == "note" and "attached tidal-poster.jpg" in e.detail["text"] for e in trace.events)
    from launchkit.memory.attached_pictures import Pictures

    assert Pictures(settings, "harbor", "maya", "t1").newest().name == "tidal-poster.jpg"


def test_the_chat_page_attaches_a_picture_to_the_conversation(settings, monkeypatch):
    """The page's attach button sends the picture to /attach; it is kept with this conversation only."""
    import asyncio
    import io

    from fastapi import UploadFile

    import launchkit.web.app as web
    from launchkit.memory.attached_pictures import Pictures

    monkeypatch.setattr(web, "settings", settings)
    upload = UploadFile(file=io.BytesIO(APPROVED.read_bytes()), filename="tidal-poster.jpg")
    kept = asyncio.run(web.attach_picture(workspace_id="harbor", user_id="maya", session_id="abc123", picture=upload))
    assert kept["url"].endswith("/abc123/uploads/tidal-poster.jpg")
    assert Pictures(settings, "harbor", "maya", "abc123").newest().name == "tidal-poster.jpg"
    assert Pictures(settings, "harbor", "maya", "def456").newest() is None


def test_a_checked_poster_gets_its_picture(settings, trace, request_for):
    """Session 1's order holds: the words pass the check, then the picture is made from the image prompt, and it joins
    the conversation."""
    from launchkit.memory.attached_pictures import Pictures

    run_main(request_for(text="A Tidal poster, please."), settings=settings, model=BannedWordModel.make(fixed=True), trace=trace, approve=NO)
    assert [e.detail["arguments"] for e in trace.tool_calls("generate_image")] == [{"image_prompt": "a bottle on a lakeshore"}]
    assert Pictures(settings, "harbor", "maya", "t1").all()[-1]["by"] == "made"



def test_from_step_2_the_model_cannot_choose_the_crop_window(settings, monkeypatch):
    """Once the fit rule is built, crop takes only the size and plain code picks the window, so a model cannot hand in
    the bottle's box (or any window). In step 1 the window is still the model's to give."""
    import inspect

    import launchkit.tools.resize_poster as pt
    from launchkit.tools.resize_poster import APPROVED, PictureDesk

    desk = PictureDesk(settings, {"navy": "#1F3A5F"}, Trace(), source=APPROVED)
    monkeypatch.setattr(pt.window_around, "todo", True, raising=False)
    assert "left" in inspect.signature(pt.around_product(desk.crop)).parameters
    monkeypatch.setattr(pt.window_around, "todo", False, raising=False)
    fitted = pt.around_product(desk.crop)
    assert list(inspect.signature(fitted).parameters) == ["width", "height"] and fitted.__name__ == "crop"



def test_a_tool_run_through_run_tool_shows_once_on_the_trace():
    """run_tool records the tool it ran, so the leash adds no second run_tool line; a call it refuses still shows."""
    trace = Trace()
    leash = make_leash(Limits(), trace)

    def run_tool(name, inputs):
        if name == "crop":
            trace.tool(name, inputs, "cropped")
            return "cropped"
        return f"No tool named {name}."

    leash("run_tool", run_tool, {"name": "crop", "inputs": {}})
    leash("run_tool", run_tool, {"name": "shrink", "inputs": {}})
    assert [e.detail["name"] for e in trace.tool_calls()] == ["crop", "run_tool"]


def test_a_flat_run_tool_call_still_runs_and_a_nameless_one_shows_on_the_trace():
    """Models sometimes flatten run_tool's inputs, or drop the name. The door takes the extra fields as the inputs,
    and a call with no name gets a plain answer that the Trace tab shows."""
    from agno.tools.function import FunctionCall

    from launchkit.tools.catalogue import forgiving
    from launchkit.agents.main_agent import loose

    trace, calls = Trace(), []

    def run_tool(name: str, inputs: dict) -> str:
        """Run a tool from the catalogue by name, with its inputs as an object."""
        calls.append((name, inputs))
        return "ok"

    door = loose([forgiving(run_tool, trace)])[0]
    door.process_entrypoint(strict=False)
    assert door.name == "run_tool" and door.parameters["required"] == ["name", "inputs"]
    for arguments in ({"name": "crop", "inputs": {"width": 1080}}, {"name": "crop", "width": 1080}, {"width": 1080, "height": 1080}):
        FunctionCall(function=door, arguments=arguments).execute()
    assert calls == [("crop", {"width": 1080}), ("crop", {"width": 1080})]
    assert [e.kind for e in trace.events] == ["refused"]


def test_the_agent_with_the_doors_makes_one_tool_call_at_a_time(settings, monkeypatch):
    """Several tool calls in one model message lose run_tool's name, so once run_tool is a door the model calls tools
    one at a time. The model the caller passed in is left as it was."""
    from agno.models.openai import OpenAIChat

    from launchkit.tools.catalogue import Catalogue
    from launchkit.agents.prompt import ContextBuilder
    from launchkit.agents.main_agent import build_main_agent
    from launchkit.brands.workspace import load_workspace

    trace = Trace()
    monkeypatch.setattr(Catalogue, "lookup", property(lambda self: True))
    catalogue = build_catalogue(settings, trace, NO)
    model = OpenAIChat(id="gpt-4.1-mini", api_key="none")
    agent = build_main_agent(load_workspace("harbor", settings, trace), ContextBuilder(settings.budgets), model, settings, trace, catalogue)
    assert agent.model.request_params == {"parallel_tool_calls": False} and model.request_params is None


def test_a_words_only_change_keeps_the_posters_picture(settings):
    """As in Session 1: the same image prompt keeps the poster's picture, so a shorter headline makes no new picture.
    A changed image prompt reworks the picture the conversation has, starting from it."""
    from launchkit.agents.main_agent import make_picture
    from launchkit.brands.workspace import load_workspace
    from launchkit.guardrails.poster_check import PosterSpec
    from launchkit.memory.attached_pictures import Pictures

    trace, pictures = Trace(), Pictures(settings, "harbor", "maya", "keep")
    ws = load_workspace("harbor", settings, trace)
    catalogue = build_catalogue(settings, trace, NO, ws=ws, pictures=pictures)
    first = PosterSpec(headline="Tidal Awaits Dawn", subheadline="s", body="b", image_prompt="a bottle on a lakeshore")
    assert make_picture(first, catalogue, trace, pictures, settings, ws) is None
    made = pictures.last_poster()["file"]

    shorter = first.model_copy(update={"headline": "Tidal Dawn"})
    assert make_picture(shorter, catalogue, trace, pictures, settings, ws) == Path(made)
    assert len(trace.tool_calls("generate_image")) == 1
    assert [e.detail["status"] for e in trace.events if e.kind == "picture"] == ["reused"]

    new_scene = first.model_copy(update={"image_prompt": "a bottle on a beach"})
    make_picture(new_scene, catalogue, trace, pictures, settings, ws)
    assert len(trace.tool_calls("generate_image")) == 2
    assert [e.detail["status"] for e in trace.events if e.kind == "picture"] == ["reused", "rework"]
    assert pictures.last_poster()["image_prompt"] == "a bottle on a beach"


def test_the_picture_request_names_colours_as_colours():
    """Brand colours reach the image model as colours only, so a colour named sea glass is not drawn as glass."""
    from launchkit.adapters.image_providers import picture_prompt

    asked = picture_prompt("an insulated steel bottle on a misty lakeshore", {"navy": "#1F3A5F", "sea_glass": "#A8D5BA"})
    assert "as colours only, not materials or objects: navy #1F3A5F, sea glass #A8D5BA" in asked
    assert picture_prompt("a bottle", {}).startswith("a bottle. The product is plain")


def test_an_unreachable_model_proxy_stops_at_once(settings, monkeypatch):
    """With the VPN off, KeyValue's proxy does not answer. The run stops in seconds and says why, not after minutes."""
    import time

    import pytest
    from agno.exceptions import ModelProviderError

    from launchkit.adapters.models import check_reachable, resolve_model

    monkeypatch.setenv("LITELLM_API_KEY", "test")
    monkeypatch.setenv("LITELLM_BASE_URL", "http://127.0.0.1:9/v1")
    model = resolve_model(replace(settings, model="openai:gpt-4.1-mini"), Trace())
    started = time.time()
    with pytest.raises(ModelProviderError, match="Is the VPN on"):
        check_reachable(model)
    assert time.time() - started < 5


def test_saved_sizes_are_named_to_the_agent(settings):
    """A size the tools save joins the conversation's list by its real name, so a later turn can put it on the brief.
    The picture tools still work on the poster, not on the size."""
    from launchkit.memory.attached_pictures import Pictures

    pictures = Pictures(settings, "harbor", "maya", "sizes")
    poster = pictures.attach(APPROVED)
    pictures.size_made(settings.data_dir / "sizes" / "tidal-poster-crop-1080x1080-ab12.png")
    assert pictures.newest() == poster
    assert "tidal-poster-crop-1080x1080-ab12.png" in pictures.describe()


def test_a_fake_run_that_worked_prints_no_parse_warnings(settings, trace, request_for, caplog):
    """A fake reply comes in the answer shape the main agent asks for, so a run that worked shows no warnings."""
    import logging

    from launchkit.adapters.fakes import ToolsModel

    with caplog.at_level(logging.WARNING):
        result = run_main(request_for(text="Morning!"), settings=settings, model=ToolsModel(), trace=trace, approve=NO)
    assert result.reply == "Morning, Maya. What do you need today?"
    assert not [r for r in caplog.records if "pars" in r.getMessage().lower() or "output_schema" in r.getMessage()]


def test_the_chat_page_accepts_only_plain_user_names(settings, monkeypatch):
    """A user name becomes a folder under data/, so the page refuses one with ../ in it and writes nothing."""
    import io

    from fastapi.testclient import TestClient
    from PIL import Image

    import launchkit.web.app as web

    monkeypatch.setattr(web, "settings", settings)
    page = TestClient(web.app)
    picture = io.BytesIO()
    Image.new("RGB", (8, 8)).save(picture, "PNG")
    sent = {"workspace_id": "harbor", "user_id": "../../../escaped", "session_id": "abc123"}
    assert page.post("/attach", data=sent, files={"picture": ("p.png", picture.getvalue())}).status_code == 422
    assert page.post("/run", json={"workspace_id": "harbor", "user_id": "../x", "text": "hi"}).status_code == 422
    assert not list(settings.data_dir.parent.glob("**/escaped"))
    assert page.post("/attach", data={**sent, "user_id": "maya"}, files={"picture": ("p.png", picture.getvalue())}).status_code == 200


def test_a_poster_uses_the_photo_the_marketer_attached(settings):
    """Maya attached her own photo: a poster uses it and pays for no new picture."""
    from launchkit.agents.main_agent import make_picture
    from launchkit.guardrails.poster_check import PosterSpec
    from launchkit.memory.attached_pictures import Pictures
    from types import SimpleNamespace

    from launchkit.tools.catalogue import Entry

    pictures = Pictures(settings, "harbor", "maya", "abc123")
    photo = pictures.attach(APPROVED)
    drawn = []
    catalogue = SimpleNamespace(entries={"generate_image": Entry("generate_image", "make a new poster picture", "read", lambda image_prompt: drawn.append(image_prompt))})
    spec = PosterSpec(headline="Calm water", subheadline="Ready for the trail", body="Cold for 24 hours.", image_prompt="a bottle by a lake")
    trace = Trace()
    assert make_picture(spec, catalogue, trace, pictures) == photo
    assert drawn == [] and trace.events[-1].detail["status"] == "kept"
