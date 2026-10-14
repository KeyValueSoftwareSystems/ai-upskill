"""One LLM call.

The whole approach is: build a prompt, call the model once, turn the reply
into a PosterSpec, then ask the image model for the picture.
"""
import json
import re

from launchkit.brand import brand_rules_text, load_brand
from launchkit.images import generate_image
from launchkit.llm import complete
from launchkit.result import Result
from launchkit.spec import PosterSpec, SpecError, validate_spec


def build_prompt(text: str, brand: dict) -> list[dict]:
    """TODO 1: Build the messages for the model."""
    system = (
        "You write poster ad specs.\n"
        f"{brand_rules_text(brand)}\n"
        "Reply with ONLY a JSON object with the keys headline, subheadline, body and visual_concept. "
        "visual_concept describes the picture only and must never contain words to be drawn."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": text}]


def parse_spec(raw: str) -> PosterSpec:
    """TODO 2: Turn the model's reply into a PosterSpec, or raise SpecError."""
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise SpecError("no JSON object in the model's reply")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise SpecError(f"invalid JSON: {e}") from e
    return PosterSpec.from_dict(data)


def get_valid_spec(messages: list[dict], brand: dict) -> PosterSpec:
    """TODO 3: Call the model, validate, allow ONE repair, else raise SpecError."""
    print("[llm] calling model for spec…", flush=True)
    raw = complete(messages)
    print(f"[llm] got reply ({len(raw)} chars), parsing/validating…", flush=True)
    try:
        spec = parse_spec(raw)
        problems = validate_spec(spec, brand)
    except SpecError as e:
        spec, problems = None, [str(e)]
    if not problems:
        print("[llm] spec valid", flush=True)
        return spec

    print(f"[llm] invalid ({len(problems)} problem(s)), requesting one repair…", flush=True)
    repair = messages + [
        {"role": "assistant", "content": raw},
        {"role": "user", "content": "Fix these problems and reply with only the corrected JSON:\n- " + "\n- ".join(problems)},
    ]
    raw = complete(repair)
    print(f"[llm] got repair reply ({len(raw)} chars), re-validating…", flush=True)
    spec = parse_spec(raw)
    problems = validate_spec(spec, brand)
    if problems:
        raise SpecError("still invalid after one repair: " + "; ".join(problems))
    print("[llm] repair succeeded", flush=True)
    return spec


def handle(text: str, *, workspace: str, conversation_id: str, attachments: list[str]) -> Result:
    """Entry point used by the scoreboard. A plain call has no memory and no images in."""
    print(f"[llm] handle start conv={conversation_id!r} text={text[:60]!r}…", flush=True)
    brand = load_brand(workspace)
    print(f"[llm] loaded brand {brand.get('name', workspace)!r}", flush=True)
    try:
        spec = get_valid_spec(build_prompt(text, brand), brand)
    except SpecError as e:
        print(f"[llm] SpecError: {e}", flush=True)
        return Result(error=str(e))
    # TODO 4: picture-only image. Send the visual concept, never the copy.
    print("[llm] generating image…", flush=True)
    image = generate_image(spec.visual_concept, brand, conversation_id=conversation_id)
    print(f"[llm] done → {image}", flush=True)
    return Result(spec=spec, images=[image])
