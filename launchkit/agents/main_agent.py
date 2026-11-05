"""The main agent: one agent talking with Maya. It decides what each request needs and uses its tools.

Session 1's harness ran a fixed order, copy agent then picture agent. Here one agent decides. Same DNA, same
leash, same sessions. It holds get_brand_details and generate_image, and every tool the room builds after them.
"""

import inspect
import re
import time
from pathlib import Path
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Literal

from agno.agent import Agent
from agno.memory import MemoryManager
from agno.models.openai import OpenAIChat
from agno.session.summary import SessionSummaryManager
from agno.tools.function import Function

from launchkit.adapters.fakes import FakeModel
from launchkit.adapters.image_providers import FromPicture, make_images
from launchkit.adapters.models import check_reachable, model_name, resolve_model
from launchkit.agents.prompt import ContextBuilder, approx_tokens
from launchkit.brands.request import Request, resolve_workspace_id
from launchkit.guardrails.limits import make_leash
from launchkit.mcp.client import closes_its_mcp_links
from launchkit.mcp.servers import server_entries
from launchkit.memory.attached_pictures import Pictures
from launchkit.memory.chat_history import session_db
from launchkit.memory.compaction import conversation_text
from launchkit.memory.index import memory_index, recall
from launchkit.memory.long_term import MEMORY_SHARE, MEMORY_TASK, MemoryDb, memory_db, memories_for, memory_text, what_was_kept, write_rules
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
Never say something is made, cut, attached or posted unless a tool did it in this turn.
When the marketer asks for sizes, a picture or a voice-over, they want files a tool makes, not text in your reply. Sizes are the picture in this conversation cut to each of the brand's placements, one file each.
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


def build_main_agent(ws, ctx: ContextBuilder, model, settings, trace: Trace, catalogue: Catalogue, pictures: Pictures | None = None,
                     db=None, memory: str = "", conversation: str = "") -> Agent:
    ctx.set("rules", f"{ws.soul}\n\n{ws.agents}\n\n{placements_text(ws)}")
    ctx.set("memory", memory)
    ctx.set("conversation", conversation)
    warnings = " ".join(e.detail["text"] for e in trace.events if e.kind == "warning")
    ctx.set("facts", f"Today is {date.today():%-d %B %Y}. {warnings} {pictures.describe() if pictures else ''}".strip())
    ctx.set("task", MAIN_TASK if catalogue.lookup else "\n\n".join(part for part in (DIRECT_TASK, catalogue.skills_text()) if part))
    summariser = model  # before parallel_tool_calls is set: see the session summary below
    if catalogue.lookup and isinstance(model, OpenAIChat):
        # Several tool calls in one model message lose run_tool's name, so the agent with the doors calls one at a time.
        model = replace(model, request_params={**(model.request_params or {}), "parallel_tool_calls": False})
    agent = Agent(
        model=model,
        system_message=ctx.render(),
        output_schema=MainTurn,
        db=db if db is not None else session_db(settings),
        add_history_to_context=True,
        num_history_runs=5,
        enable_agentic_memory=True,
        memory_manager=MemoryManager(memory_capture_instructions=write_rules(), delete_memories=False),
        tools=loose(catalogue.agent_tools()),
        tool_hooks=[make_leash(replace(settings.limits, step_cap=MAIN_STEP_CAP), trace)],
        telemetry=False,
    )
    if agent.enable_session_summaries:
        # The summary call sends no tools, and the proxy refuses parallel_tool_calls without tools, so the summary is
        # written by the model as given. Passed to Agent(...), a summary manager would switch summaries on by itself.
        agent.session_summary_manager = SessionSummaryManager(model=summariser)
    if isinstance(db, MemoryDb):
        agent.tool_hooks.append(what_was_kept(db))  # after the leash, so the trace line shows what the agent is told
    if agent.enable_agentic_memory:
        # Agno tells the model about update_user_memory in the system message it builds itself. LaunchKit writes its
        # own, so the harness says it: first in the Task section, as the one step before find_tool, and in the Memory
        # section for a row that is already kept but now for everyone.
        ctx.set("task", f"{MEMORY_TASK}\n{ctx.sections['task']}")
        ctx.set("memory", "\n\n".join(part for part in (MEMORY_SHARE, ctx.sections.get("memory", "")) if part))
        agent.system_message = ctx.render()
    return agent


def build_catalogue(settings, trace: Trace, approve, board=None, model=None, ws: Workspace | None = None, user: str = "maya", pictures: Pictures | None = None,
                    memories: list | None = None) -> Catalogue:
    ws = ws or load_workspace("harbor", settings, trace)
    desk = PictureDesk(settings, ws.colours, trace, model, pictures.newest if pictures else None, pictures.size_made if pictures else None)
    entries: list[Entry] = [
        Entry("get_brand_details", "look up this brand's guide and product facts", "read", make_get_brand_details(ws, trace, settings)),
        Entry("generate_image", "make a new poster picture from a scene description, only when no photo is given", "read", make_generate_image(make_images(settings), ws.colours, trace, pictures.made if pictures else None)),
        *desk.entries(),
        Entry("check_copy", "check a headline, subheadline and body against the brand's word limits and banned claims", "read", make_check_copy(ws)),
        search_entry(settings),
        describe_image_entry(settings, model, desk),
        text_to_speech_entry(settings, model),
        *(board.entries() if board else server_entries(settings, trace, user)),
        *make_research_entries(model, settings, trace),
        *recall_entries(memories or []),
    ]
    catalogue = Catalogue(entries, load_skills(), trace, approve)
    catalogue.leash = make_leash(replace(settings.limits, step_cap=10_000), trace)
    return catalogue


@closes_its_mcp_links
def run_main(req: Request, *, settings=default_settings, model=None, trace: Trace | None = None, approve=ask_in_terminal, board=None, attach=()) -> MainResult:
    trace = trace if trace is not None else Trace()
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
    db = memory_db(settings, wid, req.user_id, trace, approve)
    rows = memories_for(db, wid, req.user_id)
    memory = memory_index(rows) if built(memory_index) else memory_text(rows)
    session = f"{wid}:{req.user_id}:{req.session_id}:main"
    catalogue = build_catalogue(settings, trace, approve, board, model, ws, req.user_id, pictures, rows)
    agent = build_main_agent(ws, ContextBuilder(settings.budgets), model, settings, trace, catalogue, pictures, db, memory, conversation_text(db, session))
    started = time.perf_counter()
    run = agent.run(req.text, session_id=session, user_id=req.user_id)
    raise_if_failed(run)
    trace.model("main", model_name(model), run.metrics)
    result = MainResult(trace=trace, runs=[run])
    turn = main_turn(run.content)
    if turn.kind == "poster" and turn.spec is not None:
        turn.spec = checked_spec(turn.spec, agent, session, req, ws, model, trace, result)
    result.spec = turn.spec
    if turn.spec is not None and not any(trace.tool_calls(name) for name in PICTURE_WORK):
        kept = make_picture(turn.spec, catalogue, trace, pictures, settings, ws)
        if kept is not None:
            result.kept.append(kept)
    result.reply = turn.reply or (poster_words(turn.spec) if turn.spec else "")
    result.seconds = time.perf_counter() - started
    result.view_tokens = tool_result_size(run)[0]
    result.history_tokens = history_size(run)[0]
    result.memory_tokens = approx_tokens(memory)
    return result


def recall_entries(rows: list) -> list[Entry]:
    """The lookup behind the Memory index: once memory hands-on 2, part A builds recall, the agent reads one topic's
    full facts."""
    if not built(recall) or not rows:
        return []

    def recall_topic(topic: str) -> str:
        """Read every fact kept under one topic of the Memory index, in full."""
        return recall(rows, topic)

    recall_topic.__name__ = "recall"
    return [Entry("recall", "read the full facts kept under one topic named in the Memory index", "read", recall_topic)]


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
    return looked_up(trace) | pages


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


def make_picture(spec: PosterSpec, catalogue: Catalogue, trace: Trace, pictures: Pictures | None = None, settings=None, ws=None) -> Path | None:
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
        fn = make_generate_image(FromPicture(make_images(settings), Path(last["file"])), ws.colours, trace, pictures.made)
    made = fn(spec.image_prompt)
    trace.tool("generate_image", {"image_prompt": spec.image_prompt}, made)
    if pictures is not None:
        pictures.mark_poster(Path(made["file"]), spec.image_prompt)
    return None
