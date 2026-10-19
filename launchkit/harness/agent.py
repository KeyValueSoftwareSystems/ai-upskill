from agno.agent import Agent
from agno.db.sqlite import SqliteDb

from launchkit.harness.context import ContextBuilder
from launchkit.harness.limits import make_leash
from launchkit.harness.spec import PosterSpec, Turn
from launchkit.harness.tools import make_generate_image
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import Workspace

SPEC_TASK = """You are talking with a marketer. Decide what kind of turn this is.
If they ask for a poster, or to change, improve or redo any part of a poster from earlier in this conversation (its words, its picture, its sky, its mood): kind is "poster", and the spec is the whole poster with that change made. Never describe what you would change; make the change.
Fill every field of the spec. Headline up to 6 words, subheadline up to 12, body up to 25. format is portrait or square.
The image_prompt describes only the picture: subject, setting, light, colours. It contains no words to print.
Otherwise, for a greeting, a question or small talk: kind is "reply", with a short helpful answer in the brand's voice. No spec."""

PICTURE_TASK = """Make the poster picture. Call generate_image once with the scene description you were given.
When the tool returns a file, reply with that file path and nothing else."""


def session_db(settings) -> SqliteDb:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return SqliteDb(db_file=str(settings.data_dir / "sessions.db"))


def build_copy_agent(ws: Workspace, ctx: ContextBuilder, model, settings, trace: Trace) -> Agent:
    ctx.set("rules", f"{ws.soul}\n\n{ws.agents}")
    ctx.set("task", SPEC_TASK)
    return Agent(
        model=model,
        system_message=ctx.render(),
        output_schema=Turn,
        db=session_db(settings),
        add_history_to_context=True,
        num_history_runs=5,
        tool_hooks=[make_leash(settings.limits, trace)],
        telemetry=False,
    )


def build_picture_agent(spec: PosterSpec, model, images, colours: dict, trace: Trace, settings) -> Agent | None:
    return Agent(
        model=model,
        system_message=PICTURE_TASK,
        tools=[make_generate_image(images, colours, trace)],
        tool_hooks=[make_leash(settings.limits, trace)],
        telemetry=False,
    )
