"""The main agent's catalogue: every tool it can use, each with a "pick me when" note and a read/write flag.

Today the agent holds every built tool directly. A slot that is not built yet stays out of the catalogue.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from launchkit.harness.trace import Trace

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


@dataclass(frozen=True)
class Entry:
    name: str
    note: str
    kind: str
    fn: Callable


def built(fn: Callable) -> bool:
    return not getattr(fn, "todo", False)


def ask_in_terminal(name: str, inputs: dict) -> bool:
    answer = input(f"\nMaya, the agent wants to {name}({json.dumps(inputs)}). Allow? [y/N] ")
    return answer.strip().lower() in ("y", "yes")


class Catalogue:
    def __init__(self, entries: list[Entry], trace: Trace, approve: Callable[[str, dict], bool]):
        self.entries = {e.name: e for e in entries if built(e.fn)}
        self.trace = trace
        self.approve = approve

    def agent_tools(self) -> list[Callable]:
        return [e.fn for e in self.entries.values()]
