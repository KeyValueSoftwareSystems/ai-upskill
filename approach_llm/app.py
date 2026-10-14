"""One LLM call.

The whole approach is: build a prompt, call the model once, turn the reply
into a PosterSpec, then ask the image model for the picture.

Every function starts as the simplest version that runs. Replace them one TODO
at a time, and after each one run:
    uv run python -m launchkit.step llm
"""
import json
import re  # noqa: F401  (you'll need this for TODO 2)

from launchkit.brand import brand_rules_text, load_brand  # noqa: F401
from launchkit.images import generate_image
from launchkit.llm import complete
from launchkit.result import Result
from launchkit.spec import PosterSpec, SpecError, validate_spec  # noqa: F401


def build_prompt(text: str, brand: dict) -> list[dict]:
    """TODO 1: Build the messages for the model."""
    # TODO 1: add a system message with Harbor's rules and the JSON shape we need.
    # Right now the model only sees the request, so it knows neither.
    return [{"role": "user", "content": text}]


def parse_spec(raw: str) -> PosterSpec:
    """TODO 2: Turn the model's reply into a PosterSpec, or raise SpecError."""
    # TODO 2: find the JSON inside prose or ```json fences, and raise SpecError if there's none.
    # Right now one sentence around the JSON makes json.loads fail.
    return PosterSpec.from_dict(json.loads(raw))


def get_valid_spec(messages: list[dict], brand: dict) -> PosterSpec:
    """TODO 3: Call the model, validate, allow ONE repair, else raise SpecError."""
    # TODO 3: check the spec with validate_spec and ask the model for one repair.
    # Right now whatever comes back is trusted, even when it breaks Harbor's rules.
    raw = complete(messages)
    return parse_spec(raw)


def handle(text: str, *, workspace: str, conversation_id: str, attachments: list[str]) -> Result:
    """Entry point used by the scoreboard. A plain call has no memory and no images in."""
    brand = load_brand(workspace)
    try:
        spec = get_valid_spec(build_prompt(text, brand), brand)
    except SpecError as e:
        return Result(error=str(e))
    # TODO 4: send only spec.visual_concept. The image model can't spell, so it must never get the copy.
    image = generate_image(f"{spec.headline}. {spec.visual_concept}", brand, conversation_id=conversation_id)
    return Result(spec=spec, images=[image])
