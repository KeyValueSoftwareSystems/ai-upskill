"""What LaunchKit remembers across conversations: Agno's user memories and learnings, kept in the project database.

Session 3's starting state. Memory went on six months ago in one line, update_memory_on_run=True, keyed by user_id.
User memories sit in agno_memories in data/sessions.db. Learnings, entity facts and the decision log sit in agno_learnings.
Learned knowledge needs a vector store, so its text sits in data/learnings/ (LanceDB, the same local embedding model as
the brand index) and only its title and tags sit in agno_knowledge.

Agno puts memories, summaries and learnings into the prompt only when it builds the system message itself. The main
agent writes its own system message (agents/prompt.py), so LaunchKit reads the rows back here and adds them as the
prompt's memory section.
"""

from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from agno.db.sqlite import SqliteDb
from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.learn import LearningMachine
from agno.db.base import SessionType
from agno.memory import MemoryManager
from agno.session.summary import SessionSummaryManager
from agno.vectordb.lancedb import LanceDb

from launchkit.adapters.fakes import FakeModel
from launchkit.adapters.models import resolve_model
from launchkit.knowledge.brand_search import EMBED_MODEL
from launchkit.memory.chat_history import session_db
from launchkit.tools.catalogue import todo


# Ticket 1: what one saved row may hold. Agno puts this in the manager's prompt as <memories_to_capture>.
CAPTURE = ""  # Ticket 1 builds it: what one saved row may hold. See docs/mem-1.md.


def cheap_model(settings, trace, main_model):
    """LAUNCHKIT_MEMORY_MODEL, for the jobs that only sort or shorten text. A fake run keeps its fake."""
    return main_model if isinstance(main_model, FakeModel) else resolve_model(replace(settings, model=settings.memory_model), trace)


@todo
def memory_manager(settings, trace, main_model) -> MemoryManager | None:
    """Ticket 1: not built yet. None means Agno builds its default manager, on the main model, with its default rules."""
    return None


def summary_manager(settings, trace, main_model) -> SessionSummaryManager:
    """Ticket 4: a running summary of one conversation, kept on the session, on the cheaper model."""
    return SessionSummaryManager(model=cheap_model(settings, trace, main_model))


def summary_text(settings, session_id: str) -> str:
    """This conversation's summary so far. Agno would add it to its own system message; LaunchKit writes its own."""
    session = session_db(settings).get_session(session_id, SessionType.AGENT) if session_id else None
    return f"Summary of this conversation so far (older turns are not in view):\n{session.summary.summary}" if session and session.summary else ""


def learnings(settings) -> Knowledge:
    """The vector store behind learned knowledge. Its contents table is the project database."""
    return _learnings(settings.data_dir)


@lru_cache(maxsize=8)
def _learnings(data_dir: Path) -> Knowledge:
    """One per data folder, so the embedding model loads once, not once per agent."""
    vectors = LanceDb(uri=str(data_dir / "learnings"), table_name="learnings", embedder=SentenceTransformerEmbedder(id=EMBED_MODEL, dimensions=384))
    return Knowledge(vector_db=vectors, contents_db=SqliteDb(db_file=str(data_dir / "sessions.db")))


def learning_machine(settings, namespace: str = "global") -> LearningMachine:
    """Learned knowledge, entity memory and the decision log. Ticket 3: learned knowledge and entity memory are shared
    within one namespace, the brand's id; Agno's default, "global", shares them with every brand."""
    return LearningMachine(db=session_db(settings), knowledge=learnings(settings), learned_knowledge=True, entity_memory=True, decision_log=True, namespace=namespace)


def user_memories(db: SqliteDb, user_id: str) -> list:
    return sorted(db.get_user_memories(user_id=user_id) or [], key=lambda m: m.updated_at or 0)


def memory_text(rows: list) -> str:
    """These memory rows, the way Agno would add them to its own system message."""
    if not rows:
        return ""
    lines = "\n".join(f"- {m.memory}" for m in rows)
    return (f"What you remember about this person from earlier conversations:\n{lines}\n"
            "A remembered brand or product fact may be out of date: facts from get_brand_facts win.")


def memory_changes(before: list, after: list) -> list[tuple[str, str]]:
    """What a run did to this person's memories: added, updated or deleted, one line each, for the Trace tab."""
    old = {m.memory_id: m.memory for m in before}
    new = {m.memory_id: m.memory for m in after}
    changes = [("added", text) for mid, text in new.items() if mid not in old]
    changes += [("updated", f"{old[mid]} → {text}") for mid, text in new.items() if mid in old and old[mid] != text]
    changes += [("deleted", text) for mid, text in old.items() if mid not in new]
    return changes
