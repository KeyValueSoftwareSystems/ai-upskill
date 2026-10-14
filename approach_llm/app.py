"""One LLM call.

The whole approach is: build a prompt, call the model once, turn the reply
into a PosterSpec, then ask the image model for the picture.

Work through the TODOs in order and rerun the scoreboard after each one:
    uv run python -m launchkit.scoreboard --approach llm
"""
import json  # noqa: F401  (you'll need these for TODO 2)
import re  # noqa: F401

from launchkit.brand import brand_rules_text, load_brand  # noqa: F401
from launchkit.images import generate_image
from launchkit.llm import complete
from launchkit.result import Result
from launchkit.spec import PosterSpec, SpecError, validate_spec  # noqa: F401


def build_prompt(text: str, brand: dict) -> list[dict]:
    """TODO 1: Build the messages for the model.

    Return [{"role": "system", ...}, {"role": "user", "content": text}].
    The system message should:
      - include the brand's rules (brand_rules_text(brand) gives you them as text)
      - ask for ONLY a JSON object with the keys headline, subheadline, body, visual_concept
      - say that visual_concept describes the picture only, never words to be drawn
    """
    raise NotImplementedError("TODO 1: build_prompt in approach_llm/app.py")


def parse_spec(raw: str) -> PosterSpec:
    """TODO 2: Turn the model's reply into a PosterSpec, or raise SpecError.

    Models often wrap JSON in prose or ```json fences. Find the JSON object,
    json.loads it, and build the spec with PosterSpec.from_dict(data).
    Raise SpecError with a clear message if there's no JSON or it's invalid.
    """
    raise NotImplementedError("TODO 2: parse_spec in approach_llm/app.py")


def get_valid_spec(messages: list[dict], brand: dict) -> PosterSpec:
    """TODO 3: Validate, allow ONE repair, otherwise raise SpecError.

    Right now this trusts whatever comes back. Replace it so that:
      1. problems = validate_spec(spec, brand) (and a SpecError from parsing counts as a problem)
      2. if there are problems, call the model ONCE more with the original messages, the model's
         reply as an "assistant" message, and a "user" message starting
         "Fix these problems and reply with only the corrected JSON:" followed by the problems
      3. if it's still invalid, raise SpecError("still invalid after one repair: ...")
    """
    raw = complete(messages)
    return parse_spec(raw)


def handle(text: str, *, workspace: str, conversation_id: str, attachments: list[str]) -> Result:
    """Entry point used by the scoreboard. A plain call has no memory and no images in."""
    brand = load_brand(workspace)
    try:
        spec = get_valid_spec(build_prompt(text, brand), brand)
    except SpecError as e:
        return Result(error=str(e))
    # TODO 4: The image model can't spell, so it must never receive the copy.
    # Change this call to send only spec.visual_concept.
    image = generate_image(f"{spec.headline}. {spec.visual_concept}", brand, conversation_id=conversation_id)
    return Result(spec=spec, images=[image])
