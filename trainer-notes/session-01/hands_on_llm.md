# Hands-on: one AI call

Branch `session-01-llm-call` · you edit one file, `approach_llm/app.py` · **3 minutes in the session**; the rest is for afterwards

Before the session, add `LAUNCHKIT_IMAGES=placeholder` to `.env`. A real image takes about a minute, which the hands-on can't spare; the trainer shows real ones.

Maya, Harbor's marketer, asked: *why don't we just use ChatGPT?* So we start where ChatGPT starts: one call to a model, with Harbor's rules in the prompt. Run it first:

```bash
uv run python -m launchkit.scoreboard --approach llm
```

**0/4.** R1 says `not a form: no JSON object in the model's reply`. Run `uv run python -m launchkit.ask R1` to see why: the reply is a chat answer. It makes up a tagline and ends with a question. People can read it; code can't use it.

## In the session (3 minutes)

**TODO 1: give the answer a shape.** Can't a better prompt fix this? Yes. Paste over `build_prompt`:

```python
def build_prompt(keys: dict, brand: dict) -> str:
    """The system message: Harbor's rules, and the shape of answer we need."""
    shape = "\n".join(f"- {key}: {what}" for key, what in keys.items())
    return (f"You write poster ads.\n{brand_rules_text(brand)}\n"
            f"Reply with ONLY a JSON object with these keys, and nothing else:\n{shape}")
```

Scoreboard: **1/4.** The one call now fills in the whole form: concept, storyboard, words and a picture description.

**TODO 2: split the job into four calls.** One call does everything at once. Split it into concept, storyboard, words and poster, each with Harbor's rules and its own fixed shape. Earlier messages go with each call, so the picture and the words carry on together. Paste over `write`:

```python
def write(text: str, brand: dict) -> PosterSpec:
    """The model's part: Maya's brief in, the filled-in form out."""
    messages, form = [{"role": "user", "content": text}], {}
    for stage, keys in STAGES.items():
        messages.append({"role": "user", "content": f"Now the {stage}."})
        reply = complete([{"role": "system", "content": build_prompt(keys, brand)}] + messages)
        form.update(parse_json(reply))
        messages.append({"role": "assistant", "content": reply})  # the next call sees this one
    return PosterSpec.from_dict(form)
```

Scoreboard: **still 1/4**, but `ask R1` now shows four short calls. Maya gets four pieces: the concept (something like "A serene, misty lakeshore at dawn"), three storyboard frames, the words (such as "Cold for 24 Hours") and the poster.

**Read the reasons under R2 to R4:**

| Maya says | Why it fails |
| --- | --- |
| R2 "Love it. Just the story size now, please." | **It drew a new one.** The code runs every step every time, so a new bottle on new rocks comes back. She loses the poster she approved and pays for a picture she never asked for. |
| R3 "What does your brand book say about washing the lid?" | She asked a question and got a new poster. |
| R4 "Is the lid dishwasher-safe? If not, fix the copy, then give me the story size." | Three asks in one message; the code knows one way to answer. |

**The model does the creative part well once the answer has a shape. What runs, and what is kept, is up to the code around it.**

## After the session

**One `if` per request?** Fixing R2 in code means one `if` per kind of request: "just the story size" → resize only; "make the headline shorter" → words only; "use our own photo" → skip the picture; "show me three options" → three pictures; "go back to the first one" → reload the old poster. And "story size, and a shorter headline"? That message has no rule at all. Try writing the R2 `if` in `handle`. You can't: nothing remembers the picture Maya approved.

**Are the answers the same each run?** No. Run `ask R1` three times and compare the headlines. Step 7 of the session shows how we trust it anyway: check it in code, and keep a trace.

**Can't we put the rules in the context?** We do. `ask R1` shows Harbor's rules in every system message, and with a short prompt the model follows them well. Prefer a browser? `uv run python -m launchkit.ui` opens http://localhost:8000 and shows the same.

| Maya needs | One AI call | What it took |
| --- | --- | --- |
| a full poster from one idea | yes | a fixed answer shape (TODO 1), four steps (TODO 2) |
| keep my picture | no | memory of what she approved: next |
| an answer, not a new poster | no | a different path for a different kind of request: next |

Next: `git checkout session-01-langgraph`
