import re
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from agno.agent import Agent

from launchkit.adapters.models import model_name
from launchkit.agents.poster_flow import raise_if_failed
from launchkit.guardrails.limits import make_leash
from launchkit.tools.catalogue import Entry
from launchkit.tools.search_web import make_search_web
from launchkit.trace import Trace

RESEARCH_TASK = """You research one question for a marketing team. Call search_web with a short query and read the pages that come back.
Reply with a short report and nothing else: one paragraph of at most 60 words on the message, the channels and what to avoid copying,
then the addresses of the pages you used."""


SAVE_TASK = """
When you have the report, call save_brief once with the competitor's name and the report, then reply with the report."""


def build_research_agent(model, settings, trace: Trace, save_brief: Callable | None = None) -> Agent | None:
    """Orchestration step 2: the research subagent. RESEARCH_TASK, search_web only, no session store and no chat history.

    Session 4: given a `save_brief`, the subagent also writes its own brief, in parallel with the others. That is what
    the ticket after shipping turns on. Without one it behaves exactly as it did in Session 2.
    """
    return Agent(
        model=model,
        system_message=RESEARCH_TASK + (SAVE_TASK if save_brief else ""),
        tools=[make_search_web(settings), *([save_brief] if save_brief else [])],
        tool_hooks=[make_leash(settings.limits, trace)],
        telemetry=False,
    )


def make_research_entries(model, settings, trace: Trace, write: Callable[[], Callable[[str, str], str]] | None = None) -> list[Entry]:
    """Orchestration step 2: research and research_many, as read tools for the catalogue.

    `write` builds a file write tool (Session 4, stage 1). When it is given, every research subagent builds its own
    at the moment it starts and saves its own brief to competitors/<name>.md with it, in parallel with the others.
    A tool per subagent is how every other tool in a research run is built, and it is what the ticket after shipping
    turns on. Nothing passes it until the room has built that tool and registered it.
    """

    def research(brief: str) -> str:
        save = write() if write else None  # built now, before the subagent has searched anything

        def save_brief(competitor: str, report: str) -> str:
            """Save this competitor's brief into the conversation's competitors folder."""
            name = re.sub(r"[^a-z0-9]+", "-", competitor.lower()).strip("-") or "competitor"
            return save(f"competitors/{name}.md", report)

        run = build_research_agent(model, settings, trace, save_brief if save else None).run(brief)
        raise_if_failed(run)
        trace.model("research", model_name(model), run.metrics)
        return str(run.content or "")

    def research_many(briefs: list[str]) -> list[str]:
        with ThreadPoolExecutor(max_workers=max(len(briefs), 1)) as pool:
            return list(pool.map(research, briefs))

    return [
        Entry("research", "hand one research question to a research agent; get back a short report, not the pages", "read", research),
        Entry("research_many", "hand several independent research questions to research agents that run at the same time; get back one short report each, in order", "read", research_many),
    ]
