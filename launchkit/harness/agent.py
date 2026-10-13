from agno.agent import Agent
from agno.db.sqlite import SqliteDb

from launchkit.harness.context import ContextBuilder
from launchkit.harness.spec import PosterSpec
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import Workspace

SPEC_TASK = """Write the words for one poster ad from the marketer's request.
Fill every field of the form. Headline up to 6 words, subheadline up to 12, body up to 25.
The image_prompt describes only the picture: subject, setting, light, colours. It contains no words to print."""

PICTURE_TASK = """Make the poster picture. Call generate_image once with the scene description you were given.
When the tool returns a file, reply with that file path and nothing else."""


def session_db(settings) -> SqliteDb:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return SqliteDb(db_file=str(settings.data_dir / "sessions.db"))


def build_copy_agent(ws: Workspace, ctx: ContextBuilder, model, settings) -> Agent:
    # TODO step 1: ctx.set("rules", ws.soul followed by ws.agents)
    ctx.set("task", SPEC_TASK)
    return Agent(
        model=model,
        system_message=ctx.render(),
        output_schema=PosterSpec,
        db=session_db(settings),
        add_history_to_context=True,
        num_history_runs=3,
        telemetry=False,
    )


def build_picture_agent(spec: PosterSpec, model, images, colours: dict, trace: Trace, settings) -> Agent | None:
    # TODO step 3: an Agent with tools=[make_generate_image(images, colours, trace)] and tool_hooks=[make_leash(settings.limits, trace)]
    return None
