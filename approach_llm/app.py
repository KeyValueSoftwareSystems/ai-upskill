"""Give it a shape: Maya's brief, split into four calls with Harbor's rules and a fixed answer shape.

    brief --> concept --> storyboard --> words --> poster --> image model
              (each call sees the earlier ones, so the picture and the words carry on together)

Solved: both TODOs from the one-AI-call hands-on are filled in. Score it:
    uv run python -m launchkit.scoreboard --approach llm
"""
from launchkit.images import generate_image
from launchkit.llm import complete
from launchkit.poster import PosterSpec, Result, SpecError, brand_rules_text, load_brand, parse_json

# The job in four steps, and the fixed shape of each step's answer: key -> what goes in it.
STAGES = {
    "concept": {"concept": "the idea of the poster, in one sentence"},
    "storyboard": {"storyboard": "a list of exactly 3 short frames that tell the poster's story, first to last"},
    "words": {"headline": "the headline", "subheadline": "the subheadline", "body": "the body copy"},
    "poster": {"visual_concept": "the picture only, for the image model; never words to draw"},
}


def build_prompt(keys: dict, brand: dict) -> str:
    """Solved TODO 1: the system message: Harbor's rules, and the shape of answer we need."""
    shape = "\n".join(f"- {key}: {what}" for key, what in keys.items())
    return (f"You write poster ads.\n{brand_rules_text(brand)}\n"
            f"Reply with ONLY a JSON object with these keys, and nothing else:\n{shape}")


def write(text: str, brand: dict) -> PosterSpec:
    """The model's part: Maya's brief in, the filled-in form out."""
    # Solved TODO 2: one call per stage, each with its own shape. Earlier messages go with each call.
    messages, form = [{"role": "user", "content": text}], {}
    for stage, keys in STAGES.items():
        messages.append({"role": "user", "content": f"Now the {stage}."})
        reply = complete([{"role": "system", "content": build_prompt(keys, brand)}] + messages)
        form.update(parse_json(reply))
        messages.append({"role": "assistant", "content": reply})
    return PosterSpec.from_dict(form)


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
