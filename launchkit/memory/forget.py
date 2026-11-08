"""Forget: remove everything the store holds about something, everywhere it was copied.

Slot for build B, ticket 6. Reference: page 7, "Lifetime", and page 4, "What never goes in".

A fact saved once gets copied: into a chat summary, into a learning the whole brand reads. Deleting the
row is not forgetting. `forget` has to reach every copy. The placeholder deletes only the person's own
rows that contain the text; the copies stay. That is ticket 6 as the room sees it.
"""

from __future__ import annotations

from launchkit.memory.store import MemoryStore


def forget(store: MemoryStore, workspace_id: str, user_id: str, text: str) -> dict[str, int]:
    """Remove every place `text` appears for this brand. Returns how many of each were cleared.

    Build B fills this in. The three places are: the person's rows (`memories`), the summaries of their
    chats and of any chat at the brand that mention it (`summaries`), and the brand's shared rows
    (`learnings`). Other people's own rows are never touched.
    """
    if not text.strip():
        raise ValueError("say what to forget; an empty text would match every row")
    rows = store.get_user_memories(user_id=user_id) or []
    hits = [r.memory_id for r in rows if text in r.memory]
    if hits:
        store.delete_user_memories(hits, user_id=user_id)
    return {"memories": len(hits), "summaries": 0, "learnings": 0}
