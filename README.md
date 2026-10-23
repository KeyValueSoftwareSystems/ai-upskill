# LaunchKit session opener

LaunchKit is the mini-Pencil we build in this upskill: a marketing assistant that turns one campaign concept into on-brand poster ads. Our first customer is **Harbor**, launching the Flask Trail 750 water bottle in its new **Tidal** colour.

## Maya's problem

Maya is Harbor's marketer. Tidal launches in six weeks and she needs about 40 posters: Insta posts, stories and web banners. Once she approves a picture it must stay the same in every size, the word "unbreakable" is banned, and the lid is hand-wash only. Her question: *why don't we just use ChatGPT?*

So we start where ChatGPT starts: one call to a model. Every approach we build is scored on Maya's four requests, sent one after another in one conversation:

| | Maya says | Needs |
| --- | --- | --- |
| R1 | Tidal launch, a misty lakeshore at dawn. Can I get a concept, a storyboard, the words and a poster? | a full poster from one idea |
| R2 | Love it. Just the story size now, please. | keep my picture: the story size of the approved poster |
| R3 | What does your brand book say about washing the lid? | an answer, not a new poster |
| R4 | Is the lid dishwasher-safe? If not, fix the copy, then give me the story size. | three asks in one message |

## The session

Each branch starts from the previous branch's solution, so you can always jump ahead if you fall behind.

| Branch | What you do | Scoreboard |
| --- | --- | --- |
| `session-01-llm-call` | One AI call, then a shape and four calls, in `approach_llm/app.py` | 1/4: R1 only |
| **`session-01-langgraph`** (you are here) | Draw the paths ahead of time, in `approach_graph/graph.py` (snippets on the hands-on sheet from your trainer) | 1/4 at the start, 3/4 when done |
| `session-01-harness` | Next segment: the agent harness | |

Fixing "just the story size" in plain code means one `if` per kind of request. LangGraph draws that map ahead of time: a router picks a path, and a saved state keeps the poster Maya approved.

```
START -> route --"poster"--> write -> picture -> END    (the four shaped calls, then the image model)
           |----"resize"--> resize -> END             (no model: the saved picture, resized by code)
           +----"answer"--> answer -> END             (TODO 3)
```

- **TODO 1**, a saved state: a checkpointer keeps the approved picture and words per conversation.
- **TODO 2**, the router: "Just the story size" goes to `resize` and keeps the picture. R2 passes: **2/4**.
- **TODO 3**, one more path: the lid question gets an answer, not a new poster. R3 passes: **3/4**.
- **R4 still fails, by design.** The router picks one path, so two of Maya's three asks vanish. How many paths for 10 kinds of request, and every mix of them?

```bash
uv run python -m launchkit.scoreboard --approach graph
```

## Setup

You need Python 3.12 or newer, [`uv`](https://docs.astral.sh/uv/), and a key for KeyValue's LiteLLM proxy (ask the trainer).

```bash
uv sync
cp .env.example .env      # then add your LITELLM_API_KEY
uv run python -m launchkit.check_setup
```

It should end with **Setup complete**. Anything marked FAIL comes with a fix printed under it. Add `--no-image` to skip the one paid image call. To skip paid image calls during the session, pass `--no-image` to `ask`, or set `LAUNCHKIT_IMAGES=placeholder` in `.env`.

## Try it in your browser

```bash
uv run python -m launchkit.ui     # opens http://localhost:8000
```

Click R1 to R4 in order, click **Send**, and see every model call, the poster, any answer, Harbor's rules checked and every image. Keep it running while you work: pick **LangGraph** under *Approach*; it picks up changes to `approach_graph/graph.py` on the next request (saving the file resets the saved state, so start again from R1). If port 8000 is busy, it tells you to add `--port 8001`; the address is then http://localhost:8001. It only accepts connections from your own machine.

## What's in the repo

```
approach_graph/graph.py       ← the file you edit on this branch
approach_llm/app.py           the four shaped calls, solved
workspaces/harbor/brand.json  Harbor's rules: voice, facts, banned claims, word limits, colours, sizes
launchkit/                    supplied code, worth a read but no need to change it
  llm.py                        complete(messages) -> text: one call to the model
  images.py                     generate_image (image model) and resize_image (plain code)
  poster.py                     Harbor's rules, the poster data, and the checks: plain code, no model
  ask.py                        uv run python -m launchkit.ask R1: try one request, see every call
  ui.py                         uv run python -m launchkit.ui: the same, in your browser
  scoreboard.py                 Maya's four requests and how each is checked
  check_setup.py                checks your setup before the session
```

Everything you make lands in `out/`.
