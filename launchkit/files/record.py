"""Stage 5: what the agent produced, written as it is produced.

Not built yet. The room builds this in stage 5, after watching the chat page show an Ember poster and none of
Maya's five briefs.

What it must do. Harbor's fourth sentence asks to see what the agent made next to the message that asked for it.
Today the chat page works that out by scanning data/ for anything modified since the run started, which is wrong
four ways at once. The record is written by whoever produces an artifact, at the moment it is written, carrying
the session, the message, the tool call and the writer, and the chat page reads it instead of scanning the disk.

Why as it goes rather than at the end. A turn that fails partway still produced files, and a record assembled
after a successful run is exactly the record you do not have when you most want it.

research_many writes from five subagents at once, so keep that in mind when you decide what a write does.

Reference page 11, Recording what the agent produced.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    """One artifact the agent produced. `path` is relative to the workspace, so the record survives a move."""

    path: str
    by: str          # the tool that wrote it
    message: str     # the message this turn is answering
    at: float


def record(root: Path, path: Path, by: str, message: str) -> None:
    raise NotImplementedError("stage 5: write down one artifact, at the moment it is written")


def entries(root: Path) -> list[Entry]:
    raise NotImplementedError("stage 5: everything this conversation produced, oldest first")
