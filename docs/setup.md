# Setup, before the session

Do this before the day. It takes about ten minutes. At the start of the build we only confirm it.

## On your machine

- Python 3.12 or newer.
- [uv](https://docs.astral.sh/uv/), the Python package runner. `curl -LsSf https://astral.sh/uv/install.sh | sh` on macOS and Linux.
- git, and access to this repository.
- A coding agent you already use: Cursor, Claude Code, or another. Each step gives you a short prompt to hand to it.
- A key for KeyValue's LiteLLM proxy. The trainer gives you one. It goes in `.env` as `LITELLM_API_KEY`, next to `LITELLM_BASE_URL`.

## Proof it works

```
git clone <this repository> && cd ai-upskill
uv sync
cp .env.example .env            # paste your key after LITELLM_API_KEY=
uv run launchkit run harbor "Poster for the Tidal bottle on a misty lakeshore at dawn."   # prints a trace and a spec
uv run launchkit ui             # open http://localhost:8000, sign in as Maya at Harbor, say hi, then ask for a poster
```

If port 8000 is taken: `uv run launchkit ui --port 8010`.

Everyone makes real pictures, on our GPU: a few seconds each. If the trainer says the GPU is down, set `LAUNCHKIT_IMAGE_PROVIDER=litellm` in `.env` (30 to 60 seconds each through the proxy). If you only want to see the words, `LAUNCHKIT_IMAGE_PROVIDER=placeholder` draws a stand-in picture instead.

Without a key everything still runs. Live runs use a fake model and a fake picture, and the trace says so.

## Read once

- [glossary.md](glossary.md), the words we use. Five minutes.
