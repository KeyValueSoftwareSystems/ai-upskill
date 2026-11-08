"""What is never a memory about a person. Plain code, no model.

held_back() asks two questions. The main agent leaves a row it holds back out of the prompt, and save_memory refuses a
new note it holds back before anyone is asked.

brand_fact     ticket 3: a row naming any brand's colour, size or never-say phrase, or a subject the brand facts table
               owns, belongs to a brand, not a person. Brand facts go in through propose_brand_fact.
personal_data  ticket 6: a phone number, an email address or a token. Code backs up the capture rules.
"""

import re
from functools import lru_cache
from pathlib import Path

import yaml


def held_back(text: str, settings) -> str | None:
    """Why this row is not a memory about the person, or None when it is one."""
    return personal_data(text) or brand_fact(text, settings)


@lru_cache(maxsize=8)
def brand_words(workspaces_dir: Path) -> tuple[str, ...]:
    """Every word a brand file owns: never-say phrases, colour names and codes, sizes, and the subjects in brand_facts.yaml."""
    words = set()
    for facts_file in sorted(workspaces_dir.glob("*/brand_facts.yaml")):
        words |= {subject.lower() for subject in (yaml.safe_load(facts_file.read_text(encoding="utf-8")) or {})}
    for rules_file in sorted(workspaces_dir.glob("*/rules.yaml")):
        rules = yaml.safe_load(rules_file.read_text(encoding="utf-8")) or {}
        words |= {claim.lower() for claim in rules.get("banned_claims", [])}
        for name, hex_code in rules.get("colours", {}).items():
            words |= {name.replace("_", " ").lower(), str(hex_code).lower()}
        words |= {size.lower() for group in rules.get("placements", {}).values() for size in group}
    return tuple(sorted(words))


def brand_fact(text: str, settings) -> str | None:
    """The reason, when the text names a word from any brand's files as a whole word; else None."""
    lowered = text.lower()
    for word in brand_words(settings.workspaces_dir):
        # Not inside a longer word ("sand" in "thousand"), and a colour code not after another # ("##1f3a5f").
        if re.search(rf"(?<![\w#]){re.escape(word)}(?!\w)", lowered):
            return f'a brand fact ("{word}"): it belongs to the brand, not the person'
    return None


PERSONAL = [
    ("a phone number", re.compile(r"\+?\d[\d ()-]{8,}\d")),
    ("an email address", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("a token or key", re.compile(r"\b(?:token|api key|password|secret)\b|\b(?=[\w-]*\d)(?=[\w-]*[a-z])[\w-]{24,}\b", re.I)),
]


def personal_data(text: str) -> str | None:
    """The reason, when the text holds a phone number (10 digits or more, so a date is not one), an email address or a
    token; else None."""
    for kind, pattern in PERSONAL:
        found = [m.group() for m in pattern.finditer(text)]
        if kind == "a phone number":
            found = [f for f in found if sum(ch.isdigit() for ch in f) >= 10]
        if found:
            return f"personal data ({kind}): never kept in memory"
    return None
