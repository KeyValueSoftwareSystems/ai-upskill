from concurrent.futures import ThreadPoolExecutor

from launchkit.adapters.models import model_name
from launchkit.harness.agent import build_research_agent
from launchkit.harness.catalogue import Entry
from launchkit.harness.run import raise_if_failed
from launchkit.harness.trace import Trace


def make_research_entries(model, settings, trace: Trace) -> list[Entry]:
    """CP2.2b: research and research_many, as read tools for the catalogue."""

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
