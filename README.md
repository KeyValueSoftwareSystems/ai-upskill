# LaunchKit session opener

LaunchKit is the mini-Pencil we build in this upskill: a marketing assistant platform that turns one campaign concept into on-brand poster ads. Our first customer is **Harbor**, launching the Flask Trail 750 in its new **Tidal** colourway.

In this opener you'll try the two approaches most teams start with, a plain LLM call and a LangGraph pipeline, and score both against the same four Harbor requests.

## The problem statement

> Given a campaign concept (text, a photo, or both) and a brand's workspace, LaunchKit must produce on-brand poster ads: copy that obeys the brand's rules, a picture with no words drawn into it, every placement size, and follow-up edits, reliably and for any brand.

## Definition of done: four Harbor requests

| ID | Request | Passes when |
|---|---|---|
| R1 | "Poster for the Tidal bottle on a misty lakeshore at dawn. Headline idea: cold for 24 hours." | Valid copy (word limits, no banned claims) and an image prompt with no copy in it |
| R2 | "Make the headline shorter." (same conversation as R1) | The headline is shorter and the concept is kept |
| R3 | "Use this photo of the bottle…" with `assets/tidal_photo.png` | The poster is built from the uploaded photo |
| R4 | "Now give me the story size (1080x1920) of that poster." (same conversation as R3) | The existing poster is resized, not regenerated |

Harbor's rules live in `workspaces/harbor/brand.json`.

## Setup

You need Python 3.12 or newer, [`uv`](https://docs.astral.sh/uv/), git with access to the KeyValue repo, the coding agent you already use, and an OpenAI key from KeyValue.

```bash
uv sync
cp .env.example .env      # then add your OPENAI_API_KEY
```

Images use `gpt-image-1` by default. To skip paid image calls, set `LAUNCHKIT_IMAGES=placeholder` in `.env`.

## Branches

Each branch contains the previous branch's solution, so you can always start from the next branch if you fall behind.

| Branch | What you do | Starts with |
|---|---|---|
| `session-01-llm-call` | Fill in the TODOs in `approach_llm/app.py` | The shared code |
| `session-01-langgraph` | Fill in the TODOs in `approach_graph/graph.py` | The LLM-call TODOs already solved |
| `session-01-harness` | Next segment: the agent harness | The LangGraph TODOs already solved |

Each branch has a `HANDS_ON.md` with the code to paste for every TODO.

## Commands

```bash
uv run python -m launchkit.scoreboard --approach llm      # score the LLM call
uv run python -m launchkit.scoreboard --approach graph    # score the LangGraph pipeline
uv run python -m launchkit.ask --approach llm "Poster for the Tidal bottle on a beach"
uv run python -m launchkit.ask --approach graph --conv mine "Make the headline shorter"
```

Outputs, and how each image was made, are written to `out/`.
