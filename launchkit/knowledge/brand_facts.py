"""Ticket 2a: brand facts LaunchKit owns, in its own table in the project database. One row is one fact and when it was
true: subject, value, scope, source, valid_from, valid_to (empty while it is still true). Plain code reads it: no model.
A new value never overwrites the old one: the old row is closed the day before, and a new row opens today.

Where the rows come from: each brand's own workspaces/<brand>/brand_facts.yaml, the dated part of its product sheet.
load_brand_facts copies the file's entries into the table; after that a change goes through propose_brand_fact and a
yes (ticket 2b), or through the file. Until ticket 2a is built the table stays empty."""

import sqlite3
from contextlib import closing
from datetime import date, timedelta

import yaml

from launchkit.tools.catalogue import todo


def _open(settings) -> sqlite3.Connection:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(settings.data_dir / "sessions.db")
    con.row_factory = sqlite3.Row
    con.execute("create table if not exists brand_facts (id integer primary key, brand text not null, subject text not null, value text not null, "
                "scope text not null, source text not null, valid_from text not null, valid_to text)")
    return con


def brand_file_facts(settings, brand: str) -> list[dict]:
    """The entries in the brand's brand_facts.yaml, one dict per value, oldest first. No file, no entries."""
    path = settings.workspaces_dir / brand / "brand_facts.yaml"
    if not path.exists():
        return []
    facts = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [{"brand": brand, "subject": subject.lower(), "value": str(e["value"]), "scope": "brand", "source": e["source"],
             "valid_from": str(e["from"]), "valid_to": str(e["to"]) if e.get("to") else None}
            for subject, entries in facts.items() for e in sorted(entries, key=lambda e: str(e["from"]))]


@todo
def load_brand_facts(settings, brand: str) -> int:
    """Ticket 2a: not built yet. Copy the brand's file entries into the table, skipping any already there; how many were added."""
    return 0


@todo
def get_brand_facts(settings, brand: str, today: date | None = None) -> list[dict]:
    """Ticket 2a: not built yet. The brand's facts that are true today, one per subject."""
    return []


def all_brand_facts(settings, brand: str, today: date | None = None) -> list[dict]:
    """Every row, old ones too, with whether it is true today: what the Memory tab shows."""
    load_brand_facts(settings, brand)
    day = (today or date.today()).isoformat()
    with closing(_open(settings)) as con:
        rows = con.execute("select * from brand_facts where brand = ? order by subject, valid_from", (brand,)).fetchall()
    return [{**dict(r), "true_today": r["valid_from"] <= day and (r["valid_to"] is None or r["valid_to"] >= day)} for r in rows]


@todo
def set_brand_fact(settings, brand: str, subject: str, value: str, source: str, scope: str = "brand", today: date | None = None) -> dict:
    """Ticket 2a: not built yet. Close the row that is true today (it ends yesterday) and open a new one from today."""
    return {}


def make_get_brand_facts(settings, ws):
    """The catalogue's tool. The brand is bound from the trusted request, as in Session 1: the model never names it."""

    def get_brand_facts_tool() -> str:
        """This brand's facts that change over time (warranty, prices, launch dates), only the ones true today, each with
        its id in brackets, its source and since when. They win over the brand guide and over anything remembered."""
        rows = get_brand_facts(settings, ws.id)
        if not rows:
            return "No dated facts are recorded for this brand."
        return "\n".join(f"[brand_facts/{ws.id}/{r['subject']}] {r['subject']}: {r['value']} (true since {r['valid_from']}; source: {r['source']})" for r in rows)

    get_brand_facts_tool.__name__ = "get_brand_facts"
    get_brand_facts_tool.todo = getattr(get_brand_facts, "todo", False)  # the catalogue leaves it out until it is built
    return get_brand_facts_tool
