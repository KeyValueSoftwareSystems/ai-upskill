"""Stage 1: the folder one conversation owns.

Every file the agent writes for one conversation lands in one place, with drawers inside it that say what a file
is for. outputs/ is finished work the marketer sees, work/ is drafts and rejected variants that exist and are not
shown, uploads/ is what the person attached, competitors/ is the research.

The brand and the conversation both come from the request, never from an argument a tool passes in and never from
anything the model writes. That is the rule the rest of the session rests on.

Conversations live under data/files/<brand>/<conversation>. The brand's own files, brand-book.md and rules.yaml,
stay where they were, under workspaces/<brand>, outside every conversation's folder.

Reference page 3, Where the work lives.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from launchkit.brands.request import Request, resolve_workspace_id

DRAWERS = ("uploads", "work", "outputs", "competitors")
CONVERSATION = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


@dataclass(frozen=True)
class Workspace:
    brand: str
    conversation: str
    root: Path       # this conversation's folder, under data/files/<brand>/<conversation>
    shared: Path     # the brand's own files, workspaces/<brand>. Read by the agent, never written, and outside root.

    def drawer(self, name: str) -> Path:
        """One drawer inside this workspace, made on first use. A name that is not a drawer is a mistake worth catching here."""
        if name not in DRAWERS:
            raise ValueError(f"{name!r} is not a drawer: {', '.join(DRAWERS)}")
        path = self.root / name
        path.mkdir(parents=True, exist_ok=True)
        return path


def for_request(request: Request, settings) -> Workspace:
    """The workspace this request owns."""
    brand = resolve_workspace_id(request, settings)
    if not CONVERSATION.fullmatch(request.session_id):
        raise ValueError(f"{request.session_id!r} is not a conversation id")
    return Workspace(
        brand=brand,
        conversation=request.session_id,
        root=settings.data_dir / "files" / brand / request.session_id,
        shared=settings.workspaces_dir / brand,
    )
