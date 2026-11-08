"""Brand facts: things true about a brand, with the dates they were true.

Ready-made for tickets 2 and 3; build A fills the two slots. Reference: page 1, "Where a fact lives", and
page 7, "Lifetime".

A brand fact is not a memory about a person. "The warranty is five years" belongs to Harbor, not to Maya,
and it stops being true one day. So brand facts get their own table, with a subject, a value and two
dates, and plain code decides which value is current. The model never reads this table directly; the
prompt's `# Brand facts` section is built from `current()`.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Fact:
    """One row of the brand_facts table."""

    id: int
    workspace_id: str
    subject: str
    value: str
    scope: str
    source: str
    valid_from: date
    valid_to: date | None


class BrandFacts:
    """The brand_facts table in one SQLite file."""

    def __init__(self, db_file: str):
        self.db_file = db_file
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS brand_facts (
                       id INTEGER PRIMARY KEY,
                       workspace_id TEXT NOT NULL,
                       subject TEXT NOT NULL,
                       value TEXT NOT NULL,
                       scope TEXT NOT NULL,
                       source TEXT NOT NULL,
                       valid_from TEXT NOT NULL,
                       valid_to TEXT
                   )"""
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_file)

    def record(self, workspace_id: str, subject: str, value: str, *, source: str, valid_from: date) -> None:
        """Write a new value for a subject.

        Build A, ticket 2, fills this in: a new value should close the row that held the old value, by
        setting its valid_to to the day the new value became true. The placeholder only adds the new row,
        so two values for one subject both look current.
        """
        with self._connect() as db:
            # The new value ends the old one on the day it became true. The old row stays, so the history can be read.
            db.execute(
                "UPDATE brand_facts SET valid_to = ? WHERE workspace_id = ? AND subject = ? AND valid_to IS NULL AND valid_from <= ?",
                (valid_from.isoformat(), workspace_id, subject, valid_from.isoformat()),
            )
            db.execute(
                "INSERT INTO brand_facts (workspace_id, subject, value, scope, source, valid_from, valid_to) VALUES (?, ?, ?, ?, ?, ?, NULL)",
                (workspace_id, subject, value, f"brand:{workspace_id}", source, valid_from.isoformat()),
            )

    def current(self, workspace_id: str, today: date) -> list[Fact]:
        """The facts that are true on a given day, for one brand.

        Build A, ticket 2, fills this in: a fact is current when valid_from is on or before the day and
        valid_to is empty or after it. The placeholder returns every row of the brand.
        """
        valid = [f for f in self.history(workspace_id) if f.valid_from <= today and (f.valid_to is None or f.valid_to > today)]
        # Rows written before record() closed old values can both be open; the newest start wins, so the
        # database the room inherits reads right without a repair.
        latest: dict[str, Fact] = {}
        for fact in valid:
            if fact.subject not in latest or fact.valid_from >= latest[fact.subject].valid_from:
                latest[fact.subject] = fact
        return [f for f in valid if latest[f.subject] is f]

    def history(self, workspace_id: str, subject: str | None = None) -> list[Fact]:
        """Every row ever recorded for a brand, oldest first; one subject when given."""
        query = "SELECT id, workspace_id, subject, value, scope, source, valid_from, valid_to FROM brand_facts WHERE workspace_id = ?"
        params: tuple = (workspace_id,)
        if subject is not None:
            query += " AND subject = ?"
            params += (subject,)
        query += " ORDER BY valid_from, id"
        with self._connect() as db:
            rows = db.execute(query, params).fetchall()
        return [
            Fact(id=r[0], workspace_id=r[1], subject=r[2], value=r[3], scope=r[4], source=r[5],
                 valid_from=date.fromisoformat(r[6]), valid_to=date.fromisoformat(r[7]) if r[7] else None)
            for r in rows
        ]


def brand_facts_section(facts: list[Fact]) -> str:
    """The `# Brand facts` section of the prompt: one line per fact with the date it became true."""
    return "\n".join(f"- {f.subject}: {f.value}  (since {f.valid_from.isoformat()})" for f in facts)


def record_brand_fact_entry(facts: BrandFacts, workspace_id: str):
    """The tool the agent calls when someone states a brand fact. It is a write, so the approval rule applies."""

    def record_brand_fact(subject: str, value: str) -> str:
        """Record a fact about this brand that is true from today, for example subject "warranty",
        value "5 years". Use it when the person states something about the brand or its product,
        never for something about themselves."""
        facts.record(workspace_id, subject.strip().lower(), value.strip(), source="chat", valid_from=date.today())
        return f"recorded {subject}: {value}, true from today"

    return record_brand_fact
