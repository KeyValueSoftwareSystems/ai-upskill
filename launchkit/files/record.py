"""Stage 5: what the agent produced, written as it is produced.

Not built yet. The room builds this in stage 5, after watching the chat page show an Ember poster and none of
Maya's five briefs.

What it must do. Harbor's fourth sentence asks to see what the agent made next to the message that asked for it.
Today the chat page works that out by scanning data/ for anything modified since the run started, which is wrong
four ways at once. The record is written by whoever produces an artifact, at the moment it is written, carrying
the session, the message, the tool call and the writer, and the chat page reads it instead of scanning the disk.

Why as it goes rather than at the end. A turn that fails partway still produced files, and a record assembled
after a successful run is exactly the record you do not have when you most want it.

The ticket lived here. research_many writes from five subagents at once, so the record has to survive five writers
that never agreed to take turns. The first version kept a list and rewrote it: all five read it, all five wrote it
back from what they read, and the last one won. Every one of their edits would have matched exactly once, which is
why an edit tool's check does not help. This version is an append-only log, one line per entry, opened for append
and never read in order to add to it.

Two things it costs, worth saying in the room. A retry appends the same line twice, so an entry's identity is its
message, its writer and its path, and the reader collapses repeats. And the atomicity of an append is a property of
a local disk. On a bucket mount a write is a whole new object and there is no real append.

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
    """One conversation's record. It loads what is there when it is built, and every write after that adds to what it
    loaded and writes the whole list back.

    A write tool builds one when it is built, and a research subagent builds its own tool when it starts. So five
    subagents each load the same list before any of them has finished, and each writes it back with only its own entry
    added. That is the ticket: nothing errors, every file is on disk, and the last writer's list is the record.
    """

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
