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

The last command checks your Python version, dependencies, `.env`, LiteLLM key and URL, the chat model, pictures and the `out/` folder, and prints a fix under anything marked FAIL. When it ends with **Setup complete**, you're ready for the session.

`LAUNCHKIT_IMAGE_PROVIDER` in `.env` picks who makes the pictures, and only that one is used:

| Value | Pictures from |
| --- | --- |
| `gpu` (the default) | Our GPU, over the VPN: a few seconds each. |
| `litellm` | `gpt-image-2` through LiteLLM: about a minute each, and paid. Use it only when the trainer says the GPU is down. |
| `placeholder` | Code draws a stand-in picture. No call. |

The setup check tests only the one you picked. With `litellm` it makes one small paid picture; add `--no-image` to skip it.
