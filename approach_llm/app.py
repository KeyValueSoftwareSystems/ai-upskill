"""One LLM call: turn a campaign concept into a Harbor poster.

    concept --> build_prompt --> model --> parse_spec --> image model --> every placement size

You fill in two TODOs (HANDS_ON.md has the code). After each one, try it:
    uv run python -m launchkit.ask R1
"""
from launchkit.images import generate_image, resize_image  # noqa: F401  (TODO 2)
from launchkit.llm import complete
from launchkit.poster import Result, SpecError, brand_rules_text, load_brand, parse_spec  # noqa: F401  (TODO 1)


def build_prompt(text: str, brand: dict) -> list[dict]:
    """TODO 1: tell the model Harbor's rules and the shape of answer we need."""
    return [{"role": "user", "content": text}]


def handle(text: str, *, workspace: str, conversation_id: str, attachments: list[str]) -> Result:
    """Make one poster from one request. Used by `ask` and the scoreboard."""
    brand = load_brand(workspace)
    reply = complete(build_prompt(text, brand))  # the one LLM call
    try:
        spec = parse_spec(reply)
    except SpecError as e:
        return Result(error=str(e))

    # The image model only gets the picture, never the copy. Words drawn into pixels can't be
    # edited, set in Harbor's font or cropped to other sizes; the copy is laid over the picture later.
    picture = generate_image(spec.visual_concept, brand, conversation_id=conversation_id)

    # TODO 2: also return the picture in every placement size (brand["placements"]).
    return Result(spec=spec, images=[picture])
