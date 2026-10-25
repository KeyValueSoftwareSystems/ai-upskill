import base64
import os
import textwrap
from pathlib import Path
from time import time

from PIL import Image, ImageDraw, ImageFont

from launchkit.gpu_images import gpu_image


class FakeImages:
    def __init__(self, out_dir: Path):
        self.out_dir = Path(out_dir)
        self.calls: list[tuple[str, dict]] = []

    def generate(self, prompt: str, colours: dict, reference: Path | None = None) -> Path:
        self.calls.append((prompt, colours))
        self.out_dir.mkdir(parents=True, exist_ok=True)
        width, height = 768, 1024
        shades = list(colours.values())
        image = Image.new("RGB", (width, height), shades[0] if shades else "#2f3b45")
        draw = ImageDraw.Draw(image)
        ink = shades[-1] if len(shades) > 1 else "#f2f2f2"
        font = ImageFont.load_default(size=26)
        draw.text((40, 40), "FAKE PICTURE", fill=ink, font=ImageFont.load_default(size=40))
        y = 140
        for line in textwrap.wrap(prompt, 44):
            draw.text((40, y), line, fill=ink, font=font)
            y += 36
        path = self.out_dir / f"poster-{int(time() * 1000)}-{len(self.calls)}.png"
        image.save(path)
        return path


class RealImages:
    def __init__(self, settings, out_dir: Path):
        self.settings = settings
        self.out_dir = Path(out_dir)
        self.calls: list[tuple[str, dict]] = []

    def client(self):
        from openai import OpenAI

        if self.via_proxy():
            key, url = os.environ.get("LITELLM_API_KEY"), os.environ.get("LITELLM_BASE_URL")
            return OpenAI(api_key=key, base_url=url, timeout=self.settings.timeout, max_retries=1)
        return OpenAI(timeout=self.settings.timeout, max_retries=1)

    @staticmethod
    def via_proxy() -> bool:
        return bool(os.environ.get("LITELLM_API_KEY") and os.environ.get("LITELLM_BASE_URL"))

    def call(self, full_prompt: str, reference: Path | None = None):
        from openai import AuthenticationError

        client = self.client()
        tries = 3 if self.via_proxy() else 1
        for attempt in range(1, tries + 1):
            try:
                if reference:
                    with open(reference, "rb") as picture:
                        return client.images.edit(
                            model=self.settings.image_model, image=picture, prompt=full_prompt, size=self.settings.image_size, quality=self.settings.image_quality, n=1
                        )
                return client.images.generate(
                    model=self.settings.image_model, prompt=full_prompt, size=self.settings.image_size, quality=self.settings.image_quality, n=1
                )
            except AuthenticationError:
                if attempt == tries:
                    raise

    def generate(self, prompt: str, colours: dict, reference: Path | None = None) -> Path:
        self.calls.append((prompt, colours))
        self.out_dir.mkdir(parents=True, exist_ok=True)
        palette = ", ".join(f"{name} {value}" for name, value in colours.items())
        full_prompt = f"{prompt}. Colour palette: {palette}. The product is plain and unbranded, with a smooth blank surface and no label." if palette else f"{prompt}. The product is plain and unbranded, with a smooth blank surface and no label."
        data = gpu_image(full_prompt, self.settings.image_size, reference=str(reference) if reference else None)
        if data is None:
            data = base64.b64decode(self.call(full_prompt, reference).data[0].b64_json)
        path = self.out_dir / f"poster-{int(time() * 1000)}.png"
        path.write_bytes(data)
        return path


class FromPicture:
    """The same adapter, told to start from a picture the conversation already has, so the product and scene stay the same."""

    def __init__(self, images, reference: Path):
        self.images = images
        self.reference = reference
        self.calls = images.calls

    def generate(self, prompt: str, colours: dict) -> Path:
        return self.images.generate(prompt, colours, reference=self.reference)


def make_images(settings):
    out_dir = settings.data_dir / "outputs"
    has_key = (os.environ.get("LITELLM_API_KEY") and os.environ.get("LITELLM_BASE_URL")) or os.environ.get("OPENAI_API_KEY") or os.environ.get("IMAGESVC_URL")
    placeholder = settings.image_mode == "fake" or os.environ.get("LAUNCHKIT_IMAGES") == "placeholder"
    if placeholder or not has_key:
        return FakeImages(out_dir)
    return RealImages(settings, out_dir)
