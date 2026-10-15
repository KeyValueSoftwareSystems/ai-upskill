# LaunchKit session opener

LaunchKit is the mini-Pencil we build in this upskill: a marketing assistant that turns one campaign concept into on-brand poster ads. Our first customer is **Harbor**, launching the Flask Trail 750 water bottle in its new **Tidal** colour.

In this opener you'll try the two approaches most teams start with, a plain LLM call and a LangGraph pipeline, and score both against the same four Harbor requests.

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

Each branch starts from the previous branch's solution, so you can always jump ahead if you fall behind.

| Branch | What you do | Scoreboard |
| --- | --- | --- |
| `session-01-llm-call` | One LLM call, in `approach_llm/app.py` | 1/4: R1 only |
| `session-01-langgraph` | A graph around that call, in `approach_graph/graph.py` (snippets on the hands-on sheet from your trainer) | 1/4 at the start, 4/4 when done |
| **`session-01-llm-langgraph-solution`** (you are here) | Nothing: both hands-ons are solved, for demos and for catching up | 1/4 for the LLM call, 4/4 for the graph |
| `session-01-harness` | Next segment: the agent harness | |

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

Pick **LangGraph** under *Approach*, paste a request, click **Make poster**, and see every model call, the poster, Harbor's rules checked and every image. Keep it running while you work: it picks up changes to `approach_graph/graph.py` on the next request, and it remembers each conversation, so R1 then R2 works as a follow-up. If port 8000 is busy, it tells you to add `--port 8001`; the address is then http://localhost:8001. It only accepts connections from your own machine.

## What's in the repo

```
approach_graph/graph.py       ← the file you edit on this branch
approach_llm/app.py           last session's LLM call, solved; the graph reuses its prompt
workspaces/harbor/brand.json  Harbor's rules: voice, facts, banned claims, word limits, colours, sizes
assets/tidal_photo.png        the photo for R3
launchkit/                    supplied code, worth a read but no need to change it
  llm.py                        complete(messages) -> text: one LLM call
  images.py                     generate_image (image model) and resize_image (plain code)
  poster.py                     Harbor's rules, the poster data, and the checks: plain code, no model
  ask.py                        uv run python -m launchkit.ask --approach graph R1: try one request, see every call
  ui.py                         uv run python -m launchkit.ui: the same, in your browser
  scoreboard.py                 Harbor's four requests and how each is checked
  check_setup.py                checks your setup before the session
```

Everything you make lands in `out/`.
