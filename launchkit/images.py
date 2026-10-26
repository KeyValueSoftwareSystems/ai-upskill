"""Pictures: one made by the image model, and a resize that is plain code.

generate_image() asks the provider set by LAUNCHKIT_IMAGE_PROVIDER: gpu (the default), litellm or placeholder.
resize_image() is plain code, not a model. Both return a Picture: the file, and how it was made.
"""
import base64
import io
import os

from dotenv import load_dotenv
from PIL import Image, ImageColor, ImageDraw, ImageFont

from .gpu_images import gpu_image, image_provider
from .poster import OUT, Picture

load_dotenv()  # the GPU address and key live in .env


def _save(img: Image.Image, conversation_id: str, kind: str) -> str:
    folder = OUT / conversation_id
    folder.mkdir(parents=True, exist_ok=True)
    n = len(list(folder.glob("*.png"))) + 1
    path = folder / f"{n:02d}_{kind}_{img.width}x{img.height}.png"
    img.save(path)
    return str(path)


def _placeholder(brand: dict, reference: str | None) -> Image.Image:
    """A brand-coloured gradient (with the uploaded photo on top, if any) instead of a paid image."""
    w = h = 1024
    top, bottom = ImageColor.getrgb(brand["colours"]["navy"]), ImageColor.getrgb(brand["colours"]["sea_glass"])
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        draw.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    if reference:
        photo = Image.open(reference).convert("RGB")
        photo.thumbnail((int(w * 0.7), int(h * 0.7)))
        img.paste(photo, ((w - photo.width) // 2, (h - photo.height) // 2))
    label = "PLACEHOLDER: no image model call"
    draw.text((w // 2, 60), label, fill=(255, 255, 255), anchor="mm", font=ImageFont.load_default(size=40))
    return img


def generate_image(visual_concept: str, brand: dict, *, conversation_id: str,
                   reference: str | None = None) -> Picture:
    """Ask the image model for the poster picture. Pass the visual concept only, never the copy."""
    colours = ", ".join(brand["colours"].values())
    prompt = f"{visual_concept}. Colour palette: {colours}. The product is plain and unbranded, with a smooth blank surface and no label."
    provider = image_provider()
    placeholder = provider == "placeholder"
    if placeholder:
        img = _placeholder(brand, reference)
        source = "code (placeholder)"
    else:
        if provider == "gpu":
            data = gpu_image(prompt, reference=reference)
            source = f"our GPU ({os.getenv('IMAGESVC_MODEL', 'flux-2-klein-9b')})"
        else:
            from .llm import client
            model = os.getenv("LAUNCHKIT_IMAGE_MODEL", "gpt-image-2")
            source = f"LiteLLM ({model})"
            if reference:
                with open(reference, "rb") as f:
                    reply = client().images.edit(model=model, image=f, prompt=prompt, size="1024x1024")
            else:
                reply = client().images.generate(model=model, prompt=prompt, size="1024x1024")
            data = base64.b64decode(reply.data[0].b64_json)
        img = Image.open(io.BytesIO(data)).convert("RGB")
    path = _save(img, conversation_id, "generated")
    return Picture(path, (img.width, img.height), prompt=prompt, reference=reference, placeholder=placeholder, source=source)


def resize_image(picture: Picture, size: tuple[int, int], *, conversation_id: str) -> Picture:
    """Plain code, no model: centre-crop the picture to the target shape, then scale it."""
    src = Image.open(picture.path).convert("RGB")
    tw, th = size
    if src.width / src.height > tw / th:  # too wide: trim the sides
        nw = int(src.height * tw / th)
        box = ((src.width - nw) // 2, 0, (src.width - nw) // 2 + nw, src.height)
    else:                                 # too tall: trim top and bottom
        nh = int(src.width * th / tw)
        box = (0, (src.height - nh) // 2, src.width, (src.height - nh) // 2 + nh)
    path = _save(src.crop(box).resize(size), conversation_id, "resized")
    return Picture(path, (tw, th), resized_from=picture.path, placeholder=picture.placeholder)
