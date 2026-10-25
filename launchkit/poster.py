"""The plain-code side of a poster: the brand's rules, the poster data, and the checks.

Nothing here calls a model. The models are in llm.py (text) and images.py (pictures).
"""
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the repo folder
OUT = ROOT / "out"                          # everything we make goes here
FIELDS = ("concept", "storyboard", "headline", "subheadline", "body", "visual_concept")
FRAMES = 3  # storyboard frames


# ---- the brand

def load_brand(workspace: str) -> dict:
    """A brand's rules, from workspaces/<workspace>/brand.json."""
    return json.loads((ROOT / "workspaces" / workspace / "brand.json").read_text())


def brand_rules_text(brand: dict) -> str:
    """Brand rules as plain text you can drop into a prompt."""
    limits = brand["copy_limits"]
    return "\n".join([
        f"Brand: {brand['name']}. Product: {brand['product']}.",
        f"Voice: {brand['voice']}",
        "Facts you may use: " + "; ".join(brand["facts"]) + ".",
        "Never use these claims: " + ", ".join(brand["banned_claims"]) + ".",
        f"Headline: at most {limits['headline']} words. "
        f"Subheadline: at most {limits['subheadline']} words. "
        f"Body: at most {limits['body']} words.",
    ])


# ---- the poster

class SpecError(ValueError):
    """The model's reply can't be turned into a poster spec."""


@dataclass
class PosterSpec:
    """The whole form: the idea, its storyboard, the words on the poster, and a description of its picture."""
    concept: str          # the idea, in one sentence
    storyboard: list[str]  # the story in frames, first to last
    headline: str
    subheadline: str
    body: str
    visual_concept: str   # describes the picture only; never words to draw

    @classmethod
    def from_dict(cls, data: dict) -> "PosterSpec":
        if not isinstance(data, dict):
            raise SpecError("expected a JSON object")
        text = [f for f in FIELDS if f != "storyboard"]
        missing = [f for f in text if not isinstance(data.get(f), str) or not data.get(f).strip()]
        frames = data.get("storyboard")
        if not isinstance(frames, list) or not frames or not all(isinstance(x, str) and x.strip() for x in frames):
            missing.append("storyboard")
        if missing:
            raise SpecError("missing or empty fields: " + ", ".join(missing))
        return cls(storyboard=[x.strip() for x in frames], **{f: data[f].strip() for f in text})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Picture:
    """An image file, and how it was made."""
    path: str
    size: tuple[int, int]
    prompt: str | None = None        # what the image model was asked for
    reference: str | None = None     # the uploaded photo it started from, if any
    resized_from: str | None = None  # set when code resized another picture instead
    placeholder: bool = False        # drawn by code instead of the image model (no paid call)
    source: str | None = None        # who drew it: our GPU, the backup image model, or code (placeholder)


@dataclass
class Result:
    """What an approach returns for one request."""
    spec: PosterSpec | None = None
    images: list[Picture] = field(default_factory=list)
    answer: str | None = None  # a reply in words, when the request was a question
    error: str | None = None


def parse_json(raw: str) -> dict:
    """The model replies with text. Find the JSON object in it (even inside prose or ```json fences)."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise SpecError("no JSON object in the model's reply")
    try:
        data = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        raise SpecError(f"invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise SpecError("expected a JSON object")
    return data


def parse_spec(raw: str) -> PosterSpec:
    """A whole poster spec from one reply."""
    return PosterSpec.from_dict(parse_json(raw))


# ---- the checks

def word_count(text: str) -> int:
    return len(text.split())


def validate_spec(spec: PosterSpec, brand: dict) -> list[str]:
    """Check a spec against the brand's written rules. An empty list means it follows them all."""
    problems = []
    if len(spec.storyboard) != FRAMES:
        problems.append(f"storyboard has {len(spec.storyboard)} frames; it needs {FRAMES}")
    for name, limit in brand["copy_limits"].items():
        n = word_count(getattr(spec, name))
        if n > limit:
            problems.append(f"{name} has {n} words; the limit is {limit}")
    copy = " ".join([spec.headline, spec.subheadline, spec.body]).lower()
    for claim in brand["banned_claims"]:
        if claim.lower() in copy:
            problems.append(f'banned claim "{claim}"')
    # Naming the product ("a Tidal Flask on a rock") is fine; asking for text to be drawn is not.
    if re.search(r'["“”]|\b(headline|caption|slogan|tagline|lettering)\b', spec.visual_concept, re.I):
        problems.append("visual_concept asks for words in the picture; the image model must never draw text")
    return problems
