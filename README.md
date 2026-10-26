# LaunchKit session opener

LaunchKit is the mini-Pencil we build in this upskill: a marketing assistant platform that turns one campaign concept into on-brand poster ads. Our first customer is **Harbor**, launching the Flask Trail 750 in its new **Tidal** colourway.

## The problem statement

> Given a campaign concept (text, a photo, or both) and a brand's workspace, LaunchKit must produce on-brand poster ads: copy that obeys the brand's rules, a picture with no words drawn into it, every placement size, and follow-up edits, reliably and for any brand.

## Setup

You need Python 3.12 or newer, [`uv`](https://docs.astral.sh/uv/), git with access to the KeyValue repo, the coding agent you already use, a key for KeyValue's LiteLLM proxy and a key for our GPU (ask the trainer for both), and the VPN on.

```bash
uv sync
cp .env.example .env      # then add your LITELLM_API_KEY and IMAGESVC_KEY
uv run python -m launchkit.check_setup
```

The last command checks your Python version, dependencies, `.env`, LiteLLM key and URL, the chat model, pictures from our GPU, the backup image model and the `out/` folder, and prints a fix under anything marked FAIL. When it ends with **Setup complete**, you're ready for the session. A *warning* on the backup image model means pictures still work from the GPU: tell the trainer and carry on. The backup check makes one small paid image call; add `--no-image` to skip it (the GPU is still checked).

Pictures come from our GPU first and fall back to `gpt-image-1` through LiteLLM. To skip real pictures, set `LAUNCHKIT_IMAGES=placeholder` in `.env`.
