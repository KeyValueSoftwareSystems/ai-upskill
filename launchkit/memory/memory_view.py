"""What LaunchKit remembers, read straight from the store: the chat page's Memory tab and `launchkit memory show`.

Read-only. Agno's tables are read as they are, so the tab shows exactly what the agent can be handed.
"""

import json
import shutil
import sqlite3
from datetime import datetime, timezone

from launchkit.settings import ROOT

SNAPSHOT = ROOT / "fixtures" / "memory-snapshot.db"
SNAPSHOT_LEARNINGS = ROOT / "fixtures" / "memory-snapshot-learnings"


def reset_to_snapshot(settings) -> list[str]:
    """Put the checked-in snapshot in place of the project database and the learnings folder. Keeps a copy of what was there."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db, learnings = settings.data_dir / "sessions.db", settings.data_dir / "learnings"
    kept = []
    if db.exists():  # every reset keeps its own copy, named by the time, so no earlier copy is ever overwritten
        backup = db.with_name(f"sessions-{datetime.now():%Y%m%d-%H%M%S}.db.bak")
        with sqlite3.connect(db) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        kept.append(str(backup))
    for extra in (db.with_suffix(".db-wal"), db.with_suffix(".db-shm")):
        extra.unlink(missing_ok=True)
    shutil.copyfile(SNAPSHOT, db)
    shutil.rmtree(learnings, ignore_errors=True)
    shutil.copytree(SNAPSHOT_LEARNINGS, learnings)
    return kept


def _day(value) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d")
    return str(value)[:10]


def _rows(con, sql: str, *args) -> list[sqlite3.Row]:
    try:
        return con.execute(sql, args).fetchall()
    except sqlite3.OperationalError:  # the table is made on first write; before that there is nothing to show
        return []


def memory_view(settings, user_id: str, workspace_id: str = "") -> dict:
    from launchkit.knowledge.brand_facts import all_brand_facts
    from launchkit.memory.scope import held_back

    path = settings.data_dir / "sessions.db"
    facts = all_brand_facts(settings, workspace_id) if workspace_id else []
    if not path.exists():
        return {"memories": [], "summaries": [], "learnings": [], "entities": [], "decisions": [], "brand_facts": facts}
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        memories = [{"memory": r["memory"], "topics": json.loads(r["topics"] or "[]"), "updated": _day(r["updated_at"]), "held_back": held_back(r["memory"], settings) or ""}
                    for r in _rows(con, "select memory, topics, updated_at from agno_memories where user_id = ? order by updated_at", user_id)]
        # Agno writes a conversation with no summary yet as the JSON text "null", which SQL's "is not null" lets through.
        summaries = [{"session": r["session_id"], "summary": s["summary"], "updated": _day(r["updated_at"])}
                     for r in _rows(con, "select session_id, summary, updated_at from agno_sessions where user_id = ?", user_id)
                     if (s := json.loads(r["summary"] or "null")) and s.get("summary")]
        learnings = [{"title": r["name"], **{k: v for k, v in json.loads(r["metadata"] or "{}").items() if k in ("namespace", "tags")}, "updated": _day(r["updated_at"])}
                     for r in _rows(con, "select name, metadata, updated_at from agno_knowledge order by updated_at")]
        entities = [{"entity": json.loads(r["content"]).get("name") or r["entity_id"], "namespace": r["namespace"],
                     "facts": [f["content"] for f in json.loads(r["content"]).get("facts", [])]}
                    for r in _rows(con, "select entity_id, namespace, content from agno_learnings where learning_type = 'entity_memory'")]
        decisions = [{"decision": json.loads(r["content"]).get("decision"), "updated": _day(r["created_at"])}
                     for r in _rows(con, "select content, created_at from agno_learnings where learning_type = 'decision_log' and user_id = ?", user_id)]
    return {"memories": memories, "summaries": summaries, "learnings": learnings, "entities": entities, "decisions": decisions, "brand_facts": facts}
