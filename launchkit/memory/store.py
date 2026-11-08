"""Long-term memory: the one door every saved fact passes through.

Ready-made for tickets 1 to 6. Reference: page 1, "Where a fact lives".

Agno keeps a person's memories in the `agno_memories` table of the same SQLite file that holds the chat
history. `MemoryStore` is that table with a door in front of it: every save goes through
`upsert_user_memory`, which stamps the row with who said it, where it came from, who may read it and
when it became true, asks the write door whether to keep it, and leaves a line in the trace.

Reading back goes through `rows_for`, which decides which rows one person at one brand gets to see.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import NamedTuple

from agno.db.schemas.memory import UserMemory
from agno.db.sqlite import SqliteDb

from launchkit.agents.prompt import approx_tokens
from launchkit.settings import ROOT
from launchkit.trace import Trace


class Decision(NamedTuple):
    """What the write door decided about one row: keep it or not, and under which scope.

    `scope` is "user", "brand" or None. None means "leave the scope as it arrived".
    """

    keep: bool
    scope: str | None


# The write door. Build B replaces the placeholder in write_door.py; the store only calls it.
Decide = Callable[[str, list[str]], Decision]


def brand_owner(workspace_id: str) -> str:
    """The user id that holds a brand's shared rows. Agno files rows under one user id and knows nothing
    about brands, so a brand gets a user id of its own."""
    return f"{workspace_id}:brand"


class MemoryStore(SqliteDb):
    """The memory table, opened as one person at one brand, with the door in front of every save."""

    def __init__(self, db_file: str, workspace_id: str, user_id: str, trace: Trace, decide: Decide | None = None):
        super().__init__(db_file=db_file, memory_table="agno_memories")
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.trace = trace
        self.decide = decide

    def upsert_user_memory(self, memory: UserMemory, deserialize: bool = True):
        """Save one row, after stamping it and asking the door.

        Agno calls this for every memory it wants to keep, whether the extractor found it after a reply
        or the agent asked for it with its memory tool. Nothing reaches the table any other way.
        """
        topics = list(memory.topics or [])
        if not has(topics, "author:"):
            topics.append(f"author:{self.user_id}")
        if not has(topics, "source:"):
            topics.append("source:chat")
        if not has(topics, "scope:"):
            topics.append(f"scope:user:{memory.user_id or self.user_id}")
        if not has(topics, "valid_from:"):
            topics.append(f"valid_from:{date.today():%Y-%m-%d}")

        if self.decide is not None:
            decision = self.decide(memory.memory, topics)
            if not decision.keep:
                self.trace.memory_refused(memory.memory, f"{self.user_id} said no")
                return None
            if decision.scope == "brand":
                topics = [t for t in topics if not t.startswith("scope:")] + [f"scope:brand:{self.workspace_id}"]
                memory.user_id = brand_owner(self.workspace_id)
            elif decision.scope == "user":
                topics = [t for t in topics if not t.startswith("scope:")] + [f"scope:user:{self.user_id}"]
                memory.user_id = self.user_id

        memory.topics = topics
        saved = super().upsert_user_memory(memory, deserialize=deserialize)
        self.trace.memory_kept(topic_value(topics, "scope:"), memory.memory)
        return saved

    def insert_raw(self, memory: UserMemory):
        """Write a row exactly as given, past the door. For the seed script and the tests only."""
        return super().upsert_user_memory(memory, deserialize=True)


def has(topics: list[str], prefix: str) -> bool:
    return any(t.startswith(prefix) for t in topics)


def topic_value(topics: list[str], prefix: str, default: str = "") -> str:
    """The value after a prefix, for topics written as `prefix:value`."""
    for t in topics:
        if t.startswith(prefix):
            return t[len(prefix):]
    return default


def rows_for(store: MemoryStore, workspace_id: str, user_id: str) -> list[UserMemory]:
    """The rows one person at one brand may read.

    Build A, ticket 3, fills this in. The placeholder returns every row filed under the person's user
    id, whatever brand they were saved at, and none of the brand's shared rows.
    """
    return list(store.get_user_memories(user_id=user_id) or [])


def memory_section(rows: list[UserMemory]) -> str:
    """The `# Memory` section of the prompt: one line per row with its kind, scope and start date."""
    lines = []
    for row in rows:
        topics = row.topics or []
        kind = topic_value(topics, "kind:", "fact")
        scope = topic_value(topics, "scope:", f"user:{row.user_id}")
        since = topic_value(topics, "valid_from:", "unknown")
        lines.append(f"- {row.memory}  ({kind} · {scope} · since {since})")
    return "\n".join(lines)


def memory_tokens(text: str) -> int:
    return approx_tokens(text)


def capture_rules() -> str:
    """The instructions the extractor follows when it decides what to save. Build A, ticket 1, rewrites them."""
    return (ROOT / "launchkit" / "memory" / "capture_rules.md").read_text(encoding="utf-8").strip()


def open_store(settings, workspace_id: str, user_id: str, trace: Trace, decide: Decide | None = None) -> MemoryStore:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return MemoryStore(str(settings.data_dir / "sessions.db"), workspace_id, user_id, trace, decide)
