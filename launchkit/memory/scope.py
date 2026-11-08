"""Ticket 3: a brand fact is never a memory about a person. Plain code, no model: a row that names any brand's colour,
size or never-say phrase, or a subject in the brand facts table, belongs to a brand. It is never loaded as a person's
memory, and a new note like it is refused before anyone is asked. Brand facts go in through propose_brand_fact."""

import re
from functools import lru_cache
from pathlib import Path

import yaml

FACT_SUBJECTS = ("warranty",)  # subjects the brand_facts table owns


@lru_cache(maxsize=8)
def _brand_words(workspaces_dir: Path) -> tuple[str, ...]:
    words = set(FACT_SUBJECTS)
    for rules_file in sorted(workspaces_dir.glob("*/rules.yaml")):
        rules = yaml.safe_load(rules_file.read_text(encoding="utf-8")) or {}
        words |= {claim.lower() for claim in rules.get("banned_claims", [])}
        for name, hex_code in rules.get("colours", {}).items():
            words |= {name.replace("_", " ").lower(), str(hex_code).lower()}
        words |= {size.lower() for group in rules.get("placements", {}).values() for size in group}
    return tuple(sorted(words))


def held_back(text: str, settings) -> str | None:
    """Why this row is not a memory about the person, or None when it is one."""
    for word in _brand_words(settings.workspaces_dir):
        if re.search(rf"(?<![\w#]){re.escape(word)}(?!\w)", text.lower()):
            return f'a brand fact ("{word}"): it belongs to the brand, not the person'
    return None
