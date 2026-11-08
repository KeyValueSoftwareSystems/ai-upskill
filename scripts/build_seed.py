"""Build samples/memory/seed.db from samples/memory/seed.yaml.

Run once, in prep: `uv run python scripts/build_seed.py`. The result is checked in; `launchkit setup`
copies it into data/ on a fresh clone. The room never runs this.

The rows go in past the door (`insert_raw`) and through the placeholder brand table, so the database
holds the bugs the tickets describe: no scope filtering, two open warranty rows, a web learning that
everyone reads.
"""

import sys
from datetime import date, datetime
from pathlib import Path

import yaml
from agno.db.schemas.memory import UserMemory
from agno.session.agent import AgentSession
from agno.session.summary import SessionSummary

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from launchkit.memory.brand_facts import BrandFacts  # noqa: E402
from launchkit.memory.store import MemoryStore  # noqa: E402
from launchkit.trace import Trace  # noqa: E402

SOURCE = ROOT / "samples" / "memory" / "seed.yaml"
TARGET = ROOT / "samples" / "memory" / "seed.db"


def written_on(topics: list[str]) -> int:
    """The row's valid_from date as a Unix timestamp, so created_at matches the story's dates."""
    for topic in topics:
        if topic.startswith("valid_from:"):
            return int(datetime.fromisoformat(topic.split(":", 1)[1]).timestamp())
    return int(datetime(2026, 5, 1).timestamp())


def main() -> int:
    if TARGET.exists():
        TARGET.unlink()
    data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    store = MemoryStore(str(TARGET), "harbor", "seed", Trace())
    for row in data["memories"]:
        topics = list(row["topics"])
        store.insert_raw(UserMemory(memory=row["memory"], user_id=row["user_id"], topics=topics, created_at=written_on(topics), updated_at=written_on(topics)))
    facts = BrandFacts(str(TARGET))
    for fact in data["brand_facts"]:
        valid_from = fact["valid_from"] if isinstance(fact["valid_from"], date) else date.fromisoformat(str(fact["valid_from"]))
        facts.record(fact["workspace_id"], fact["subject"], fact["value"], source=fact["source"], valid_from=valid_from)
    for session in data["sessions"]:
        store.upsert_session(
            AgentSession(
                session_id=session["session_id"],
                user_id=session["user_id"],
                agent_id="main",
                summary=SessionSummary(summary=session["summary"], updated_at=datetime(2026, 10, 2)),
                created_at=int(datetime(2026, 10, 2).timestamp()),
                updated_at=int(datetime(2026, 10, 2).timestamp()),
            )
        )
    print(f"wrote {TARGET.relative_to(ROOT)}: {len(data['memories'])} memory rows, {len(data['brand_facts'])} brand facts, {len(data['sessions'])} sessions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
