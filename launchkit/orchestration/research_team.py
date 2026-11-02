from agno.agent import Agent

from launchkit.guardrails.limits import make_leash
from launchkit.tools.catalogue import Entry
from launchkit.trace import Trace

RESEARCH_TASK = """You research one question for a marketing team. Call search_web with a short query and read the pages that come back.
Reply with a short report and nothing else: one paragraph of at most 60 words on the message, the channels and what to avoid copying,
then the addresses of the pages you used."""


def build_research_agent(model, settings, trace: Trace) -> Agent | None:
    """Orchestration step 2: the research subagent. RESEARCH_TASK, search_web only, no session store and no chat history."""
    return None


def make_research_entries(model, settings, trace: Trace) -> list[Entry]:
    """Orchestration step 2: research and research_many, as read tools for the catalogue."""
    return []
