"""Ticket 6: forget one person. A delete that cascades by user_id across every place LaunchKit keeps something about
them, then a search for what still names them. Agno's stores are deleted through their own tables; a shared learning
is found by the tag source:<user_id> that save_learning adds, because Agno keeps no user_id on a shared learning."""

import json
import shutil
import sqlite3
from contextlib import closing

import lancedb

from launchkit.memory.long_term import learnings

TABLES = [  # (what, table, the column that holds the person)
    ("memories", "agno_memories", "user_id"),
    ("conversations and their summaries", "agno_sessions", "user_id"),
    ("decision log and entity rows", "agno_learnings", "user_id"),
]
TEXT = [("agno_memories", "memory"), ("agno_sessions", "summary"), ("agno_learnings", "content"), ("agno_knowledge", "name"), ("brand_facts", "source")]


def _files(settings, user_id: str):
    return [p for kind in ("conversations", "pictures") for p in (settings.data_dir / kind).glob(f"*/{user_id}") if p.is_dir()]


def still_naming(settings, user_id: str, names: list[str]) -> list[str]:
    """Every place the person's id or a name of theirs still appears: database rows, the learnings' text, files."""
    found, needles = [], [user_id, *names]
    with closing(sqlite3.connect(settings.data_dir / "sessions.db")) as con:
        for table, column in TEXT:
            try:
                rows = con.execute(f"select {column}, * from {table}").fetchall()
            except sqlite3.OperationalError:
                continue
            found += [f"{table}: {str(r[0])[:90]}" for r in rows if any(n.lower() in json.dumps(r, default=str).lower() for n in needles)]
    folder = settings.data_dir / "learnings"
    if folder.exists() and "learnings" in lancedb.connect(str(folder)).table_names():
        for row in lancedb.connect(str(folder)).open_table("learnings").to_arrow().to_pylist():
            payload = json.loads(row.get("payload") or "{}")
            if any(n.lower() in json.dumps(payload).lower() for n in names):
                found.append(f"learned knowledge text: {str(payload.get('name') or payload.get('content'))[:90]}")
    return found + [f"files: {p.relative_to(settings.data_dir)}" for p in _files(settings, user_id)]


def delete_user(settings, user_id: str, apply: bool) -> list[tuple[str, int]]:
    """What the cascade removes (or would remove, without apply), one line per store. A table not made yet is skipped."""
    removed = []
    with closing(sqlite3.connect(settings.data_dir / "sessions.db")) as con, con:
        for what, table, column in TABLES:
            try:
                count = con.execute(f"select count(*) from {table} where {column} = ?", (user_id,)).fetchone()[0]
            except sqlite3.OperationalError:
                continue
            if apply:
                con.execute(f"delete from {table} where {column} = ?", (user_id,))
            removed.append((what, count))
        try:  # Agno keeps no user_id on a shared learning: save_learning tags it source:<user_id>
            proposed = [row_id for row_id, metadata in con.execute("select id, metadata from agno_knowledge")
                        if f"source:{user_id}" in (json.loads(metadata or "{}").get("tags") or [])]
        except sqlite3.OperationalError:
            proposed = None
        try:  # the fact stays true for the brand; only who proposed it goes
            facts = con.execute("select count(*) from brand_facts where source = ?", (user_id,)).fetchone()[0]
            if apply:
                con.execute("update brand_facts set source = 'removed user' where source = ?", (user_id,))
        except sqlite3.OperationalError:
            facts = None
    if proposed is not None:  # after the connection above is closed: removing a learning writes to the same database
        if apply:
            for row_id in proposed:
                learnings(settings).remove_content_by_id(row_id)
        removed.append((f"shared learnings they proposed (tag source:{user_id})", len(proposed)))
    if facts is not None:
        removed.append(("brand facts they proposed (kept, source set to 'removed user')", facts))
    folders = _files(settings, user_id)
    if apply:
        for folder in folders:
            shutil.rmtree(folder)
    removed.append(("chat page folders (conversations and pictures)", len(folders)))
    return removed
