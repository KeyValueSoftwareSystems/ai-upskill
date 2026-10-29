"""The picture tools for "every size". The harness binds the approved poster: the model never names a file.

Plain code cuts, pads or stretches the picture: free, and the same every time. One tool asks a vision model
where the bottle is: it costs money, so the desk asks once per poster and keeps the box.
"""

import base64
import json
from pathlib import Path

from PIL import Image, ImageColor

from launchkit.harness.catalogue import Entry, built
from launchkit.harness.trace import Trace
from launchkit.settings import ROOT

APPROVED = ROOT / "samples" / "approved" / "tidal-poster.jpg"


def todo(fn):
    """Marks a slot. The catalogue leaves it out until it is built."""
    fn.todo = True
    return fn


def centre_window(size: tuple[int, int], target: tuple[int, int]) -> tuple[int, int, int, int]:
    """The biggest window of the target's shape, cut from the centre. Session 1's resize_image does exactly this."""
    w, h = size
    tw, th = target
    if w / h > tw / th:
        nw = int(h * tw / th)
        return ((w - nw) // 2, 0, (w - nw) // 2 + nw, h)
    nh = int(w * th / tw)
    return (0, (h - nh) // 2, w, (h - nh) // 2 + nh)


def window_around(box: list[int], size: tuple[int, int], target: tuple[int, int], margin: float = 0.08) -> tuple[int, int, int, int] | None:
    """The bottle-box fit rule. The biggest window of the target's shape, centred on the box and pushed back inside the
    picture. It counts only if it holds the whole box plus a margin on every side; else None. Plain code, no model."""
    w, h = size
    tw, th = target
    ww, wh = (h * tw / th, h) if w / h > tw / th else (w, w * th / tw)
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    left = min(max(cx - ww / 2, 0), w - ww)
    top = min(max(cy - wh / 2, 0), h - wh)
    window = (round(left), round(top), round(left + ww), round(top + wh))
    mx, my = (box[2] - box[0]) * margin, (box[3] - box[1]) * margin
    fits = window[0] <= box[0] - mx and window[1] <= box[1] - my and window[2] >= box[2] + mx and window[3] >= box[3] + my
    return window if fits else None


def colour_of(name: str, colours: dict) -> str:
    return colours.get(name, name) if name else next(iter(colours.values()), "#000000")


def find_subject(picture: Path, model) -> list[int]:
    """Ask a vision model for the main subject's box. With a fake model, read the box saved next to the picture."""
    saved = picture.with_suffix(".bottle.json")
    if model is None or getattr(model, "provider", "") == "fake" or not hasattr(model, "id"):
        return json.loads(saved.read_text())["box"]
    from launchkit.llm import client

    image = base64.b64encode(picture.read_bytes()).decode()
    w, h = Image.open(picture).size
    ask = (
        f"This poster is {w}x{h} pixels. Find the product, the main subject. Reply with JSON only: "
        '{"box": [left, top, right, bottom]} in pixels, tight around the whole product.'
    )
    reply = client().chat.completions.create(
        model=model.id,
        messages=[{"role": "user", "content": [{"type": "text", "text": ask}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}}]}],
        extra_body=None if "api.openai.com" in str(client().base_url) else {"cache": {"no-cache": True}},
    )
    text = reply.choices[0].message.content or ""
    return json.loads(text[text.find("{"): text.rfind("}") + 1])["box"]


class PictureDesk:
    def __init__(self, settings, colours: dict, trace: Trace, model=None, source: Path = APPROVED):
        self.source = Path(source)
        self.colours = colours
        self.trace = trace
        self.model = model
        self.out = settings.data_dir / "sizes"
        self.box: list[int] | None = None

    def open(self) -> Image.Image:
        return Image.open(self.source).convert("RGB")

    def save(self, img: Image.Image, kind: str) -> str:
        self.out.mkdir(parents=True, exist_ok=True)
        path = self.out / f"{self.source.stem}-{kind}-{img.width}x{img.height}.png"
        img.save(path)
        return str(path)

    def centre_crop(self, width: int, height: int) -> dict:
        """Cut the approved poster to a new size from its centre, then scale it. Plain code: free, the same every time."""
        img = self.open()
        window = centre_window(img.size, (width, height))
        return {"file": self.save(img.crop(window).resize((width, height)), "centre"), "size": f"{width}x{height}", "window": list(window)}

    def detect_focal_point(self) -> dict:
        """Find the main subject of the approved poster, here the bottle, and give back its box [left, top, right, bottom]
        in pixels. It asks a vision model, so it costs money: the box is kept for the next call."""
        if self.box is None:
            self.box = find_subject(self.source, self.model)
            self.trace.note(f"detect_focal_point asked the vision model once: box {self.box}")
        return {"box": self.box}

    def crop(self, width: int, height: int, left: int = -1, top: int = -1, right: int = -1, bottom: int = -1) -> dict:
        """Cut a window [left, top, right, bottom] out of the approved poster and scale it to width x height. The window
        should already have the new size's shape. Leave the window out to cut around the product. Plain code."""
        img = self.open()
        if min(left, top, right, bottom) < 0:
            if not built(window_around):
                return {"status": "refused", "reason": "give the window to cut: left, top, right, bottom"}
            window = window_around(self.detect_focal_point()["box"], img.size, (width, height))
            if window is None:
                return {"status": "does not fit", "reason": "the product and its margin do not fit this shape", "next": "expand_canvas"}
        else:
            window = (left, top, right, bottom)
        whole = self.box is None or (window[0] <= self.box[0] and window[1] <= self.box[1] and window[2] >= self.box[2] and window[3] >= self.box[3])
        return {"file": self.save(img.crop(window).resize((width, height)), "crop"), "size": f"{width}x{height}", "window": list(window), "product_whole": whole}

    def expand_canvas(self, width: int, height: int, colour: str = "") -> dict:
        """Fit the whole approved poster into width x height without cutting anything, and fill the new space with a
        brand colour, e.g. "navy". Plain code."""
        img = self.open()
        img.thumbnail((width, height))
        canvas = Image.new("RGB", (width, height), ImageColor.getrgb(colour_of(colour, self.colours)))
        canvas.paste(img, ((width - img.width) // 2, (height - img.height) // 2))
        return {"file": self.save(canvas, "bars"), "size": f"{width}x{height}"}

    def scale(self, width: int, height: int) -> dict:
        """Stretch the approved poster to width x height. Fast, plain code, and it changes the poster's proportions."""
        return {"file": self.save(self.open().resize((width, height)), "scaled"), "size": f"{width}x{height}"}

    def entries(self) -> list[Entry]:
        return [
            Entry("detect_focal_point", "find where the product sits in the approved poster", "read", self.detect_focal_point),
            Entry("crop", "cut any window out of the approved poster at a new size", "read", self.crop),
            Entry("expand_canvas", "fit the whole approved poster into a new size, with bars of a brand colour", "read", self.expand_canvas),
            Entry("scale", "stretch the approved poster to a new size", "read", self.scale),
        ]
