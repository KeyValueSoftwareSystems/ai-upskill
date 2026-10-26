"""Who makes the pictures: LAUNCHKIT_IMAGE_PROVIDER in .env picks one, and only that one is used.

    gpu          our GPU over the VPN (IMAGESVC_URL, IMAGESVC_KEY): a few seconds a picture. The default.
    litellm      the image model through LiteLLM (LAUNCHKIT_IMAGE_MODEL, default gpt-image-2): paid, slower.
    placeholder  no model: code draws a stand-in picture.

LAUNCHKIT_IMAGES=placeholder, the older spelling, still means placeholder.
"""
import base64
import os

PROVIDERS = ("gpu", "litellm", "placeholder")

SIZES = [(1024, 1024), (1152, 896), (1216, 832), (1344, 768), (896, 1152), (832, 1216), (768, 1344)]


def nearest_size(size: str) -> str:
    """The service's size closest in shape to the one asked for, e.g. 1024x1536 -> 832x1216."""
    w, h = (int(n) for n in size.split("x"))
    best = min(SIZES, key=lambda s: abs(s[0] / s[1] - w / h))
    return f"{best[0]}x{best[1]}"


def image_provider() -> str:
    if "placeholder" in (os.getenv("LAUNCHKIT_IMAGES", "").strip(), os.getenv("LAUNCHKIT_IMAGE_PROVIDER", "").strip()):
        return "placeholder"
    provider = os.getenv("LAUNCHKIT_IMAGE_PROVIDER", "").strip().lower() or "gpu"
    if provider not in PROVIDERS:
        raise ValueError(f"LAUNCHKIT_IMAGE_PROVIDER={provider} is not known. Set it to gpu, litellm or placeholder in .env")
    return provider


def gpu_image(prompt: str, size: str = "1024x1024", reference: str | None = None) -> bytes:
    url = os.getenv("IMAGESVC_URL", "").strip()
    if not url:
        raise RuntimeError("IMAGESVC_URL is not set in .env. Add it (see .env.example), or set LAUNCHKIT_IMAGE_PROVIDER=litellm")
    import httpx
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
        raise RuntimeError(f"Our GPU could not make the picture ({type(error).__name__}). "
                           "Turn the VPN on and check IMAGESVC_KEY, or set LAUNCHKIT_IMAGE_PROVIDER=litellm in .env") from error
