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

1. **This branch, one AI call** (snippets on the hands-on sheet from your trainer). Harbor's rules are in the prompt, but what comes back is a chat reply, not a form. TODO 1 gives the answer a fixed shape. TODO 2 splits the job into four calls: concept, storyboard, words, poster. R1 passes. R2 to R4 fail: the code runs every step every time, so "just the story size" draws a new picture.
   ```bash
   uv run python -m launchkit.scoreboard --approach llm     # 0/4 as you get it, 1/4 after the TODOs
   ```
2. **`session-01-langgraph`**: we draw the paths ahead of time (a router, and a saved state) and see how far that goes.

## Setup

You need Python 3.12 or newer, [`uv`](https://docs.astral.sh/uv/), and a key for KeyValue's LiteLLM proxy (ask the trainer).

```bash
uv sync
cp .env.example .env      # then add your LITELLM_API_KEY
uv run python -m launchkit.check_setup
```

It should end with **Setup complete**. Anything marked FAIL comes with a fix printed under it. Pictures come from our GPU (`LAUNCHKIT_IMAGE_PROVIDER=gpu` in `.env`); set it to `litellm` only when the trainer says the GPU is down. To skip pictures, pass `--no-image` to `ask`, or set `LAUNCHKIT_IMAGE_PROVIDER=placeholder` in `.env`.

## Try it in your browser

```bash
uv run python -m launchkit.ui     # opens http://localhost:8000
```

Click R1 to R4 in order, click **Send**, and see every model call, the poster, any answer, Harbor's rules checked and every image. Keep it running while you work: it picks up changes to `approach_llm/app.py` on the next request. If port 8000 is busy, it tells you to add `--port 8001`; the address is then http://localhost:8001. It only accepts connections from your own machine.

## What's in the repo

```
approach_llm/app.py           ← the only file you edit
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
