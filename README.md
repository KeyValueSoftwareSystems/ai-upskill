# LaunchKit session opener

LaunchKit is the mini-Pencil we build in this upskill: a marketing assistant platform that turns one campaign concept into on-brand poster ads. Our first customer is **Harbor**, launching the Flask Trail 750 in its new **Tidal** colourway.

## The problem statement

> Given a campaign concept (text, a photo, or both) and a brand's workspace, LaunchKit must produce on-brand poster ads: copy that obeys the brand's rules, a picture with no words drawn into it, every placement size, and follow-up edits, reliably and for any brand.

## Setup

You need Python 3.12 or newer, [`uv`](https://docs.astral.sh/uv/), git with access to the KeyValue repo, the coding agent you already use, and a key for KeyValue's LiteLLM proxy (ask the trainer).

```bash
uv sync
cp .env.example .env      # then add your LITELLM_API_KEY
uv run python -m launchkit.check_setup
```

The last command checks your Python version, dependencies, `.env`, LiteLLM key and URL, chat model, image model and the `out/` folder, and prints a fix under anything marked FAIL. When it ends with **Setup complete**, every check passed and you're ready for the session. The image check makes one small paid image call; add `--no-image` to skip it.

Images use `gpt-image-1` by default. To skip paid image calls, set `LAUNCHKIT_IMAGES=placeholder` in `.env`.
