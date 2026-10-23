"""Pictures from our own GPU, tried before the image model behind LiteLLM.

Set IMAGESVC_URL (and IMAGESVC_KEY) in .env; the service is reachable over the VPN.
gpu_image() returns None when the URL isn't set or the service doesn't answer,
so the caller falls back to LAUNCHKIT_IMAGE_MODEL (gpt-image-1).
"""
import base64
import os
import sys

import httpx

SIZES = [(1024, 1024), (1152, 896), (1216, 832), (1344, 768), (896, 1152), (832, 1216), (768, 1344)]


def nearest_size(size: str) -> str:
    """The service's size closest in shape to the one asked for, e.g. 1024x1536 -> 832x1216."""
    w, h = (int(n) for n in size.split("x"))
    best = min(SIZES, key=lambda s: abs(s[0] / s[1] - w / h))
    return f"{best[0]}x{best[1]}"


def gpu_image(prompt: str, size: str = "1024x1024", reference: str | None = None) -> bytes | None:
    url = os.getenv("IMAGESVC_URL")
    if not url:
        return None
    from openai import OpenAI

    client = OpenAI(base_url=url, api_key=os.getenv("IMAGESVC_KEY") or "none",
                    timeout=httpx.Timeout(130, connect=5), max_retries=1)
    args = dict(model=os.getenv("IMAGESVC_MODEL", "flux-2-klein-9b"), prompt=prompt, n=1, response_format="b64_json")
    try:
        if reference:
            with open(reference, "rb") as f:
                reply = client.images.edit(image=f, size="auto", **args)
        else:
            reply = client.images.generate(size=nearest_size(size), **args)
        return base64.b64decode(reply.data[0].b64_json)
    except Exception as error:
        print(f"GPU image service failed ({type(error).__name__}); using {os.getenv('LAUNCHKIT_IMAGE_MODEL', 'gpt-image-1')}",
              file=sys.stderr)
        return None
