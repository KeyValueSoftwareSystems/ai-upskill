"""Ticket 4: how long a memory lives. A scheduled job, never part of a run: prune each person's rows older than N days,
then fold what is left into one row with Agno's Summarize strategy when a person still has too many."""

import time

from agno.memory.strategies.types import MemoryOptimizationStrategyType

from launchkit.agents.prompt import approx_tokens
from launchkit.memory.long_term import user_memories
from launchkit.tools.catalogue import todo


def tokens(rows) -> int:
    return approx_tokens(" ".join(m.memory for m in rows))


@todo
def retain(manager, days: int, summarise_over: int, apply: bool, now: float | None = None) -> list[dict]:
    """Ticket 4: not built yet. One line per person: rows and tokens before, rows pruned, rows and tokens after."""
    return []
