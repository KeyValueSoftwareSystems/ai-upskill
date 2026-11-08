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
    import re
    import sqlite3

    from launchkit.memory.store import brand_owner, topic_value

    # The person's own rows at this brand. Rows saved at another brand are that brand's business.
    rows = store.get_user_memories(user_id=user_id) or []
    hits = [r.memory_id for r in rows if text in r.memory and topic_value(r.topics or [], "brand:", workspace_id) == workspace_id]
    if hits:
        store.delete_user_memories(hits, user_id=user_id)

    # Chat summaries at this brand that still carry the text. The chat stays; the sentence goes.
    summaries = 0
    for session in store.get_sessions() or []:
        summary = session.summary.summary if session.summary else ""
        if text in (summary or "") and str(session.session_id).startswith(f"{workspace_id}:"):
            sentences = re.split(r"(?<=[.!?])\s+", summary)
            session.summary.summary = " ".join(s for s in sentences if text not in s)
            store.upsert_session(session)
            summaries += 1

    # The brand's shared rows, which every chat at the brand reads.
    shared = store.get_user_memories(user_id=brand_owner(workspace_id)) or []
    learning_hits = [r.memory_id for r in shared if text in r.memory]
    if learning_hits:
        store.delete_user_memories(learning_hits, user_id=brand_owner(workspace_id))

    # SQLite keeps deleted bytes in old pages and in the write-ahead log until the file is compacted.
    # Forgotten means gone from the file, so compact it now, outside any transaction.
    db = sqlite3.connect(store.db_file, isolation_level=None)
    try:
        db.execute("PRAGMA secure_delete = ON")
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        db.execute("VACUUM")
    finally:
        db.close()

    return {"memories": len(hits), "summaries": summaries, "learnings": len(learning_hits)}
