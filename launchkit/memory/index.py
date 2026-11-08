"""Reading memory back without putting every row in the prompt.

Slot for build B, ticket 5. Reference: page 6, "Reading memory back".

Two functions share the work. `memory_index` is what goes into the prompt's `# Memory` section: short
enough to send on every turn. `recall` is a read tool the agent calls when it wants one topic in full.
A topic is a row's `topic:` label; a row without one takes its first word that is not a stop word.

The placeholder index is the full list of rows, so the prompt grows with every save. That is ticket 5.
"""

from __future__ import annotations

import re

from agno.db.schemas.memory import UserMemory

from launchkit.memory.store import MemoryStore, memory_section, rows_for, topic_value
from launchkit.tools.catalogue import Entry

LINE_CAP = 80
STOP_WORDS = {"the", "a", "an", "and", "for", "to", "of", "in", "on", "is", "are", "our", "we", "prefers", "likes", "uses", "wants", "never", "always", "not"}


def topic_of(row: UserMemory) -> str:
    """The topic a row files under: its `topic:` label, or its first plain word."""
    labelled = topic_value(row.topics or [], "topic:")
    if labelled:
        return labelled
    for word in re.findall(r"[a-z]+", row.memory.lower()):
        if word not in STOP_WORDS and len(word) > 2:
            return word
    return "other"


def memory_index(rows: list[UserMemory]) -> str:
    """The `# Memory` section as the model sees it.

    Build B fills this in: one line per topic, `- <topic>: <n> rows · recall("<topic>")`, each line at
    most LINE_CAP characters, topics in alphabetical order. Built by code, no model call.
    """
    return memory_section(rows)


def recall(rows: list[UserMemory], topic: str) -> str:
    """Every row under one topic, in full, each with its kind.

    Build B fills this in. When no row matches, say so and list the topics that exist, so the agent can
    ask again with a topic that does.
    """
    return f"No rows about {topic}. Recall is not built yet; the full memory is in the prompt."


def recall_entry(store: MemoryStore, workspace_id: str, user_id: str) -> Entry:
    """recall as a read tool in the catalogue, so the agent reaches it through run_tool."""

    def recall_topic(topic: str) -> str:
        """Read everything memory holds on one topic, for example "photography" or "warranty". The
        memory section of your prompt lists the topics; call this before you rely on one."""
        return recall(rows_for(store, workspace_id, user_id), topic)

    recall_topic.__name__ = "recall"
    return Entry("recall", "read everything memory holds about one topic named in the memory section", "read", recall_topic)
