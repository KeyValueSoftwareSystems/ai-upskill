"""The main agent: one agent talking with Maya. It decides what each request needs and uses its tools.

Session 1's harness ran a fixed order, copy agent then picture agent. Here one agent decides. Same DNA, same
leash, same sessions. It holds get_brand_details and generate_image, and every tool the room builds after them.
"""

import re
import time
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Literal

from agno.agent import Agent
from agno.tools.function import Function

from launchkit.adapters.images import make_images
from launchkit.adapters.models import model_name, resolve_model
from launchkit.harness.agent import session_db
from launchkit.harness.brand import make_get_brand_details
from launchkit.harness.catalogue import Catalogue, Entry, ask_in_terminal
from launchkit.harness.context import ContextBuilder
from launchkit.harness.limits import make_leash
from launchkit.harness.picture_tools import PictureDesk
from launchkit.harness.request import Request, resolve_workspace_id
from pydantic import BaseModel, Field

from launchkit.harness.run import history_size, looked_up, raise_if_failed, tool_result_size
from launchkit.harness.spec import PosterSpec, SpecError, repair_message, validate_spec
from launchkit.harness.tools import make_generate_image
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import Workspace, load_workspace
from launchkit.settings import settings as default_settings

MAIN_TASK = """You work for the marketer you are talking with. Decide what each request needs and use your tools for it.
Brand and product facts come only from get_brand_details. Answer in plain words, in the brand's voice."""

MAIN_STEP_CAP = 12


class MainTurn(BaseModel):
    """Session 1's answer shape, worded for an agent that does many jobs, not only posters."""

    kind: Literal["poster", "reply"] = Field(description="poster only when this answer is a poster's words: a headline, subheadline and body. reply for everything else: a greeting, a question, research, sizes, board work, any other job.")
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


def placements_text(ws) -> str:
    sizes = [f"{name} {size}" for name, group in ws.rules.get("placements", {}).items() for size in group]
    return "This brand's placements (every size): " + ", ".join(sizes) + "." if sizes else ""


def build_main_agent(ws, ctx: ContextBuilder, model, settings, trace: Trace, catalogue: Catalogue) -> Agent:
    ctx.set("rules", f"{ws.soul}\n\n{ws.agents}\n\n{placements_text(ws)}")
    ctx.set("facts", f"Today is {date.today():%-d %B %Y}.")
    ctx.set("task", MAIN_TASK)
    return Agent(
        model=model,
        system_message=ctx.render(),
        output_schema=MainTurn,
        db=session_db(settings),
        add_history_to_context=True,
        num_history_runs=5,
        tools=loose(catalogue.agent_tools()),
        tool_hooks=[make_leash(replace(settings.limits, step_cap=MAIN_STEP_CAP), trace)],
        telemetry=False,
    )


def build_catalogue(settings, trace: Trace, approve, board=None, model=None, ws: Workspace | None = None) -> Catalogue:
    ws = ws or load_workspace("harbor", settings, trace)
    entries: list[Entry] = [
        Entry("get_brand_details", "look up this brand's guide and product facts", "read", make_get_brand_details(ws, trace, settings)),
        Entry("generate_image", "make a new poster picture from a scene description", "read", make_generate_image(make_images(settings), ws.colours, trace)),
        *PictureDesk(settings, ws.colours, trace, model).entries(),
    ]
    return Catalogue(entries, trace, approve)


def run_main(req: Request, *, settings=default_settings, model=None, trace: Trace | None = None, approve=ask_in_terminal, board=None) -> MainResult:
    trace = trace if trace is not None else Trace()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    wid = resolve_workspace_id(req, settings)
    ws = load_workspace(wid, settings, trace)
    model = model if model is not None else resolve_model(settings, trace)
    catalogue = build_catalogue(settings, trace, approve, board, model, ws)
    agent = build_main_agent(ws, ContextBuilder(settings.budgets), model, settings, trace, catalogue)
    started = time.perf_counter()
    session = f"{wid}:{req.user_id}:{req.session_id}:main"
    run = agent.run(req.text, session_id=session, user_id=req.user_id)
    raise_if_failed(run)
    trace.model("main", model_name(model), run.metrics)
    result = MainResult(trace=trace, runs=[run])
    turn = main_turn(run.content)
    if turn.kind == "poster" and turn.spec is not None:
        turn.spec = checked_spec(turn.spec, agent, session, req, ws, model, trace, result)
    result.spec = turn.spec
    result.reply = turn.reply or (poster_words(turn.spec) if turn.spec else "")
    result.seconds = time.perf_counter() - started
    result.view_tokens = tool_result_size(run)[0]
    result.history_tokens = history_size(run)[0]
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
        out.append(f)
    return out
