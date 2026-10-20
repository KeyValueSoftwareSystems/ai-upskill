import re
import shutil
from pathlib import Path

import yaml
from agno.agent import Agent
from pydantic import BaseModel, Field
from pypdf import PdfReader

from launchkit.adapters.models import model_name, resolve_model
from launchkit.harness.context import approx_tokens
from launchkit.harness.request import WORKSPACE_ID, UnknownWorkspace
from launchkit.harness.store import index_brand
from launchkit.harness.trace import Trace
from launchkit.settings import settings as default_settings


class Colour(BaseModel):
    name: str = Field(description="The colour's name as the brand calls it, for example navy.")
    hex: str = Field(description="Six-digit hex with a leading #, for example #0f2f4a. Make a sensible guess if the pack gives none.")


class BrandProfile(BaseModel):
    brand_name: str
    voice: list[str] = Field(description="Two or three short lines on how the brand sounds, written to the copywriter: 'You are ...'. Plain words.")
    rules: list[str] = Field(description="Operating rules for poster copy, one per line, besides word limits and banned claims.")
    banned_claims: list[str] = Field(description="Words or claims the copy must never make. Lower case, short.")
    colours: list[Colour] = Field(description="The brand's main colours, primary first. At most four.")
    facts: list[str] = Field(description="Product and company facts, one short sentence each, exactly as the pack states them.")


ONBOARD_TASK = """You read a brand pack and fill a BrandProfile form for a poster copywriting agent.
Take every value from the pack. Do not invent claims or facts. Keep each line short."""


def extract_text(pdf_path: Path) -> tuple[str, int]:
    reader = PdfReader(str(pdf_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages).strip(), len(pages)


def restates_a_fixed_rule(rule: str) -> bool:
    text = rule.lower()
    limits = "words" in text and any(part in text for part in ("headline", "subheadline", "body"))
    no_words = "contains words" in text or "no words" in text or "without words" in text
    return limits or no_words


def render_files(profile: BrandProfile, brand_text: str) -> dict[str, str]:
    colours = ", ".join(c.name for c in profile.colours) or "the brand colours"
    banned = ", ".join(f'"{claim}"' for claim in profile.banned_claims) or "nothing in particular"
    soul = f"You are {profile.brand_name}'s poster copywriter.\n" + "\n".join(profile.voice) + "\n"
    agents = (
        "## Rules\n"
        "- Headline up to 6 words. Subheadline up to 12. Body up to 25.\n"
        f"- Use the colours {colours} when you describe the picture.\n"
        f"- Never claim {banned}.\n"
        + "".join(f"- {rule}\n" for rule in profile.rules if not restates_a_fixed_rule(rule))
        + "- The picture never contains words. Copy goes in the spec, not the image prompt.\n\n"
        "## Memory\n- If the marketer corrects you, follow the correction for the rest of the conversation.\n"
    )
    rules = yaml.safe_dump(
        {
            "banned_claims": [c.lower() for c in profile.banned_claims],
            "colours": {c.name: c.hex if c.hex.startswith("#") else f"#{c.hex}" for c in profile.colours},
        },
        sort_keys=False,
        allow_unicode=True,
    )
    facts = "\n".join(profile.facts) + "\n"
    users = yaml.safe_dump({"brand": profile.brand_name, "users": [{"id": "owner", "name": "Owner", "role": "owner"}]}, sort_keys=False, allow_unicode=True)
    return {
        "SOUL.md": soul,
        "AGENTS.md": agents,
        "rules.yaml": rules,
        "facts.md": facts,
        "brand-book.md": brand_text + "\n",
        "users.yaml": users,
    }


def slug(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return cleaned[:32].strip("-") or "brand"


def brand_of(root: Path) -> str | None:
    users = root / "users.yaml"
    if not users.is_file():
        return None
    try:
        data = yaml.safe_load(users.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None
    return str(data["brand"]) if isinstance(data, dict) and data.get("brand") else None


def workspace_of_brand(brand_name: str, settings) -> str | None:
    """The folder a brand already has, found by the brand line in its users.yaml, whatever the folder is called."""
    wanted = slug(brand_name)
    for folder in sorted(p for p in settings.workspaces_dir.iterdir() if p.is_dir()):
        current = brand_of(folder)
        if current and slug(current) == wanted:
            return folder.name
    return None


def onboard_workspace(pdf_path: Path, *, workspace_id: str | None = None, settings=default_settings, model=None, trace: Trace | None = None) -> list[Path]:
    trace = trace if trace is not None else Trace()
    pdf_path = Path(pdf_path)
    if workspace_id is not None and not WORKSPACE_ID.fullmatch(workspace_id):
        raise UnknownWorkspace(workspace_id)

    text, pages = extract_text(pdf_path)
    if not text:
        raise ValueError(f"{pdf_path.name} has no text to read. A scanned PDF needs OCR first.")
    trace.note(f"read {pages} page{'s' if pages != 1 else ''} of {pdf_path.name}, about {approx_tokens(text)} tokens of text")

    model = model if model is not None else resolve_model(settings, trace)
    agent = Agent(model=model, system_message=ONBOARD_TASK, output_schema=BrandProfile, retries=2, telemetry=False)
    run = agent.run(text)
    trace.model("onboard", model_name(model), run.metrics)
    profile = run.content if isinstance(run.content, BrandProfile) else BrandProfile.model_validate_json(str(run.content))

    if workspace_id is None:
        found = workspace_of_brand(profile.brand_name, settings)
        if found and found != slug(profile.brand_name):
            trace.note(f"brand '{profile.brand_name}' already has workspace '{found}'")
        workspace_id = found or slug(profile.brand_name)
    root = settings.workspaces_dir / workspace_id
    if root.is_dir():
        trace.note(f"brand '{profile.brand_name}' replaces the drafted files of workspace '{workspace_id}'")
    else:
        trace.note(f"brand '{profile.brand_name}' gets the new workspace '{workspace_id}'")
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for old in assets.glob("*.pdf"):
        if old.name != pdf_path.name:
            old.unlink()
            trace.note(f"removed the older pack {old.name}")
    stored = assets / pdf_path.name
    shutil.copyfile(pdf_path, stored)
    trace.file(stored)

    written = []
    for name, body in render_files(profile, text).items():
        path = root / name
        if name == "users.yaml" and path.exists():
            continue
        path.write_text(body, encoding="utf-8")
        trace.written(path)
        written.append(path)
    index_brand(workspace_id, settings, trace)
    return written
