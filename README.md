# LaunchKit session opener

LaunchKit is the mini-Pencil we build in this upskill: a marketing assistant that turns one campaign concept into on-brand poster ads. Our first customer is **Harbor**, launching the Flask Trail 750 water bottle in its new **Tidal** colour.

## The problem statement

> Given a campaign concept (text, a photo, or both) and a brand's workspace, LaunchKit must produce on-brand poster ads: copy that obeys the brand's rules, a picture with no words drawn into it, every placement size, and follow-up edits, reliably and for any brand.

Harbor has sent four requests, and every approach we build is scored on them:

| | Request | Tests |
| --- | --- | --- |
| R1 | Poster for the Tidal bottle on a misty lakeshore at dawn. Headline idea: cold for 24 hours. | a concept becomes an on-brand poster |
| R2 | Make the headline shorter. | follow-up edits |
| R3 | Use this photo of the bottle. Make the bottle bigger and the lake moodier. | a concept given as a photo |
| R4 | Now give me the story size (1080x1920) of that poster. | resizing the poster we just made |

## The session

1. **This branch, one LLM call** (`HANDS_ON.md`): how far does a single model call get us? Pretty far for R1, and nowhere for R2 to R4.
2. **`session-01-langgraph`**: we add the memory and steps around the model that R2 to R4 need.

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

Paste a request, click **Make poster**, and see the model call, the poster, Harbor's rules checked and every image. Keep it running while you work: it picks up changes to `approach_llm/app.py` on the next request. If port 8000 is busy, it tells you to add `--port 8001`; the address is then http://localhost:8001. It only accepts connections from your own machine.

## What's in the repo

```
approach_llm/app.py           ← the only file you edit
workspaces/harbor/brand.json  Harbor's rules: voice, facts, banned claims, word limits, colours, sizes
assets/tidal_photo.png        the photo for R3
launchkit/                    supplied code, worth a read but no need to change it
  llm.py                        complete(messages) -> text: the one LLM call
  images.py                     generate_image (image model) and resize_image (plain code)
  poster.py                     Harbor's rules, the poster data, and the checks: plain code, no model
  ask.py                        uv run python -m launchkit.ask R1: try one request, see every call
  ui.py                         uv run python -m launchkit.ui: the same, in your browser
  scoreboard.py                 Harbor's four requests and how each is checked
  check_setup.py                checks your setup before the session
```

Everything you make lands in `out/`.
