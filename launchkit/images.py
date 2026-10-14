"""Image generation and a deterministic resize tool.

generate_image() calls the image model (LAUNCHKIT_IMAGE_MODEL, default gpt-image-1).
Set LAUNCHKIT_IMAGES=placeholder to draw a placeholder instead and skip paid calls.
resize_image() is plain code, not a model. Every image gets a .json sidecar
recording how it was made, so checks can confirm the copy never reached the image model.
"""
import base64
import io
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw

from .paths import out_dir


def _save(img: Image.Image, conversation_id: str, meta: dict) -> str:
    folder = out_dir(conversation_id)
    n = len(list(folder.glob("*.png"))) + 1
    path = folder / f"{n:02d}_{meta['kind']}_{img.width}x{img.height}.png"
    img.save(path)
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    return str(path)


def read_meta(path: str) -> dict:
    return json.loads(Path(path).with_suffix(".json").read_text())


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _placeholder(brand: dict, size: tuple[int, int], reference: str | None) -> Image.Image:
    w, h = size
    top, bottom = _hex(brand["colours"]["navy"]), _hex(brand["colours"]["sea_glass"])
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        draw.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    if reference:
        ref = Image.open(reference).convert("RGB")
        ref.thumbnail((int(w * 0.7), int(h * 0.7)))
        img.paste(ref, ((w - ref.width) // 2, (h - ref.height) // 2))
    draw.text((16, h - 28), "placeholder image", fill=(255, 255, 255))
    return img


def generate_image(visual_concept: str, brand: dict, *, conversation_id: str,
                   reference: str | None = None) -> str:
    """Generate the poster picture. Pass the visual concept only, never the copy."""
    colours = ", ".join(brand["colours"].values())
    prompt = f"{visual_concept}. Colour palette: {colours}. No text, letters or logos in the image."
    if os.getenv("LAUNCHKIT_IMAGES", "openai") == "placeholder":
        img = _placeholder(brand, (1024, 1024), reference)
    else:
        from .llm import client
        model = os.getenv("LAUNCHKIT_IMAGE_MODEL", "gpt-image-1")
        if reference:
            with open(reference, "rb") as f:
                reply = client().images.edit(model=model, image=f, prompt=prompt, size="1024x1024")
        else:
            reply = client().images.generate(model=model, prompt=prompt, size="1024x1024")
        img = Image.open(io.BytesIO(base64.b64decode(reply.data[0].b64_json))).convert("RGB")
    meta = {"kind": "generated", "prompt": prompt, "size": [img.width, img.height], "reference": reference}
    return _save(img, conversation_id, meta)


def resize_image(path: str, size: tuple[int, int], *, conversation_id: str) -> str:
    """Deterministic resize: centre-crop to the target ratio, then scale."""
    src = Image.open(path).convert("RGB")
    tw, th = size
    target, current = tw / th, src.width / src.height
    if current > target:
        nw = int(src.height * target)
        box = ((src.width - nw) // 2, 0, (src.width - nw) // 2 + nw, src.height)
    else:
        nh = int(src.width / target)
        box = (0, (src.height - nh) // 2, src.width, (src.height - nh) // 2 + nh)
    img = src.crop(box).resize(size)
    meta = {"kind": "resized", "derived_from": path, "size": [tw, th]}
    return _save(img, conversation_id, meta)
