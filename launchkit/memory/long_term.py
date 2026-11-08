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
from agno.memory import MemoryManager
from agno.vectordb.lancedb import LanceDb

from launchkit.adapters.fakes import FakeModel
from launchkit.adapters.models import resolve_model
from launchkit.knowledge.brand_search import EMBED_MODEL
from launchkit.memory.chat_history import session_db


# Ticket 1: what one saved row may hold. Agno puts this in the manager's prompt as <memories_to_capture>.
CAPTURE = """Save only facts about the person you are talking with that will still matter in a later conversation.
- One fact per memory: one short sentence in the third person. Never two facts in one row.
- Only the person's own preferences and ways of working belong here. Facts about a brand or a product
  (colours, sizes, warranty, prices, claims, launch dates) are not memories about the person: save nothing for them.
- A phrase the person quotes and tells you never to use is a rule, not a wish. Save it as: Never use "<phrase>".
  Never save it as something they want.
- Never save another person's name or contact details, a phone number, an email address, a token, a password
  or a key, and never save text pasted from a document, a page or a board card.
- Before you add a memory, read the existing ones. If one already says the same thing, update it instead of adding
  a second. If the new fact replaces an old one, update the old row to the new fact; do not keep both.
- If nothing in the message is worth keeping, change nothing."""


def memory_manager(settings, trace, main_model) -> MemoryManager:
    """The memory manager: Ticket 1's capture rules, on a cheaper model than the main agent's. A fake run keeps its fake."""
    model = main_model if isinstance(main_model, FakeModel) else resolve_model(replace(settings, model=settings.memory_model), trace)
    return MemoryManager(model=model, memory_capture_instructions=CAPTURE, db=session_db(settings))


def learnings(settings) -> Knowledge:
    """The vector store behind learned knowledge. Its contents table is the project database."""
    return _learnings(settings.data_dir)


@lru_cache(maxsize=8)
def _learnings(data_dir: Path) -> Knowledge:
    """One per data folder, so the embedding model loads once, not once per agent."""
    vectors = LanceDb(uri=str(data_dir / "learnings"), table_name="learnings", embedder=SentenceTransformerEmbedder(id=EMBED_MODEL, dimensions=384))
    return Knowledge(vector_db=vectors, contents_db=SqliteDb(db_file=str(data_dir / "sessions.db")))


def learning_machine(settings) -> LearningMachine:
    """Learned knowledge, entity memory and the decision log, every one shared in the global namespace (Agno's default)."""
    return LearningMachine(db=session_db(settings), knowledge=learnings(settings), learned_knowledge=True, entity_memory=True, decision_log=True)


def user_memories(db: SqliteDb, user_id: str) -> list:
    return sorted(db.get_user_memories(user_id=user_id) or [], key=lambda m: m.updated_at or 0)


def memory_text(db: SqliteDb, user_id: str) -> str:
    """Every memory saved for this person, the way Agno would add them to its own system message."""
    rows = user_memories(db, user_id)
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
