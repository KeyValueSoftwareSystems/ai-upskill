"""The research helper: a subagent that reads pages and reports back. As memory shipped it also carried a save tool.

Ready-made for ticket 4. Reference: page 5, "Scope".
"""

from concurrent.futures import ThreadPoolExecutor

from agno.agent import Agent
from agno.db.schemas.memory import UserMemory

from launchkit.adapters.models import model_name
from launchkit.agents.poster_flow import raise_if_failed
from launchkit.guardrails.limits import make_leash
from launchkit.memory.store import MemoryStore, brand_owner
from launchkit.tools.catalogue import Entry
from launchkit.tools.search_web import make_search_web
from launchkit.trace import Trace

RESEARCH_TASK = """You research one question for a marketing team. Call search_web with a short query and read the pages that come back.
Reply with a short report and nothing else: one paragraph of at most 60 words on the message, the channels and what to avoid copying,
then the addresses of the pages you used. When a page states something the whole brand should remember, call save_learning with it."""


def make_save_learning(store: MemoryStore):
    """The helper's save tool, as memory shipped. Build B, ticket 4, takes it away or has the door refuse it.

    What it saves is filed under the brand, read by every chat at that brand, and marked as coming from the web.
    """

    def save_learning(text: str) -> str:
        """Keep one sentence the brand should remember from the pages you read, for example a claim a
        competitor makes. Everyone at the brand will see it in later chats."""
        row = UserMemory(memory=text, user_id=brand_owner(store.workspace_id), topics=[f"scope:brand:{store.workspace_id}", "source:web", "kind:fact"])
        saved = store.upsert_user_memory(row)
        return "kept for the brand" if saved is not None else "not kept"

    return save_learning


def build_research_agent(model, settings, trace: Trace, store: MemoryStore | None = None) -> Agent | None:
    """Orchestration step 2: the research subagent. RESEARCH_TASK, search_web, no session store and no chat history.
    With a memory store it also carries save_learning, which is how the helper came to write to memory."""
    tools = [make_search_web(settings)]
    if store is not None:
        tools.append(make_save_learning(store))
    return Agent(
        model=model,
        system_message=RESEARCH_TASK,
        tools=tools,
        tool_hooks=[make_leash(settings.limits, trace)],
        telemetry=False,
    )


def make_research_entries(jobs_or_model, settings, trace: Trace, store: MemoryStore | None = None) -> list[Entry]:
    """Orchestration step 2: research and research_many, as read tools for the catalogue. Each run gets its model
    from the research job's route, and moves on the way on_failure says when that model is down. A plain model
    instead of a Jobs means: this model, every time."""
    from launchkit.adapters.jobs import Jobs

    jobs = jobs_or_model if isinstance(jobs_or_model, Jobs) else Jobs(settings, trace, fixed=jobs_or_model)

    def research(brief: str) -> str:
        def call(model):
            run = build_research_agent(model, settings, trace, store).run(brief)
            raise_if_failed(run)
            trace.model("research", model_name(model), run.metrics)
            return str(run.content or "")

        return jobs.in_order("research", call)

    def research_many(briefs: list[str]) -> list[str]:
        with ThreadPoolExecutor(max_workers=max(len(briefs), 1)) as pool:
            return list(pool.map(research, briefs))

    return [
        Entry("research", "hand one research question to a research agent; get back a short report, not the pages", "read", research),
        Entry("research_many", "hand several independent research questions to research agents that run at the same time; get back one short report each, in order", "read", research_many),
    ]
