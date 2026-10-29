"""The main agent: one agent talking with Maya. It decides what each request needs and uses its tools.

Session 1's harness ran a fixed order, copy agent then picture agent. Here one agent decides. Same DNA, same
leash, same sessions. It holds get_brand_details and generate_image, and every tool the room builds after them.
"""

import time
from dataclasses import dataclass, field, replace

from agno.agent import Agent

from launchkit.adapters.images import make_images
from launchkit.adapters.models import model_name, resolve_model
from launchkit.harness.agent import session_db
from launchkit.harness.brand import make_get_brand_details
from launchkit.harness.catalogue import Catalogue, Entry, ask_in_terminal
from launchkit.harness.context import ContextBuilder
from launchkit.harness.limits import make_leash
from launchkit.harness.picture_tools import PictureDesk
from launchkit.harness.request import Request, resolve_workspace_id
from launchkit.harness.run import history_size, raise_if_failed, tool_result_size
from launchkit.harness.tools import make_generate_image
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import Workspace, load_workspace
from launchkit.settings import settings as default_settings

MAIN_TASK = """You work for the marketer you are talking with. Decide what each request needs and use your tools for it.
Brand and product facts come only from get_brand_details. Answer in plain words, in the brand's voice."""

MAIN_STEP_CAP = 12


@dataclass
class MainResult:
    reply: str = ""
    trace: Trace = field(default_factory=Trace)
    runs: list = field(default_factory=list)
    seconds: float = 0.0
    view_tokens: int = 0
    history_tokens: int = 0


def build_main_agent(ws, ctx: ContextBuilder, model, settings, trace: Trace, catalogue: Catalogue) -> Agent:
    ctx.set("rules", f"{ws.soul}\n\n{ws.agents}")
    ctx.set("task", MAIN_TASK)
    return Agent(
        model=model,
        system_message=ctx.render(),
        db=session_db(settings),
        add_history_to_context=True,
        num_history_runs=5,
        tools=catalogue.agent_tools(),
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
    run = agent.run(req.text, session_id=f"{wid}:{req.user_id}:{req.session_id}:main", user_id=req.user_id)
    raise_if_failed(run)
    result = MainResult(reply=str(run.content or ""), trace=trace, runs=[run], seconds=time.perf_counter() - started)
    trace.model("main", model_name(model), run.metrics)
    result.view_tokens = tool_result_size(run)[0]
    result.history_tokens = history_size(run)[0]
    return result
