"""The record: what the agent produced in a conversation, written as it is produced.

Every tool that writes a file adds one entry the moment it has written it: the path, the tool that wrote it, the
message the turn is answering, and the time. The chat page lists a turn's files from this record, and keeps drafts
(anything under work/) out of what the marketer sees.

It lives in the conversation's own folder, as artifacts.json, a JSON list of Entry rows. A Record loads that list when
it is built and keeps it, and every add() appends one entry to it and writes the whole list back. A write tool builds
one Record when the tool is built, and a research subagent builds its own tool when it starts.

Reference page 11, Recording what the agent produced.
"""

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    """One artifact the agent produced. `path` is relative to the workspace, so the record survives a move."""

    path: str
    by: str          # the tool that wrote it
    message: str     # the message this turn is answering
    at: float


def _file(root: Path) -> Path:
    return Path(root) / "artifacts.json"


def entries(root: Path) -> list[Entry]:
    """Everything this conversation produced, oldest first."""
    file = _file(root)
    if not file.exists():
        return []
    try:
        return [Entry(**row) for row in json.loads(file.read_text(encoding="utf-8"))]
    except (json.JSONDecodeError, TypeError):
        return []


class Record:
    """One conversation's record. It loads what is there when it is built, and every write adds to that list and
    writes the whole list back."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.items = entries(self.root)

    def add(self, path: Path, by: str, message: str) -> None:
        self.items.append(Entry(path=Path(path).as_posix(), by=by, message=message, at=time.time()))
        file = _file(self.root)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps([asdict(e) for e in self.items], indent=2), encoding="utf-8")


def record(root: Path, path: Path, by: str, message: str) -> None:
    """Write down one artifact, at the moment it is written, by the code that wrote it."""
    Record(root).add(path, by, message)
