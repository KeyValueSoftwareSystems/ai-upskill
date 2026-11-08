"""Ticket 5: how long a memory lives. A scheduled job, never part of a run: prune each person's rows older than N days,
then fold what is left into one row with Agno's Summarize strategy when a person still has too many."""

import time

from agno.memory.strategies.types import MemoryOptimizationStrategyType

from launchkit.agents.prompt import approx_tokens
from launchkit.memory.long_term import user_memories


def tokens(rows) -> int:
    return approx_tokens(" ".join(m.memory for m in rows))


def retain(manager, days: int, summarise_over: int, apply: bool, now: float | None = None) -> list[dict]:
    """One line per person: rows and tokens before, rows pruned, rows and tokens after. Without apply, nothing is
    written and the line says what it would do."""
    cutoff = (now or time.time()) - days * 86400
    report = []
    for user in sorted({m.user_id for m in manager.db.get_user_memories() or [] if m.user_id}):
        rows = user_memories(manager.db, user)
        old = [m for m in rows if (m.updated_at or 0) < cutoff]
        kept = [m for m in rows if m not in old]
        if apply:
            if old:
                manager.db.delete_user_memories([m.memory_id for m in old], user_id=user)
            if len(kept) > summarise_over:
                manager.optimize_memories(user_id=user, strategy=MemoryOptimizationStrategyType.SUMMARIZE, apply=True)
            kept = user_memories(manager.db, user)
        report.append({"user": user, "before": len(rows), "tokens_before": tokens(rows), "pruned": len(old),
                       "after": len(kept), "tokens_after": tokens(kept)})
    return report
