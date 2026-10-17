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
    soul = read_text(root / "SOUL.md", trace)
    agents = read_text(root / "AGENTS.md", trace)
    rules = yaml.safe_load(read_text(root / "rules.yaml", trace)) or {}
    return Workspace(id=workspace_id, root=root, soul=soul, agents=agents, rules=rules)
