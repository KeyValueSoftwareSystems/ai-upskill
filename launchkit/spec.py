"""The poster spec: the structured output every approach must produce."""
from dataclasses import asdict, dataclass

FIELDS = ("headline", "subheadline", "body", "visual_concept")


class SpecError(ValueError):
    """The model's output can't be turned into a valid poster spec."""


@dataclass
class PosterSpec:
    headline: str
    subheadline: str
    body: str
    visual_concept: str  # describes the picture only; never words to draw
    reference_image: str | None = None  # path of an uploaded photo, if used

    @classmethod
    def from_dict(cls, data: dict) -> "PosterSpec":
        if not isinstance(data, dict):
            raise SpecError("expected a JSON object")
        missing = [f for f in FIELDS if not isinstance(data.get(f), str) or not data.get(f).strip()]
        if missing:
            raise SpecError("missing or empty fields: " + ", ".join(missing))
        return cls(**{f: data[f].strip() for f in FIELDS}, reference_image=data.get("reference_image"))

    def to_dict(self) -> dict:
        return asdict(self)


def word_count(text: str) -> int:
    return len(text.split())


def validate_spec(spec: PosterSpec, brand: dict) -> list[str]:
    """Return a list of problems. An empty list means the spec is valid."""
    problems = []
    for field, limit in brand["copy_limits"].items():
        n = word_count(getattr(spec, field))
        if n > limit:
            problems.append(f"{field} has {n} words; the limit is {limit}")
    copy = " ".join([spec.headline, spec.subheadline, spec.body]).lower()
    for claim in brand["banned_claims"]:
        if claim.lower() in copy:
            problems.append(f'banned claim "{claim}"')
    if spec.headline.lower() in spec.visual_concept.lower():
        problems.append("visual_concept contains the headline; the image model must never draw the words")
    return problems
