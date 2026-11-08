"""Ticket 2: brand facts LaunchKit owns, in its own table in the project database. One row is one fact and when it was
true: subject, value, scope, source, valid_from, valid_to (empty while it is still true). Plain code reads it: no model.
A new value never overwrites the old one: the old row is closed the day before, and a new row opens today.

Where the rows come from: each brand's own workspaces/<brand>/brand_facts.yaml, the dated part of its product sheet.
load_brand_facts copies the file's entries into the table; after that a change goes through propose_brand_fact and a
yes (ticket 4), or through the file. Until ticket 2 is built the table stays empty."""

import sqlite3
from contextlib import closing
from datetime import date, timedelta

import yaml



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


def load_brand_facts(settings, brand: str) -> int:
    """Copy the brand's file entries into the table, skipping any already there (same brand, subject and valid_from),
    so loading twice adds nothing and a row closed later stays closed. How many rows were added."""
    added = 0
    with closing(_open(settings)) as con, con:
        for e in brand_file_facts(settings, brand):
            if con.execute("select 1 from brand_facts where brand = ? and subject = ? and valid_from = ?", (e["brand"], e["subject"], e["valid_from"])).fetchone():
                continue
            con.execute("insert into brand_facts (brand, subject, value, scope, source, valid_from, valid_to) values (?, ?, ?, ?, ?, ?, ?)",
                        (e["brand"], e["subject"], e["value"], e["scope"], e["source"], e["valid_from"], e["valid_to"]))
            added += 1
    return added


def get_brand_facts(settings, brand: str, today: date | None = None) -> list[dict]:
    """The brand's facts that are true on today (default: the real today), one per subject."""
    load_brand_facts(settings, brand)
    day = (today or date.today()).isoformat()
    with closing(_open(settings)) as con:
        rows = con.execute("select subject, value, scope, source, valid_from from brand_facts where brand = ? and valid_from <= ? "
                           "and (valid_to is null or valid_to >= ?) order by subject", (brand, day, day)).fetchall()
    return [dict(r) for r in rows]


def all_brand_facts(settings, brand: str, today: date | None = None) -> list[dict]:
    """Every row, old ones too, with whether it is true today: what the Memory tab shows."""
    load_brand_facts(settings, brand)
    day = (today or date.today()).isoformat()
    with closing(_open(settings)) as con:
        rows = con.execute("select * from brand_facts where brand = ? order by subject, valid_from", (brand,)).fetchall()
    return [{**dict(r), "true_today": r["valid_from"] <= day and (r["valid_to"] is None or r["valid_to"] >= day)} for r in rows]


def set_brand_fact(settings, brand: str, subject: str, value: str, source: str, scope: str = "brand", today: date | None = None) -> dict:
    """Never overwrite: in one transaction, close the open row for this subject (it ends yesterday) and open a new one from today."""
    load_brand_facts(settings, brand)
    day = today or date.today()
    with closing(_open(settings)) as con, con:  # the inner `with con` commits both statements together, or neither
        con.execute("update brand_facts set valid_to = ? where brand = ? and subject = ? and valid_to is null",
                    ((day - timedelta(days=1)).isoformat(), brand, subject))
        con.execute("insert into brand_facts (brand, subject, value, scope, source, valid_from, valid_to) values (?, ?, ?, ?, ?, ?, null)",
                    (brand, subject, value, scope, source, day.isoformat()))
    return {"brand": brand, "subject": subject, "value": value, "source": source, "valid_from": day.isoformat()}


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
