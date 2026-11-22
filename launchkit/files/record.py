"""The record: what the agent produced in a conversation, written as it is produced.

Every tool that writes a file adds one entry the moment it has written it: the path, the tool that wrote it, the
message the turn is answering, and the time. The chat page lists a turn's files from this record, and keeps drafts
(anything under work/) out of what the marketer sees.

It is ready-made, and it switches on when stage 1 builds for_request. It is an append-only log, artifacts.jsonl,
one line per entry, opened for append and never read in order to add to it. research_many writes from five
subagents at once, and a log that is only ever appended to keeps all five entries.

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
    return Path(root) / "artifacts.jsonl"


def entries(root: Path) -> list[Entry]:
    """Everything this conversation produced, oldest first, with a retried write counted once.

    A last line cut short by a crash is skipped rather than raised into the chat.
    """
    file = _file(root)
    if not file.exists():
        return []
    seen, out = set(), []
    for line in file.read_text(encoding="utf-8").splitlines():
        try:
            entry = Entry(**json.loads(line))
        except (json.JSONDecodeError, TypeError):
            continue
        key = (entry.message, entry.by, entry.path)
        if key not in seen:
            seen.add(key)
            out.append(entry)
    return out


class Record:
    """One conversation's record. Writing never reads it: a write opens the file for append and adds one line.

    That is the whole fix. A record that was loaded when the tool was built can be as stale as it likes, because
    nothing is written back from it.
    """

    def __init__(self, root: Path):
        self.root = Path(root)

    def add(self, path: Path, by: str, message: str) -> None:
        line = json.dumps(asdict(Entry(path=Path(path).as_posix(), by=by, message=message, at=time.time()))) + "\n"
        file = _file(self.root)
        file.parent.mkdir(parents=True, exist_ok=True)
        with open(file, "a", encoding="utf-8") as log:
            log.write(line)


def record(root: Path, path: Path, by: str, message: str) -> None:
    """Write down one artifact, at the moment it is written, by the code that wrote it. One line, appended."""
    Record(root).add(path, by, message)
