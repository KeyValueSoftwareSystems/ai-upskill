"""Ticket 2a: brand facts LaunchKit owns, in its own table in the project database. One row is one fact and when it was
true: subject, value, scope, source, valid_from, valid_to (empty while it is still true). Plain code reads it: no model.
A new value never overwrites the old one: the old row is closed the day before, and a new row opens today."""

import sqlite3
from contextlib import closing
from datetime import date, timedelta

# Harbor's warranty, as two rows: two years until it changed in March, five years from April and still true.
SEED = [
    ("harbor", "warranty", "2 years", "brand", "Harbor product sheet, 2025", "2025-01-01", "2026-03-31"),
    ("harbor", "warranty", "5 years", "brand", "Harbor product sheet, April 2026", "2026-04-01", None),
]


def _open(settings) -> sqlite3.Connection:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(settings.data_dir / "sessions.db")
    con.row_factory = sqlite3.Row
    con.execute("create table if not exists brand_facts (id integer primary key, brand text not null, subject text not null, value text not null, "
                "scope text not null, source text not null, valid_from text not null, valid_to text)")
    if con.execute("select count(*) from brand_facts").fetchone()[0] == 0:
        con.executemany("insert into brand_facts (brand, subject, value, scope, source, valid_from, valid_to) values (?, ?, ?, ?, ?, ?, ?)", SEED)
        con.commit()
    return con


def get_brand_facts(settings, brand: str, today: date | None = None) -> list[dict]:
    """The brand's facts that are true today, one per subject."""
    day = (today or date.today()).isoformat()
    with closing(_open(settings)) as con:
        rows = con.execute("select subject, value, scope, source, valid_from from brand_facts where brand = ? and valid_from <= ? "
                           "and (valid_to is null or valid_to >= ?) order by subject", (brand, day, day)).fetchall()
    return [dict(r) for r in rows]


def all_brand_facts(settings, brand: str, today: date | None = None) -> list[dict]:
    """Every row, old ones too, with whether it is true today: what the Memory tab shows."""
    day = (today or date.today()).isoformat()
    with closing(_open(settings)) as con:
        rows = con.execute("select * from brand_facts where brand = ? order by subject, valid_from", (brand,)).fetchall()
    return [{**dict(r), "true_today": r["valid_from"] <= day and (r["valid_to"] is None or r["valid_to"] >= day)} for r in rows]


def set_brand_fact(settings, brand: str, subject: str, value: str, source: str, scope: str = "brand", today: date | None = None) -> dict:
    """Close the row that is true today (it ends yesterday) and open a new one from today."""
    day = today or date.today()
    with closing(_open(settings)) as con, con:
        con.execute("update brand_facts set valid_to = ? where brand = ? and subject = ? and valid_to is null", ((day - timedelta(days=1)).isoformat(), brand, subject))
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
    return get_brand_facts_tool
