"""One AI call: Maya's brief goes to the model, with Harbor's rules in the prompt.

    brief --> write: one call, rules in the prompt --> parse_spec --> image model --> poster

What comes back is a chat reply, not a form. You fill in two TODOs (the hands-on sheet has
the code). After each one, try it:
    uv run python -m launchkit.ask R1
"""
from launchkit.images import generate_image
from launchkit.llm import complete
from launchkit.poster import PosterSpec, Result, SpecError, brand_rules_text, load_brand, parse_json, parse_spec  # noqa: F401  (TODO 2)

# The job in four steps, and the fixed shape of each step's answer: key -> what goes in it.
STAGES = {
    "concept": {"concept": "the idea of the poster, in one sentence"},
    "storyboard": {"storyboard": "a list of exactly 3 short frames that tell the poster's story, first to last"},
    "words": {"headline": "the headline", "subheadline": "the subheadline", "body": "the body copy"},
    "poster": {"visual_concept": "the picture only, for the image model; never words to draw"},
}
ALL_KEYS = {key: what for keys in STAGES.values() for key, what in keys.items()}


def build_prompt(keys: dict, brand: dict) -> str:
    """The system message: Harbor's rules. TODO 1: add the shape of answer we need, from `keys`."""
    return f"You write poster ads.\n{brand_rules_text(brand)}"


def write(text: str, brand: dict) -> PosterSpec:
    """The model's part: Maya's brief in, the filled-in form out."""
    # TODO 2: split the job into four calls, one per stage in STAGES, each with its own shape.
    reply = complete([{"role": "system", "content": build_prompt(ALL_KEYS, brand)},
                      {"role": "user", "content": text}])  # the one AI call
    return parse_spec(reply)


def handle(text: str, *, workspace: str, conversation_id: str) -> Result:
    """Make a poster from one request. Used by `ask`, the UI and the scoreboard."""
    brand = load_brand(workspace)
    try:
        spec = write(text, brand)
    except SpecError as e:
        return Result(error=f"not a form: {e}")

    # The image model only gets the picture, never the words. Words drawn into pixels can't be
    # edited, set in Harbor's font or cropped to other sizes; the copy is laid over the picture later.
    picture = generate_image(spec.visual_concept, brand, conversation_id=conversation_id)
    return Result(spec=spec, images=[picture])
