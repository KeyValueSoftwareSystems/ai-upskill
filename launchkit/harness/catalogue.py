"""The main agent's catalogue: every tool it can use, each with a "pick me when" note and a read/write flag,
and every skill: a plain-words how-to in launchkit/skills/<name>/skill.md.

Before run_tool is built, the agent holds every built tool directly and the prompt lists the skills. Once it is
built, the agent holds three doors instead: find_tool, run_skill and run_tool. A slot that is not built yet
stays out of the catalogue.
"""

import inspect
import json
import re
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
        self.leash: Callable | None = None

    @property
    def lookup(self) -> bool:
        return built(self.make_run_tool())

    def agent_tools(self) -> list[Callable]:
        if self.lookup:
            return [self.make_find_tool(), self.make_run_skill(), self.make_run_tool()]
        tools = [e.fn for e in self.entries.values()]
        return tools + [self.make_run_skill()] if self.skills else tools

    def skills_text(self) -> str:
        if not self.skills or self.lookup:
            return ""
        return "Skills you can load with run_skill:\n" + "\n".join(f"- {s.name}: {s.note}" for s in self.skills.values())

    def make_run_skill(self):
        def run_skill(name: str) -> str:
            skill = self.skills.get(name)
            if skill is None:
                return f"No skill named {name}."
            if not self.lookup:
                return skill.text
            uses = [self.entries[t] for t in re.split(r"[,\s]+", field_of(skill.text, "uses")) if t in self.entries]
            calls = "\nThe calls for these steps:\n" + "\n".join(f"- {call_shape(e)}: {e.note}" for e in uses) if uses else ""
            return skill.text + calls + "\nDo the steps now, one call at a time, through run_tool."

        if self.lookup:
            run_skill.__doc__ = "Load a skill by name. It returns the steps to follow; follow them."
        else:
            listed = "; ".join(f"{s.name}: {s.note}" for s in self.skills.values())
            run_skill.__doc__ = f"Load a skill's steps. When a skill fits the job, call this before any other tool, then follow its steps. Skills: {listed}"
        return run_skill

    def make_find_tool(self, top: int = 5):
        hidden = {name for s in self.skills.values() for name in s.hides}

        def find_tool(query: str) -> str:
            """List the skills and tools that could help with a job, best first, each with when to pick it. Call this first."""
            lines = [(f'skill {s.name}: {s.note} · call run_skill("{s.name}")', f"{s.name} {s.note}") for s in self.skills.values()]
            lines += [(f"tool {e.name} ({e.kind}): {e.note} · call {call_shape(e)}", f"{e.name} {e.note}") for e in self.entries.values() if e.name not in hidden]
            asked = stems(query)
            ranked = sorted(lines, key=lambda line: -len(asked & stems(line[1])))
            best = [shown for shown, words in ranked if asked & stems(words)][:top]
            return "\n".join(best) if best else "Nothing fits. Search again with other words, or ask the marketer."

        return find_tool

    def make_run_tool(self):
        def run_tool(name: str, inputs: dict) -> str:
            """Run a tool from the catalogue by name, with its inputs as an object."""
            entry = self.entries.get(name.removeprefix("functions."))
            if entry is None:
                return f"No tool named {name}. Call find_tool to see what exists."
            try:
                inspect.signature(entry.fn).bind(**inputs)
            except TypeError as error:
                return f"Wrong inputs for {name}: {error}. Check the skill's steps or call find_tool."
            if entry.kind == "write" and not self.approve(name, inputs):
                self.trace.refused(name, "Maya said no")
                return f"Maya did not allow {name}. Do not try it again; tell her what you wanted to do."
            if self.leash is None:
                result = entry.fn(**inputs)
                self.trace.tool(name, inputs, result)
            else:
                result = self.leash(name, entry.fn, inputs)
            return result if isinstance(result, str) else json.dumps(result)

        return run_tool

def call_shape(entry: Entry) -> str:
    """The exact call to make, e.g. run_tool("crop", {"width": int, "height": int}). Optional inputs are left out."""
    params = [p for p in inspect.signature(entry.fn).parameters.values() if p.default is inspect.Parameter.empty]
    inputs = ", ".join(f'"{p.name}": {getattr(p.annotation, "__name__", "value")}' for p in params)
    return f'run_tool("{entry.name}", {{{inputs}}})'


def stems(text: str) -> set[str]:
    """Words, cut to their first five letters, so "competitors" meets "competitor" and "sizes" meets "size"."""
    return {w[:5] for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 2} - {"the", "and", "for", "you", "with", "this"}
