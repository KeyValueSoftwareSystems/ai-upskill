import re
from pathlib import Path

import yaml

from launchkit.harness.request import WORKSPACE_ID, UnknownWorkspace

BOILERPLATE = re.compile(r"^You are .+'s poster copywriter\.$")


def workspace_root(workspace_id: str, settings) -> Path:
    root = settings.workspaces_dir / workspace_id
    if not WORKSPACE_ID.fullmatch(workspace_id) or not root.is_dir():
        raise UnknownWorkspace(workspace_id)
    return root


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(_text(path))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _rules(agents: str) -> list[str]:
    rules, in_rules = [], False
    for line in agents.splitlines():
        if line.startswith("## "):
            in_rules = line[3:].strip().lower() == "rules"
        elif in_rules and line.strip().startswith("- "):
            rules.append(line.strip()[2:])
    return rules


def _label(key: str) -> str:
    text = str(key).replace("_", " ").strip()
    return text[:1].upper() + text[1:]


def read_library(workspace_id: str, settings) -> dict:
    """A brand at a glance: what was drafted from its pack, as categories a person can read, plus the uploaded packs."""
    root = workspace_root(workspace_id, settings)
    users = _yaml(root / "users.yaml")
    rules = _yaml(root / "rules.yaml")
    brand = users.get("brand") or workspace_id

    assets = root / "assets"
    uploads = [
        {"name": p.name, "bytes": p.stat().st_size, "modified": p.stat().st_mtime}
        for p in sorted(assets.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if p.is_file()
    ] if assets.is_dir() else []

    colours = rules.get("colours") or {}
    details = [
        {"category": "Brand", "items": [{"text": brand}]},
        {"category": "Voice and tone", "items": [{"text": line} for line in _lines(_text(root / "SOUL.md")) if not BOILERPLATE.match(line)]},
        {"category": "Copy rules", "items": [{"text": rule} for rule in _rules(_text(root / "AGENTS.md"))]},
        {"category": "Words and claims to avoid", "items": [{"text": str(claim)} for claim in rules.get("banned_claims") or []]},
        {"category": "Colours", "items": [{"text": _label(name), "hex": str(hex_)} for name, hex_ in colours.items()] if isinstance(colours, dict) else []},
        {"category": "Product and company facts", "items": [{"text": line} for line in _lines(_text(root / "facts.md"))]},
        {"category": "People", "items": [
            {"text": f"{u.get('name', u.get('id'))} ({u['role']})" if u.get("role") else str(u.get("name", u.get("id")))}
            for u in users.get("users") or [] if isinstance(u, dict)
        ]},
    ]
    return {"workspace_id": workspace_id, "brand": brand, "uploads": uploads, "details": details}


def asset_path(workspace_id: str, name: str, settings) -> Path:
    path = workspace_root(workspace_id, settings) / "assets" / Path(name).name
    if not path.is_file():
        raise FileNotFoundError(name)
    return path
