"""Stage 1: the folder one conversation owns.

Not built yet. The room builds this in stage 1, after watching Maya ask for Monday's brief and get a new one.

What it must do. Take the brand and the conversation from the request, never from an argument a tool passes in
and never from anything the model writes, and give back one folder with drawers inside it: uploads, work,
outputs, competitors. Drawers decide what the Files panel shows later: outputs/ is finished work, work/ is
drafts and rejected variants.

The checks in checks/test_files.py read `Workspace` as a folder per conversation, because that is the answer the
branch expects the room to reach. If the room chooses another layout, the lead adapts the checks.

Reference page 3, Where the work lives.
"""

from dataclasses import dataclass
from pathlib import Path

from launchkit.brands.request import Request

DRAWERS = ("uploads", "work", "outputs", "competitors")


@dataclass(frozen=True)
class Workspace:
    brand: str
    conversation: str
    root: Path       # this conversation's folder, under data/files/<brand>/<conversation>
    shared: Path     # the brand's own files, workspaces/<brand>. Read by the agent, never written, and outside root.

    def drawer(self, name: str) -> Path:
        raise NotImplementedError("stage 1: a drawer inside this conversation's folder, made on first use")


def for_request(request: Request, settings) -> Workspace:
    raise NotImplementedError("stage 1: the workspace this request owns")
