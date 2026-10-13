import base64
import os
import textwrap
from pathlib import Path
from time import time

from PIL import Image, ImageDraw, ImageFont


class FakeImages:
    def __init__(self, out_dir: Path):
        self.out_dir = Path(out_dir)
        self.calls: list[tuple[str, dict]] = []

    def generate(self, prompt: str, colours: dict) -> Path:
        self.calls.append((prompt, colours))
        self.out_dir.mkdir(parents=True, exist_ok=True)
        width, height = 768, 1024
        image = Image.new("RGB", (width, height), colours.get("primary", "#2f3b45"))
        draw = ImageDraw.Draw(image)
        ink = colours.get("secondary", "#f2f2f2")
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

    def generate(self, prompt: str, colours: dict) -> Path:
        from openai import OpenAI

        self.calls.append((prompt, colours))
        self.out_dir.mkdir(parents=True, exist_ok=True)
        palette = ", ".join(f"{name} {value}" for name, value in colours.items())
        full_prompt = f"{prompt}. Colour palette: {palette}. No text, no letters, no logos." if palette else f"{prompt}. No text, no letters, no logos."
        response = OpenAI().images.generate(model=self.settings.image_model, prompt=full_prompt, size=self.settings.image_size, n=1)
        path = self.out_dir / f"poster-{int(time() * 1000)}.png"
        path.write_bytes(base64.b64decode(response.data[0].b64_json))
        return path


def make_images(settings):
    out_dir = settings.data_dir / "outputs"
    if settings.image_mode == "fake" or not os.environ.get("OPENAI_API_KEY"):
        return FakeImages(out_dir)
    return RealImages(settings, out_dir)
