from concurrent.futures import ThreadPoolExecutor

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


def build_research_agent(model, settings, trace: Trace) -> Agent | None:
    """Orchestration step 2: the research subagent. RESEARCH_TASK, search_web only, no session store and no chat history."""
    return Agent(
        model=model,
        system_message=RESEARCH_TASK,
        tools=[make_search_web(settings)],
        tool_hooks=[make_leash(settings.limits, trace)],
        telemetry=False,
    )


def make_research_entries(model, settings, trace: Trace) -> list[Entry]:
    """Orchestration step 2: research and research_many, as read tools for the catalogue."""

    def research(brief: str) -> str:
        run = build_research_agent(model, settings, trace).run(brief)
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
