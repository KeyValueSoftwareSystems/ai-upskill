from agno.agent import Agent

from launchkit.agents.prompt import ContextBuilder
from launchkit.brands.workspace import Workspace
from launchkit.guardrails.limits import make_leash
from launchkit.guardrails.poster_check import PosterSpec, Turn
from launchkit.memory.chat_history import session_db
from launchkit.tools.generate_image import make_generate_image
from launchkit.tools.get_brand_details import make_get_brand_details
from launchkit.trace import Trace

SPEC_TASK = """You are talking with a marketer. Decide what kind of turn this is.
If they ask for a poster, or to change, improve or redo any part of a poster from earlier in this conversation (its words, its picture, its sky, its mood): kind is "poster", and the spec is the whole poster with that change made. Never describe what you would change; make the change.
Fill every field of the spec. Headline up to 6 words, subheadline up to 12, body up to 25. format is portrait or square.
The image_prompt describes only the picture: subject, setting, light, colours. It contains no words to print.
Brand and product facts are not in this prompt. Before you state any product fact, call get_brand_details and use only what it returns. Never claim what it does not say. In sources, list the id in brackets of every section a fact in the copy came from.
Otherwise, for a greeting, a question or small talk: kind is "reply", with a short helpful answer in the brand's voice. No spec."""

PICTURE_TASK = """Make the poster picture. Call generate_image once with the scene description you were given.
When the tool returns a file, reply with that file path and nothing else."""

RESEARCH_TASK = """You research one question for a marketing team. Call search_web with a short query and read the pages that come back.
Reply with a short report and nothing else: one paragraph of at most 60 words on the message, the channels and what to avoid copying,
then the addresses of the pages you used."""


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
        tools=[make_get_brand_details(ws, trace, settings)],
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
