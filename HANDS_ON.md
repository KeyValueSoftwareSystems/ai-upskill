# Hands-on: one LLM call

Branch `session-01-llm-call` · file `approach_llm/app.py` · about 3 minutes

Paste each snippet over the matching function in `approach_llm/app.py`, then run:

```bash
uv run python -m launchkit.scoreboard --approach llm
```

## TODO 1: build the prompt

Solves: the model doesn't know Harbor's rules or the shape of answer we need.

```python
def build_prompt(text: str, brand: dict) -> list[dict]:
    """TODO 1: Build the messages for the model."""
    system = (
        "You write poster ad specs.\n"
        f"{brand_rules_text(brand)}\n"
        "Reply with ONLY a JSON object with the keys headline, subheadline, body and visual_concept. "
        "visual_concept describes the picture only and must never contain words to be drawn."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": text}]
```

## TODO 2: parse the reply

Solves: the model wraps JSON in prose and code fences, so the reply isn't usable as data.

```python
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
```

## TODO 3: validate, allow one repair

Solves: the model breaks word limits and uses banned claims; code checks every reply and asks for one fix.

```python
def get_valid_spec(messages: list[dict], brand: dict) -> PosterSpec:
    """TODO 3: Call the model, validate, allow ONE repair, else raise SpecError."""
    raw = complete(messages)
    try:
        spec = parse_spec(raw)
        problems = validate_spec(spec, brand)
    except SpecError as e:
        spec, problems = None, [str(e)]
    if not problems:
        return spec

    repair = messages + [
        {"role": "assistant", "content": raw},
        {"role": "user", "content": "Fix these problems and reply with only the corrected JSON:\n- " + "\n- ".join(problems)},
    ]
    raw = complete(repair)
    spec = parse_spec(raw)
    problems = validate_spec(spec, brand)
    if problems:
        raise SpecError("still invalid after one repair: " + "; ".join(problems))
    return spec
```

## TODO 4: picture only

Solves: image models misspell text, so the copy must never reach the image model. In `handle`, replace the `generate_image(...)` line with:

```python
    image = generate_image(spec.visual_concept, brand, conversation_id=conversation_id)
```

## Then

Run the scoreboard and read why R2, R3 and R4 fail. Try your own requests:

```bash
uv run python -m launchkit.ask --approach llm "Poster for the Tidal bottle on a beach"
```
