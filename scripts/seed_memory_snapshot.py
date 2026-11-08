"""Prep only: build the memory database as it stood the morning the support queue filled, and write it to fixtures/.

    uv run python scripts/seed_memory_snapshot.py

Writes fixtures/memory-snapshot.db (the project database: Agno's own tables) and fixtures/memory-snapshot-learnings/
(the LanceDB folder behind learned knowledge; Agno keeps a learning's text there and only its title and tags in SQLite).
The room never runs this: the snapshot is checked in, and `uv run launchkit memory reset` copies it into data/.
Every name, number and token below is invented. The model is never called; the same input gives the same rows.
"""

import random
import shutil
import sqlite3
import sys
import tempfile
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agno.db.schemas import UserMemory  # noqa: E402
from agno.learn.schemas import DecisionLog, EntityMemory  # noqa: E402
from agno.session.agent import AgentSession  # noqa: E402
from agno.session.summary import SessionSummary  # noqa: E402

from launchkit.memory.chat_history import session_db  # noqa: E402
from launchkit.memory.long_term import learning_machine  # noqa: E402
from launchkit.settings import settings as base_settings  # noqa: E402

FIXTURES = ROOT / "fixtures"
SNAPSHOT = FIXTURES / "memory-snapshot.db"
LEARNINGS = FIXTURES / "memory-snapshot-learnings"

MEMORY_ON = datetime(2026, 5, 4, 9, 0, tzinfo=timezone.utc)  # update_memory_on_run=True shipped
QUEUE_FILLED = datetime(2026, 11, 2, 8, 0, tzinfo=timezone.utc)  # the morning of the snapshot
AGENCY_MANAGER = "Dana Whitlock"  # invented; account manager at the invented Fieldnote Agency
PHONE = "07700 900461"  # in the UK range set aside for fiction
TOKEN = "lkdemo-board-token-7f3a91c2e8b4d605"  # invented; not any real service's format


def ts(day: datetime) -> int:
    return int(day.timestamp())


def between(rng: random.Random, start: datetime = MEMORY_ON, end: datetime = QUEUE_FILLED) -> int:
    return rng.randint(ts(start), ts(end))


NAVY = [
    "Maya prefers Harbor navy as the main colour.",
    "Maya likes navy backgrounds on Harbor posters.",
    "Maya wants navy (#1F3A5F) to lead every Harbor layout.",
    "Maya prefers navy over sand for headline panels.",
    "Maya said navy should be the dominant colour.",
    "Maya likes a deep navy colour scheme.",
    "Maya wants Harbor navy behind the bottle.",
    "Maya prefers dark navy for the Tidal story size.",
    "Maya likes the navy and sea glass pairing, navy first.",
    "Maya asked for more navy in the feed posts.",
    "Maya prefers navy as the background colour for posters.",
]

MAYA_OTHER = [
    ("Maya is the marketing lead at Harbor.", ["work"]),
    ("Maya prefers short sentences and no exclamation marks.", ["style"]),
    ("Maya always wants a PNG and a PDF attached to finished sizes.", ["preferences", "files"]),
    ("Maya is preparing the Tidal launch; it launches in six weeks.", ["tidal", "launch"]),
    ("Maya's team posts on Tuesdays and Thursdays.", ["schedule"]),
    ("Maya likes to see the story size first.", ["preferences"]),
    ("Maya dislikes stock photos of beaches.", ["preferences", "pictures"]),
    ("Maya likes headlines under six words.", ["style"]),
    ("The Breeze colourway is pale blue and sand.", ["breeze", "product"]),
    ("Maya wants the Breeze shoot on a windy ridge.", ["breeze", "shoot"]),
    ("Maya asks for three headline options each time.", ["preferences"]),
    ("Maya prefers British spelling.", ["style"]),
    ("Maya works with Sam, the Harbor intern.", ["work"]),
    ("Maya reviews drafts on Friday mornings.", ["schedule"]),
    ("The Tidal launch brief lives on Harbor's Notion board.", ["tidal", "board"]),
    ("Maya likes a calm, outdoorsy tone.", ["style"]),
    ("Harbor's audience is weekend hikers and weekday commuters.", ["audience"]),
    ("Maya wants the web banner checked so the bottle base is not cut off.", ["sizes"]),
    ("For Breeze, never mention the lid.", ["breeze", "rules"]),
    ("Maya likes sea glass as an accent colour.", ["colours"]),
    ("Maya prefers the shoot photo over AI pictures.", ["pictures"]),
    ("Maya wants competitor research as one paragraph per brand.", ["research"]),
    ("Maya's Tidal voice-over should stay under ten seconds.", ["tidal", "audio"]),
    ("Maya is based in the Bristol office.", ["personal"]),
]

MAYA_PLANTED = [
    ("Maya wants headlines to mention the lifetime guarantee.", ["preferences", "headlines"], None),  # the inverted rule
    ("Harbor warranty is 2 years.", ["product", "warranty"], datetime(2026, 5, 12, 10, 30, tzinfo=timezone.utc)),
    (f"Maya is following up with customer Callum Ferris ({PHONE}) about a dented Tidal bottle.", ["customers"], None),
    (f"Maya's board API token is {TOKEN}.", ["board", "access"], None),
]

AGENCY = [
    (f"The user's name is {AGENCY_MANAGER}, an account manager at Fieldnote Agency.", ["personal"]),
    ("Works across several client brands in the same afternoon.", ["work"]),
    ("Prefers navy #1F3A5F as the lead colour.", ["colours"]),
    ("Accent colours are sea glass and sand.", ["colours"]),
    ("Never say 'lifetime guarantee', 'eco-friendly', 'sustainable', 'unbreakable', 'cold forever' or 'fully dishwasher-safe'.", ["rules"]),
    ("Sizes needed: 1080x1080, 1080x1350, 1080x1920, 1200x628 and 300x250.", ["sizes"]),
    ("Headlines up to six words, subheadlines up to twelve.", ["style"]),
    ("Bottle should always be shown whole, never cropped at the base.", ["pictures"]),
    ("Audience is weekend hikers and weekday commuters.", ["audience"]),
    ("Likes moss green for spring work.", ["colours"]),
    ("Spring poster series is due on 20 March.", ["schedule"]),
    ("Prefers bullet-point summaries at the end of a reply.", ["style"]),
    ("Wants the product name in every headline.", ["style"]),
    ("Sends finished files to the client on Mondays.", ["schedule"]),
    ("Prefers a warm, plain voice with no jargon.", ["style"]),
    ("Uses the feed square size most.", ["sizes"]),
    ("Calm tone; short sentences; no emoji.", ["style"]),
    ("Asks for two headline options, not three.", ["preferences"]),
]

POWER_SUBJECTS = ["feed posts", "story ads", "web banners", "display ads", "email headers", "voice-overs", "launch decks", "trend reports", "competitor notes", "shoot briefs"]
POWER_LIKES = [
    "a question as the opening line", "the product in the lower third", "three options to choose from", "one emoji-free line under the headline",
    "a numbered list in the brief", "the price kept out", "a sunrise palette", "the logo top left", "a one-line summary first", "British spelling",
    "a quiet, plain voice", "the headline in sentence case", "a call to action under four words", "trail photos over city photos", "no stock models",
    "the date in the file name", "a draft by Wednesday", "the hikers' angle, not the commuters'", "sources listed at the end", "a word count beside each line",
]
POWER_EXTRA = [
    "for the autumn push", "for the Tidal launch", "for the Breeze week", "when the brief is short", "for the weekend posts",
    "after the Monday stand-up", "for the agency hand-off", "for the newsletter", "for the retail partners", "for the summer recap",
]


def memories() -> list[UserMemory]:
    rng = random.Random(3)
    rows: list[tuple[str, str, list[str], int]] = []
    for text in NAVY:
        rows.append(("maya", text, ["preferences", "colours"], between(rng)))
    for text, topics in MAYA_OTHER:
        rows.append(("maya", text, topics, between(rng)))
    for text, topics, when in MAYA_PLANTED:
        rows.append(("maya", text, topics, ts(when) if when else between(rng)))
    for text, topics in AGENCY:
        rows.append(("agency-manager", text, topics, between(rng)))
    seen = set()
    while len(seen) < 600:
        line = f"Prefers {rng.choice(POWER_LIKES)} in {rng.choice(POWER_SUBJECTS)} {rng.choice(POWER_EXTRA)}."
        if line not in seen:
            seen.add(line)
            rows.append(("power-user", line, ["preferences", "marketing"], between(rng)))
    return [
        UserMemory(memory=text, memory_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{user}/{text}")), user_id=user, topics=topics,
                   input=text, agent_id="launchkit-main", created_at=when, updated_at=when)
        for user, text, topics, when in rows
    ]


def summaries() -> list[AgentSession]:
    """Two of the agency manager's sessions, each with the summary Agno would have kept. Both name her."""
    rows = [
        ("harbor", "a1b2c3", f"{AGENCY_MANAGER} from Fieldnote Agency cut Harbor's Tidal poster to every size and checked the never-say list.", ["harbor", "sizes"]),
        ("alder", "d4e5f6", f"{AGENCY_MANAGER} drafted Alder's spring poster headlines and asked for navy accents like the Harbor work.", ["alder", "headlines"]),
    ]
    out = []
    for wid, sid, text, topics in rows:
        when = datetime(2026, 10, 20 if wid == "harbor" else 27, 15, 0, tzinfo=timezone.utc)
        out.append(AgentSession(session_id=f"{wid}:agency-manager:{sid}:main", agent_id="launchkit-main", user_id="agency-manager",
                                summary=SessionSummary(summary=text, topics=topics, updated_at=when), created_at=ts(when), updated_at=ts(when)))
    return out


def build(data_dir: Path) -> None:
    settings = replace(base_settings, data_dir=data_dir)
    db = session_db(settings)
    for memory in memories():
        db.upsert_user_memory(memory, deserialize=True)
    for session in summaries():
        db.upsert_session(session)
    machine = learning_machine(settings)
    machine.learned_knowledge_store.save(
        title=f"{AGENCY_MANAGER}'s tip: lead every poster with navy",
        learning=f"{AGENCY_MANAGER} (Fieldnote Agency) found that posters leading with navy #1F3A5F and a sea glass accent get approved first time.",
        context="Poster colour choices", tags=["colours", "posters"], agent_id="launchkit-main", namespace="global",
    )
    harbor = EntityMemory(entity_id="harbor", entity_type="company", name="Harbor", description="Insulated bottles for weekend hikers.")
    harbor.add_fact("Lead colour is navy #1F3A5F.")
    harbor.add_fact("Never-say list: lifetime guarantee, eco-friendly, sustainable, unbreakable, cold forever, fully dishwasher-safe.")
    machine.entity_memory_store._save_entity(harbor, agent_id="launchkit-main", namespace="global")
    for n, (decision, why) in enumerate([
        ("Used navy as the lead colour on the Tidal feed square.", f"{AGENCY_MANAGER} asked for it."),
        ("Cut the web banner around the bottle, not from the centre.", "The bottle base was cut off."),
    ]):
        machine.decision_log_store.save(DecisionLog(id=f"decision-agency-{n}", decision=decision, reasoning=why, decision_type="design",
                                                    session_id="harbor:agency-manager:a1b2c3:main", user_id="agency-manager", agent_id="launchkit-main",
                                                    created_at=datetime(2026, 10, 20, 15, n, tzinfo=timezone.utc).isoformat()))
    # Agno stamps learnings with the time they are written; put them back on the dates they happened in the story.
    with sqlite3.connect(data_dir / "sessions.db") as con:
        when = ts(datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc))
        con.execute("update agno_learnings set created_at = ?, updated_at = ?", (when, when))
        con.execute("update agno_knowledge set created_at = ?, updated_at = ?", (when, when))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        build(Path(tmp))
        FIXTURES.mkdir(exist_ok=True)
        SNAPSHOT.unlink(missing_ok=True)
        with sqlite3.connect(Path(tmp) / "sessions.db") as source, sqlite3.connect(SNAPSHOT) as target:
            source.backup(target)  # a plain copy would miss rows still in SQLite's write-ahead log
        shutil.rmtree(LEARNINGS, ignore_errors=True)
        shutil.copytree(Path(tmp) / "learnings", LEARNINGS)
    print(f"wrote {SNAPSHOT.relative_to(ROOT)} and {LEARNINGS.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
