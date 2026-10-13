from dataclasses import dataclass, field
from pathlib import Path

import yaml

from launchkit.harness.trace import Trace


@dataclass
class Workspace:
    id: str
    root: Path
    soul: str = ""
    agents: str = ""
    rules: dict = field(default_factory=dict)

    @property
    def colours(self) -> dict:
        return self.rules.get("colours", {})


def read_text(path: Path, trace: Trace) -> str:
    trace.file(path)
    return path.read_text(encoding="utf-8")


def load_workspace(workspace_id: str, settings, trace: Trace) -> Workspace:
    root = settings.workspaces_dir / workspace_id
    # TODO step 1: read SOUL.md, AGENTS.md and rules.yaml with read_text and fill the Workspace
    trace.note("no workspace files read yet, step 1 fills this")
    return Workspace(id=workspace_id, root=root)
