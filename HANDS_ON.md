# Hands-on: one LLM call

Branch `session-01-llm-call` · file `approach_llm/app.py` · about 10 minutes

Every function in `approach_llm/app.py` starts as the simplest version that runs. You replace them one TODO at a time, and after each one you run the step runner. It works out which TODOs you've done, sends a live request through your code, shows what came back, checks it, and names the limitation the next TODO fixes.

```bash
uv run python -m launchkit.step llm              # run the step you're on
uv run python -m launchkit.step llm --no-image   # same, without the paid image call
```

## Step 0: before you change anything

Run `uv run python -m launchkit.step llm`.

Look for: what the model writes when it has no rules or format to follow, and what `parse_spec` does with it.

Limitation: the model doesn't know Harbor's rules or the shape of answer we need.

## TODO 1: build the prompt

Solves: the model doesn't know Harbor's rules or the shape of answer we need.

Paste over `build_prompt`:

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

Run `uv run python -m launchkit.step llm`.

Look for: the system message carrying Harbor's rules and the reply it gets. Then a reply from another run, wrapped in prose and a ```` ```json ```` fence, and what `parse_spec` does with it.

Limitation: the reply is text, not data; one stray sentence breaks it.

## TODO 2: parse the reply

Solves: the model wraps JSON in prose and code fences, so the reply isn't usable as data.

Paste over `parse_spec`:

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

Run `uv run python -m launchkit.step llm`.

Look for: a request that asks for banned claims, a reply your `parse_spec` reads, and the problems `validate_spec` finds in it. Nothing in your code stops them yet.

Limitation: we can read the reply, but nothing stops it breaking the rules.

## TODO 3: validate, allow one repair

Solves: the model breaks word limits and uses banned claims; code checks every reply and asks for one fix.

Paste over `get_valid_spec`:

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

Run `uv run python -m launchkit.step llm`.

Look for: attempt 1 and its problems, the repair message your code sent, and attempt 2. Then the prompt sent to the image model, with the headline marked `>>> <<<` inside it.

Limitation: the copy is baked into the picture, so it can't be edited, resized or set in Harbor's font, and spelling isn't guaranteed.

## TODO 4: picture only

Solves: image models misspell text, so the copy must never reach the image model.

In `handle`, replace the `generate_image(...)` line with:

```python
    image = generate_image(spec.visual_concept, brand, conversation_id=conversation_id)
```

Run `uv run python -m launchkit.step llm`.

Look for: an image prompt with no headline in it. Then "Make the headline shorter." in the same conversation, and the headline that comes back next to the first one.

Limitation: a single call has no memory. The follow-up starts from nothing, so it can't edit the poster we just made.

## Final check: the scoreboard

```bash
uv run python -m launchkit.scoreboard --approach llm
```

Expect R1 to pass and R2 to R4 to fail. Read why each one fails: those are the problems the next approach has to solve. Try your own requests too:

```bash
uv run python -m launchkit.ask --approach llm "Poster for the Tidal bottle on a beach"
```

Next: `git checkout session-01-langgraph`
