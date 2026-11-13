"""The main agent: one agent talking with Maya. It decides what each request needs and uses its tools.

Session 1's harness ran a fixed order, copy agent then picture agent. Here one agent decides. Same DNA, same
leash, same sessions. It holds get_brand_details and generate_image, and every tool the room builds after them.
"""

import inspect
import re
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Literal

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.function import Function

from launchkit.adapters.fakes import FakeModel
from launchkit.adapters.image_providers import FromPicture, make_images
from launchkit.adapters.models import check_reachable, model_name, resolve_model
from launchkit.agents.prompt import ContextBuilder
from launchkit.brands.request import Request, resolve_workspace_id
from launchkit.guardrails.limits import make_leash
from launchkit.knowledge.brand_facts import make_get_brand_facts
from launchkit.mcp.client import closes_its_mcp_links
from launchkit.mcp.servers import server_entries
from launchkit.files.workspace import for_request
from launchkit.memory.attached_pictures import Pictures
from launchkit.memory.chat_history import session_db
from launchkit.memory.long_term import memory_changes, memory_manager, memory_text, summary_manager, summary_text, user_memories
from launchkit.memory.scope import held_back
from launchkit.tools.save_memory import memory_entries
from launchkit.tools.list_files import make_list_files
from launchkit.tools.read_file import make_read_file
from launchkit.tools.search_files import make_search_files
from launchkit.tools.write_file import make_write_file
from launchkit.tools.catalogue import Catalogue, Entry, ask_in_terminal, built, load_skills
from launchkit.tools.check_copy import make_check_copy
from launchkit.tools.describe_image import describe_image_entry
from launchkit.tools.get_brand_details import make_get_brand_details
from launchkit.tools.resize_poster import PictureDesk
from launchkit.tools.text_to_speech import text_to_speech_entry
from pydantic import BaseModel, Field

from launchkit.agents.poster_flow import history_size, looked_up, raise_if_failed, tool_result_size
from launchkit.brands.workspace import Workspace, load_workspace
from launchkit.guardrails.poster_check import PosterSpec, SpecError, repair_message, validate_spec
from launchkit.orchestration.research_team import make_research_entries
from launchkit.settings import settings as default_settings
from launchkit.tools.generate_image import make_generate_image
from launchkit.tools.search_web import search_entry
from launchkit.trace import Trace

MAIN_TASK = """You work for the marketer you are talking with. For any job beyond a greeting, call find_tool first, with the
marketer's own words. It lists skills and tools, not answers: call it once for the whole job, not once per item.
Each new ask is a new job: call find_tool for it, even when an earlier turn loaded a skill.
If nothing it lists fits the job, search again with other words before you answer.
When find_tool lists a skill for the job, load it once with run_skill before you call any tool, and do the job the way its steps say, not another way.
Call tools only through run_tool, as run_tool(name, inputs) with every input inside inputs, e.g.
run_tool("<a tool find_tool listed>", {"<input>": "..."}).
Every job beyond a greeting is done with the skills and tools find_tool lists, never from your own knowledge. A question is a job too: you know nothing about this season, the web or the competitors until a tool tells you.
This conversation has a workspace of files, and everything you have made for the marketer is kept there. Save finished work with write_file in outputs/ and drafts in work/. Before you answer from memory or ask the marketer to send something again, look in the workspace with list_files, search_files and read_file. A brief, plan, draft or document is a file there, not a card on the board.
Never say something is made, cut, attached or posted unless a tool did it in this turn.
When the marketer asks for sizes, a picture or a voice-over, they want files a tool makes, not text in your reply. Sizes are the picture in this conversation cut to each of the brand's placements, one file each.
When the marketer tells you how they like to work and it will matter in a later conversation, call run_tool("save_memory", {"note": "..."}); a new value for a brand fact, such as the warranty, goes to propose_brand_fact. Every memory write asks the marketer first.
Answer in plain words, in the brand's voice."""

DIRECT_TASK = """You work for the marketer you are talking with. Decide what each request needs and use your tools for it.
When a skill below fits the job, load it once with run_skill before you call any other tool, and do the job the way its steps say, not another way.
Brand and product facts come only from get_brand_details. Answer in plain words, in the brand's voice."""

MAIN_STEP_CAP = 20


class MainTurn(BaseModel):
    """Session 1's answer shape, worded for an agent that does many jobs, not only posters."""

    kind: Literal["poster", "reply"] = Field(description="poster only when the marketer asks for a whole poster or a change to one: then the answer is its headline, subheadline and body. reply for everything else: a headline, tagline or single line on its own, a greeting, a question, research, sizes (also a photo cut to a size), sound, board work, any other job.")
    reply: str | None = Field(default=None, description="When kind is reply: your answer to the marketer, in the brand's voice. Otherwise null.")
    spec: PosterSpec | None = Field(default=None, description="When kind is poster: the filled poster form. Otherwise null.")


@dataclass
class MainResult:
    reply: str = ""
    spec: PosterSpec | None = None
    trace: Trace = field(default_factory=Trace)
    runs: list = field(default_factory=list)
    seconds: float = 0.0
    view_tokens: int = 0
    history_tokens: int = 0
    memory_tokens: int = 0
    kept: list[Path] = field(default_factory=list)


def placements_text(ws) -> str:
    sizes = [f"{name} {size}" for name, group in ws.rules.get("placements", {}).items() for size in group]
    return "This brand's placements (every size): " + ", ".join(sizes) + "." if sizes else ""


def build_main_agent(ws, ctx: ContextBuilder, model, settings, trace: Trace, catalogue: Catalogue, pictures: Pictures | None = None, user_id: str = "", session_id: str = "") -> Agent:
    ctx.set("rules", f"{ws.soul}\n\n{ws.agents}\n\n{placements_text(ws)}")
    warnings = " ".join(e.detail["text"] for e in trace.events if e.kind == "warning")
    ctx.set("facts", f"Today is {date.today():%-d %B %Y}. {warnings} {pictures.describe() if pictures else ''}".strip())
    ctx.set("task", MAIN_TASK if catalogue.lookup else "\n\n".join(part for part in (DIRECT_TASK, catalogue.skills_text()) if part))
    if catalogue.lookup and isinstance(model, OpenAIChat):
        # Several tool calls in one model message lose run_tool's name, so the agent with the doors calls one at a time.
        model = replace(model, request_params={**(model.request_params or {}), "parallel_tool_calls": False})
    # Ticket 3: a row that names a brand fact is held back. Brand facts come from the brand's files and get_brand_facts.
    rows = memory_text([m for m in user_memories(session_db(settings), user_id) if not held_back(m.memory, settings)])
    ctx.set("memory", "\n\n".join(part for part in (summary_text(settings, session_id), rows) if part))
    return Agent(
        model=model,
        system_message=ctx.render(),
        output_schema=MainTurn,
        db=session_db(settings),
        add_history_to_context=True,
        num_history_runs=3,
        # Ticket 5: a running summary of the older turns, on the cheaper model. The fakes are scripted for the conversation only.
        session_summary_manager=summary_manager(settings, trace, model) if model is not None and not isinstance(model, FakeModel) else None,
        # Ticket 4: no write after every run and no learning tools beside the three doors. Every memory write is a
        # catalogue tool of kind "write", so it goes through run_tool and asks first.
        update_memory_on_run=False,
        tools=loose(catalogue.agent_tools()),
        tool_hooks=[make_leash(replace(settings.limits, step_cap=MAIN_STEP_CAP), trace)],
        telemetry=False,
    )


def build_catalogue(settings, trace: Trace, approve, board=None, model=None, ws: Workspace | None = None, user: str = "maya", pictures: Pictures | None = None, files=None, message: str = "") -> Catalogue:
    ws = ws or load_workspace("harbor", settings, trace)
    file_tools = [make_read_file(files, trace), make_list_files(files, trace), make_write_file(files, trace, message), make_search_files(files, trace)] if files is not None else []
    outputs = files.drawer("outputs") if files is not None else None
    desk = PictureDesk(settings, ws.colours, trace, model, pictures.newest if pictures else None, pictures.size_made if pictures else None, files)
    entries: list[Entry] = [
        Entry("get_brand_details", "look up this brand's guide and product facts", "read", make_get_brand_details(ws, trace, settings)),
        Entry("get_brand_facts", "this brand's facts that change over time, true today: warranty, prices, launch dates", "read", make_get_brand_facts(settings, ws)),
        Entry("generate_image", "make a new poster picture from a scene description, only when no photo is given", "read", make_generate_image(make_images(settings, outputs), ws.colours, trace, pictures.made if pictures else None)),
        *desk.entries(),
        Entry("check_copy", "check a headline, subheadline and body against the brand's word limits and banned claims", "read", make_check_copy(ws)),
        search_entry(settings),
        describe_image_entry(settings, model, desk),
        text_to_speech_entry(settings, model, files),
        *(board.entries() if board else server_entries(settings, trace, user)),
        *file_tools,
        *make_research_entries(model, settings, trace, write=(lambda: make_write_file(files, trace, message).fn) if files is not None else None),
        *memory_entries(settings, lambda: memory_manager(settings, trace, model), user, namespace=ws.id),
    ]
    catalogue = Catalogue(entries, load_skills(), trace, approve)
    catalogue.leash = make_leash(replace(settings.limits, step_cap=10_000), trace)
    return catalogue


@closes_its_mcp_links
def run_main(req: Request, *, settings=default_settings, model=None, trace: Trace | None = None, approve=ask_in_terminal, board=None, attach=()) -> MainResult:
    trace = trace if trace is not None else Trace()
    trace.message = trace.message or uuid.uuid4().hex[:8]
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    wid = resolve_workspace_id(req, settings)
    ws = load_workspace(wid, settings, trace)
    model = model if model is not None else resolve_model(settings, trace)
    check_reachable(model)
    if isinstance(model, FakeModel):
        # The fakes are scripted against the saved pages and the local board, so a fake never reaches the live web or Notion.
        settings = replace(settings, search="saved", board="local")
    pictures = Pictures(settings, wid, req.user_id, req.session_id)
    for picture in attach:
        trace.note(f"attached {Path(picture).name} to this conversation")
        pictures.attach(Path(picture))
    files = for_request(req, settings)
    catalogue = build_catalogue(settings, trace, approve, board, model, ws, req.user_id, pictures, files, message=uuid.uuid4().hex[:8])
    ctx = ContextBuilder(settings.budgets)
    session = f"{wid}:{req.user_id}:{req.session_id}:main"
    agent = build_main_agent(ws, ctx, model, settings, trace, catalogue, pictures, req.user_id, session)
    before = user_memories(session_db(settings), req.user_id)
    held = [m for m in before if held_back(m.memory, settings)]
    trace.memory("loaded", rows=len(before) - len(held), held=len(held), tokens=next(r["tokens"] for r in ctx.report() if r["section"] == "memory"), by=settings.memory_model if built(memory_manager) and not isinstance(model, FakeModel) else model_name(model))
    started = time.perf_counter()
    run = agent.run(req.text, session_id=session, user_id=req.user_id)
    raise_if_failed(run)
    trace.model("main", model_name(model), run.metrics)
    changes = memory_changes(before, user_memories(session_db(settings), req.user_id))
    for change, text in changes:
        trace.memory(change, text=text)
    if not changes:
        trace.memory("none")
    result = MainResult(trace=trace, runs=[run])
    turn = main_turn(run.content)
    if turn.kind == "poster" and turn.spec is not None:
        turn.spec = checked_spec(turn.spec, agent, session, req, ws, model, trace, result)
    result.spec = turn.spec
    if turn.spec is not None and not any(trace.tool_calls(name) for name in PICTURE_WORK):
        kept = make_picture(turn.spec, catalogue, trace, pictures, settings, ws, files)
        if kept is not None:
            result.kept.append(kept)
    result.reply = turn.reply or (poster_words(turn.spec) if turn.spec else "")
    result.seconds = time.perf_counter() - started
    result.view_tokens = tool_result_size(run)[0]
    result.history_tokens = history_size(run)[0]
    result.memory_tokens = next(r["tokens"] for r in ctx.report() if r["section"] == "memory")
    return result


def main_turn(content) -> MainTurn:
    """The main agent's answer: a reply, or a poster spec. Plain text counts as a reply."""
    if isinstance(content, MainTurn):
        return content
    if isinstance(content, dict):
        return MainTurn.model_validate(content)
    try:
        return MainTurn.model_validate_json(str(content or ""))
    except ValueError:
        return MainTurn(kind="reply", reply=str(content or ""))


def found(trace: Trace) -> set[str]:
    """What the agent may cite: brand sections get_brand_details returned, and pages a tool returned with an address."""
    pages = {a for e in trace.events if e.kind == "tool" for a in re.findall(r"^Address: (\S+)", str(e.detail.get("result", "")), flags=re.M)}
    facts = {ref for e in trace.tool_calls("get_brand_facts") if e.kind == "tool" for ref in re.findall(r"^\[([^\]]+)\]", str(e.detail["result"]), flags=re.M)}
    return looked_up(trace) | pages | facts


def checked_spec(spec: PosterSpec, agent, session: str, req, ws, model, trace: Trace, result) -> PosterSpec:
    """Session 1's check, unchanged: check the words in code, let the model repair once, then stop with a typed error."""
    trace.draft(spec)
    errors = validate_spec(spec, ws.rules, found(trace))
    if not errors:
        return spec
    trace.validation(errors, attempt=1)
    run = agent.run(repair_message(errors), session_id=session, user_id=req.user_id)
    result.runs.append(run)
    raise_if_failed(run)
    trace.model("repair", model_name(model), run.metrics)
    repaired = main_turn(run.content).spec or spec
    errors = validate_spec(repaired, ws.rules, found(trace))
    trace.validation(errors, attempt=2)
    if errors:
        raise SpecError(errors)
    return repaired


def poster_words(spec: PosterSpec) -> str:
    return f"{spec.headline}\n{spec.subheadline}\n{spec.body}"


def loose(tools: list) -> list[Function]:
    """The Turn answer shape makes Agno ask OpenAI for strict tool schemas, and strict schemas refuse run_tool's free-form
    inputs. The answer shape stays strict; the tools do not need to be."""
    out = []
    for fn in tools:
        f = Function.from_callable(fn)
        f.strict = False
        params = inspect.signature(fn).parameters.values()
        if any(p.kind is p.VAR_KEYWORD for p in params):
            # A tool that takes extra fields checks its own inputs: Agno keeps the schema as written and skips its check.
            named = [p.name for p in params if p.kind is not p.VAR_KEYWORD]
            f.parameters["properties"] = {k: v for k, v in f.parameters["properties"].items() if k in named}
            f.parameters["required"] = named
            f.skip_entrypoint_processing = True
        out.append(f)
    return out


# A turn that already made or reworked a picture keeps it: the harness makes one only for a poster with none.
PICTURE_WORK = ("generate_image", "centre_crop", "crop", "expand_canvas", "scale", "describe_image")


def make_picture(spec: PosterSpec, catalogue: Catalogue, trace: Trace, pictures: Pictures | None = None, settings=None, ws=None, files=None) -> Path | None:
    """Session 1's picture phase, kept: a checked poster gets its picture, made from the image prompt, never from the
    words. It joins the conversation, so "now all the sizes" works on it. As in Session 1, the same image prompt keeps
    the poster's picture, and a changed one reworks it. Returns the kept picture, if any."""
    generate = catalogue.entries.get("generate_image")
    if generate is None:
        return None
    last = pictures.last_poster() if pictures is not None else None
    given = [i for i in pictures.all() if i["by"] != "size"] if pictures is not None else []
    if given and given[-1]["by"] == "attached":
        trace.picture("kept", file=given[-1]["file"], reason="the marketer gave this photo, so the poster uses it")
        pictures.mark_poster(Path(given[-1]["file"]), spec.image_prompt)
        return Path(given[-1]["file"])
    if last is not None and last["image_prompt"] == spec.image_prompt:
        trace.picture("reused", file=last["file"], reason="the image prompt did not change")
        return Path(last["file"])
    fn = generate.fn
    if last is not None and settings is not None and ws is not None:
        trace.picture("rework", file=last["file"], reason="the image prompt changed, so the new picture starts from this one")
        fn = make_generate_image(FromPicture(make_images(settings, files.drawer("outputs") if files is not None else None), Path(last["file"])), ws.colours, trace, pictures.made)
    made = fn(spec.image_prompt)
    trace.tool("generate_image", {"image_prompt": spec.image_prompt}, made)
    if pictures is not None:
        pictures.mark_poster(Path(made["file"]), spec.image_prompt)
    return None
