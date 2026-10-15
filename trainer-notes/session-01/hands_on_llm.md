# Hands-on: how far does one LLM call get us?

Branch `session-01-llm-call` · you edit one file, `approach_llm/app.py` · **3 minutes in the session**; the rest is for afterwards

Before the session, add `LAUNCHKIT_IMAGES=placeholder` to `.env`. A real image takes about a minute, which the hands-on can't spare; the trainer shows real ones.

## In the session (3 minutes)

**1. Tell the model Harbor's rules and the answer we need** ("copy that obeys the brand's rules"). Paste over `build_prompt`:

```python
def build_prompt(text: str, brand: dict) -> list[dict]:
    """TODO 1: tell the model Harbor's rules and the shape of answer we need."""
    system = (
        "You write poster ads.\n"
        f"{brand_rules_text(brand)}\n"
        "Reply with ONLY a JSON object with the keys headline, subheadline, body and visual_concept. "
        "visual_concept describes the picture only and never contains words to draw."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": text}]
```

**2. Make every placement size with code** ("every placement size"). The model can't make five sizes; plain code can, and it's safe because the picture has no words a crop could cut off. Under the `# TODO 2` comment in `handle`, replace the `return` line with:

```python
    sizes = [resize_image(picture, tuple(size), conversation_id=conversation_id)
             for size in brand["placements"].values()]
    return Result(spec=spec, images=[picture] + sizes)
```

**3. Score it on Harbor's four requests:**

```bash
uv run python -m launchkit.scoreboard --approach llm
```

**Expect R1 to pass and R2 to R4 to fail.** Read the reason under each one:

| Request | Needs | Why one call fails |
| --- | --- | --- |
| R2 "Make the headline shorter." | follow-up edits | the call never sees the first poster, so there's nothing to edit |
| R3 "Use this photo of the bottle…" | a concept given as a photo | `handle` gets the photo but has no step that passes it on |
| R4 "…story size of that poster." | resizing the poster we just made | the call doesn't remember which poster "that poster" is, so it makes a new one |

**The LLM is good at the creative part. Everything that must be exact, checked or remembered needs something around it.**

## After the session

**See the model call.** `uv run python -m launchkit.ask R1` prints what was sent to the model and what came back. Before TODO 1, the model writes a decent poster idea as prose, so code can't use it (`no JSON object in the model's reply`); in our dry run it also invented a tagline, "Stay Fresh. Stay Tidal.". After TODO 1, the system message carries Harbor's rules and the reply is JSON. Prefer a browser? `uv run python -m launchkit.ui` opens http://localhost:8000 and shows the same.

**Is it reliable?** Try a brief Harbor's marketing team could easily send:

```bash
uv run python -m launchkit.ask "Summer festival poster: the Tidal bottle survives being dropped on concrete and keeps water ice cold all day."
```

The rules check says ✓, yet in our dry run 4 of 5 posters said something like "Ready for any drop". Harbor's `facts` in `brand.json` say nothing about drops, and Harbor bans "unbreakable": the model made the same claim in other words. It followed every written rule in all 51 dry-run posters; the problem is the rules nobody wrote down. Would a longer banned-word list catch it? Could a second model call check the claims, and what checks that one?

**Ask the model for every size.** `uv run python -m launchkit.ask "Poster for the Tidal bottle on a misty lakeshore at dawn, in every placement size"` (before TODO 2) gives one 1024x1024 image: the chat model only writes text, and the image model only makes a few fixed sizes.

**Stretch.** Make R2 pass by changing only `build_prompt`. You can't: the first poster isn't anywhere the call can see it. "For any brand": copy `workspaces/harbor/` to `workspaces/yourbrand/`, change the rules, and run `uv run python -m launchkit.ask --workspace yourbrand "..."`.

| The problem statement asks for | One LLM call? | What it took |
| --- | --- | --- |
| copy that obeys the brand's rules | yes, for rules written down | a good prompt (TODO 1) |
| …reliably | no | it slips past rules we can't write down; nothing catches it |
| a picture with no words | yes | send the image model the picture only |
| every placement size | no | plain code: resize (TODO 2) |
| follow-up edits, a photo | no | memory and steps around the model: next session |

Next: `git checkout session-01-langgraph`
