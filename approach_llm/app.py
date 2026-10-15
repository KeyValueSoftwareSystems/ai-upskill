"""One LLM call: turn a campaign concept into a Harbor poster.

    concept --> build_prompt --> model --> parse_spec --> image model --> every placement size

Solved: this is where the LLM-call session ends. The LangGraph pipeline in
approach_graph/graph.py starts from it.
    uv run python -m launchkit.ask --approach llm R1
"""
from launchkit.images import generate_image, resize_image
from launchkit.llm import complete
from launchkit.poster import Result, SpecError, brand_rules_text, load_brand, parse_spec


def build_prompt(text: str, brand: dict) -> list[dict]:
    """Solved TODO 1: tell the model Harbor's rules and the shape of answer we need."""
    system = (
        "You write poster ads.\n"
        f"{brand_rules_text(brand)}\n"
        "Reply with ONLY a JSON object with the keys headline, subheadline, body and visual_concept. "
        "visual_concept describes the picture only and never contains words to draw."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": text}]


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

    # Solved TODO 2: the picture in every placement size, by plain code.
    sizes = [resize_image(picture, tuple(size), conversation_id=conversation_id)
             for size in brand["placements"].values()]
    return Result(spec=spec, images=[picture] + sizes)
