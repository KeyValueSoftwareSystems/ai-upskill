"""Check that a trainee's environment is ready before the session starts.

    uv run python -m launchkit.check_setup             # full check
    uv run python -m launchkit.check_setup --no-image  # skip the paid image call

Prints one line per check, a one-line fix under anything that fails, and exits
0 when everything passed (or was skipped on request), 1 otherwise.
"""
from __future__ import annotations

import argparse
import base64
import importlib
import io
import os
import sys
import tempfile

from .poster import OUT, ROOT

NEXT_BRANCH = "session-01-llm-call"
WIDTH = 38          # label + dots, so every status lines up in one column
CHAT_TIMEOUT = 20   # seconds; a bad network should not hang the room
IMAGE_TIMEOUT = 90  # image generation is slower than chat


class Check:
    """Collects results so the summary and exit code can be decided at the end."""

    def __init__(self) -> None:
        self.failed = False

    def start(self, label: str) -> None:
        # Print the label before the work, so a slow API call doesn't look like a hang.
        print(f"{label} ".ljust(WIDTH, ".") + " ", end="", flush=True)

    def ok(self, detail: str = "") -> None:
        print("ok" + (f" ({detail})" if detail else ""), flush=True)

    def skip(self, reason: str) -> None:
        print(f"skipped ({reason})", flush=True)

    def fail(self, fix: str) -> None:
        self.failed = True
        print("FAIL", flush=True)
        print(f"    {fix}", flush=True)


def _scrub(text: str) -> str:
    """Never echo the key, even inside an error message."""
    key = os.getenv("LITELLM_API_KEY", "").strip()
    if key:
        text = text.replace(key, "<your key>")
    return " ".join(text.split())[:160]


def _api_fix(err: Exception, model: str, env_var: str) -> str:
    """Turn an API error into one line telling the trainee what to do."""
    import openai

    if isinstance(err, openai.AuthenticationError):
        return "The LiteLLM proxy rejected the key. Check LITELLM_API_KEY in .env (no quotes or spaces) or ask the trainer for a new one"
    if isinstance(err, (openai.PermissionDeniedError, openai.NotFoundError)):
        return f"Your key has no access to model '{model}'. Ask the trainer, or set {env_var} in .env to a model your key can use"
    if isinstance(err, openai.RateLimitError):
        if getattr(err, "code", None) == "insufficient_quota":
            return "The key's account has no credit left (insufficient_quota). Ask the trainer to top it up or for another key"
        return "Rate limited by the LiteLLM proxy. Wait a minute and run this again"
    if isinstance(err, openai.APITimeoutError):
        return "The LiteLLM proxy did not answer in time. Check your network (VPN, proxy, wifi) and run this again"
    if isinstance(err, openai.APIConnectionError):
        return "Could not reach the LiteLLM proxy. Check LITELLM_BASE_URL in .env and your network (VPN, wifi)"
    if isinstance(err, openai.BadRequestError):
        return f"The LiteLLM proxy refused the request for '{model}': {_scrub(str(getattr(err, 'message', err)))}. Check {env_var} in .env"
    if isinstance(err, openai.APIStatusError):
        return f"The LiteLLM proxy returned an error (HTTP {err.status_code}). Run this again; if it repeats, show the trainer"
    return f"Unexpected error ({type(err).__name__}): {_scrub(str(err))}"


def _image_options(model: str) -> dict:
    """Cheapest settings each image model family accepts, always returning base64."""
    if model == "dall-e-2":
        return {"response_format": "b64_json"}
    if model.startswith("dall-e"):
        return {"quality": "standard", "response_format": "b64_json"}
    return {"quality": "low"}  # gpt-image-* models always return base64


def check_python(c: Check) -> None:
    c.start("Python 3.12+")
    version = ".".join(str(n) for n in sys.version_info[:3])
    if sys.version_info >= (3, 12):
        c.ok(version)
    else:
        c.fail(f"You are on Python {version}. Install Python 3.12+ and run through uv: uv run python -m launchkit.check_setup")


def check_dependencies(c: Check) -> bool:
    c.start("Dependencies")
    missing = []
    for name in ("openai", "PIL", "dotenv", "langgraph"):
        try:
            importlib.import_module(name)
        except Exception:
            missing.append(name)
    if missing:
        c.fail(f"Missing: {', '.join(missing)}. Run `uv sync` in the repo root, then use `uv run`")
        return False
    c.ok()
    return True


def check_env_file(c: Check) -> None:
    c.start(".env found")
    if (ROOT / ".env").is_file():
        c.ok()
    else:
        c.fail(f"No .env in {ROOT}. Run `cp .env.example .env` there and add LITELLM_API_KEY and LITELLM_BASE_URL")


def check_key(c: Check, deps_ok: bool) -> bool:
    c.start("LiteLLM key and URL set")
    if deps_ok:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    missing = [v for v in ("LITELLM_API_KEY", "LITELLM_BASE_URL") if not os.getenv(v, "").strip()]
    if not missing:
        c.ok()
        return True
    c.fail(f"Add {' and '.join(missing)} to .env in the repo root (copy .env.example first)")
    return False


def check_chat(c: Check, blocked: str | None) -> None:
    model = os.getenv("LAUNCHKIT_MODEL", "gpt-4.1-mini")
    c.start(f"Chat model ({model})")
    if blocked:
        c.skip(blocked)
        return
    try:
        from .llm import client

        reply = client().with_options(timeout=CHAT_TIMEOUT, max_retries=0).chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": 'Reply with exactly one word: "Ready."'}],
        )
        text = " ".join((reply.choices[0].message.content or "").split())
    except Exception as err:
        c.fail(_api_fix(err, model, "LAUNCHKIT_MODEL"))
        return
    if text:
        c.ok(f'"{text[:40]}"')
    else:
        c.fail(f"'{model}' answered with an empty reply. Set LAUNCHKIT_MODEL in .env to a chat model such as gpt-4.1-mini")


def check_image(c: Check, blocked: str | None) -> None:
    model = os.getenv("LAUNCHKIT_IMAGE_MODEL", "gpt-image-1")
    c.start(f"Image model ({model})")
    if blocked:
        c.skip(blocked)
        return
    try:
        from .llm import client

        reply = client().with_options(timeout=IMAGE_TIMEOUT, max_retries=0).images.generate(
            model=model, prompt="A plain blue circle on a white background", size="1024x1024",
            **_image_options(model),
        )
    except Exception as err:
        c.fail(_api_fix(err, model, "LAUNCHKIT_IMAGE_MODEL"))
        return
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(base64.b64decode(reply.data[0].b64_json)))
        c.ok(f"{img.width}x{img.height}")
    except Exception:
        c.fail(f"'{model}' answered but the image could not be decoded. Show the trainer")


def check_out_dir(c: Check) -> None:
    c.start("Can write to out/")
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=OUT, prefix=".setup_check_")
        os.close(fd)
        os.remove(name)
        c.ok()
    except OSError as err:
        c.fail(f"Cannot write to {OUT} ({err.strerror}). Check the folder's permissions or clone the repo somewhere you own")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that your LaunchKit setup is ready.")
    parser.add_argument("--no-image", action="store_true", help="skip the paid image-generation call")
    args = parser.parse_args(argv)

    c = Check()
    check_python(c)
    deps_ok = check_dependencies(c)
    check_env_file(c)
    key_ok = check_key(c, deps_ok)

    api_blocked = None if deps_ok and key_ok else ("no key" if deps_ok else "dependencies missing")
    check_chat(c, api_blocked)

    image_blocked = api_blocked
    if image_blocked is None and args.no_image:
        image_blocked = "--no-image"
    elif image_blocked is None and os.getenv("LAUNCHKIT_IMAGES", "").strip() == "placeholder":
        image_blocked = "LAUNCHKIT_IMAGES=placeholder"
    check_image(c, image_blocked)

    check_out_dir(c)

    print()
    if c.failed:
        print("Setup incomplete: fix the items marked FAIL and run this again.")
        return 1
    print(f"Setup complete. Next: git checkout {NEXT_BRANCH}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(1)
