"""The main agent's catalogue: every tool it can use, each with a "pick me when" note and a read/write flag,
and every skill: a plain-words how-to in launchkit/skills/<name>/skill.md.

Today the agent holds every built tool directly, and the prompt lists the skills. A slot that is not built
yet stays out of the catalogue.
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


@dataclass(frozen=True)
class Skill:
    name: str
    note: str
    text: str
    hides: tuple[str, ...] = ()


def built(fn: Callable) -> bool:
    return not getattr(fn, "todo", False)


def field_of(text: str, name: str) -> str:
    return next((line.split(":", 1)[1].strip() for line in text.splitlines() if line.lower().startswith(f"{name}:")), "")


def load_skills(folder: Path = SKILLS_DIR) -> dict[str, Skill]:
    """Every skills/<name>/skill.md. Its 'Pick me when:' line is its note; its 'Hides:' line names the raw tools it prefers over."""
    skills = {}
    for path in sorted(folder.glob("*/skill.md")):
        text = path.read_text(encoding="utf-8")
        hides = tuple(t.strip(" `") for t in field_of(text, "hides").split("(")[0].split(",") if t.strip(" `"))
        skills[path.parent.name] = Skill(path.parent.name, field_of(text, "pick me when"), text, hides)
    return skills


def ask_in_terminal(name: str, inputs: dict) -> bool:
    answer = input(f"\nMaya, the agent wants to {name}({json.dumps(inputs)}). Allow? [y/N] ")
    return answer.strip().lower() in ("y", "yes")


class Catalogue:
    def __init__(self, entries: list[Entry], skills: dict[str, Skill], trace: Trace, approve: Callable[[str, dict], bool]):
        self.entries = {e.name: e for e in entries if built(e.fn)}
        self.skills = skills
        self.trace = trace
        self.approve = approve

    def agent_tools(self) -> list[Callable]:
        tools = [e.fn for e in self.entries.values()]
        return tools + [self.make_run_skill()] if self.skills else tools

    def skills_text(self) -> str:
        if not self.skills:
            return ""
        return "Skills you can load with run_skill:\n" + "\n".join(f"- {s.name}: {s.note}" for s in self.skills.values())

    def make_run_skill(self):
        def run_skill(name: str) -> str:
            skill = self.skills.get(name)
            return skill.text if skill else f"No skill named {name}."

        listed = "; ".join(f"{s.name}: {s.note}" for s in self.skills.values())
        run_skill.__doc__ = f"Load a skill's steps. When a skill fits the job, call this before any other tool, then follow its steps. Skills: {listed}"
        return run_skill
