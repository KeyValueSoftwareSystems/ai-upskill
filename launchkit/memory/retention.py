"""Retention: rows do not live for ever.

Slot for build B, ticket 5. Reference: page 7, "Lifetime".

A person's rows pile up; after a few months most of them are stale. `prune` removes the ones older than
a limit. `launchkit retention <brand>` runs it by hand. The placeholder removes nothing.
"""

from __future__ import annotations

from datetime import date

from launchkit.memory.store import MemoryStore


def prune(store: MemoryStore, workspace_id: str, today: date, max_age_days: int = 180) -> int:
    """Remove a person's rows whose valid_from is more than `max_age_days` before `today`. Returns how many went.

    Build B fills this in. Brand rows (`scope:brand:...`) are kept: they are the brand's, not one
    person's, and they end through the brand facts table instead.
    """
    return 0
