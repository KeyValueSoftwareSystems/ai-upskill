"""The picture tools for "every size". The harness binds the newest picture in this conversation, one the marketer
attached or one the agent made: the model never names a file.

Plain code cuts, pads or stretches the picture: free, and the same every time. One tool asks a vision model
where the bottle is: it costs money, so the desk asks once per poster and keeps the box.
"""

import base64
import functools
import json
from pathlib import Path

from PIL import Image, ImageColor

from launchkit.harness.catalogue import Entry
from launchkit.harness.pictures import NO_PICTURE, NoPicture, sidecar
from launchkit.harness.trace import Trace
from launchkit.settings import ROOT

# Maya's approved Tidal poster, ready to attach in the chat. The tools never read it unless she attaches it.
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


def colour_of(name: str, colours: dict) -> str:
    return colours.get(name, name) if name else next(iter(colours.values()), "#000000")


def find_subject(picture: Path, model) -> list[int]:
    """Ask a vision model for the main subject's box. With a fake model, read the box saved next to the picture."""
    if model is None or getattr(model, "provider", "") == "fake" or not hasattr(model, "id"):
        saved = sidecar(picture, ".bottle.json")
        if saved is None:
            raise NoPicture("The fake model only knows the sample pictures in samples/; use the real model for this one.")
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
        extra_body={"cache": {"no-cache": True}},
    )
    text = reply.choices[0].message.content or ""
    return json.loads(text[text.find("{"): text.rfind("}") + 1])["box"]


def needs_picture(fn):
    """No picture in this conversation: the tool says so, and the agent can tell the marketer."""

    @functools.wraps(fn)
    def call(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except NoPicture as missing:
            return {"status": "no picture", "reason": str(missing)}

    return call


class PictureDesk:
    def __init__(self, settings, colours: dict, trace: Trace, model=None, source=None):
        self._source = source
        self.colours = colours
        self.trace = trace
        self.model = model
        self.out = settings.data_dir / "sizes"
        self._box: list[int] | None = None
        self._box_for: Path | None = None

    @property
    def source(self) -> Path:
        """The picture to work on: the newest in this conversation, asked for at each call."""
        picked = self._source() if callable(self._source) else self._source
        if picked is None:
            raise NoPicture(NO_PICTURE)
        return Path(picked)

    @source.setter
    def source(self, picture):
        self._source = picture

    @property
    def box(self) -> list[int] | None:
        """The bottle's box, kept for the picture it was found in."""
        return self._box if self._box_for == self.source else None

    @box.setter
    def box(self, value):
        self._box, self._box_for = value, (self.source if value is not None else None)

    def open(self) -> Image.Image:
        return Image.open(self.source).convert("RGB")

    def save(self, img: Image.Image, kind: str) -> str:
        self.out.mkdir(parents=True, exist_ok=True)
        path = self.out / f"{self.source.stem}-{kind}-{img.width}x{img.height}.png"
        img.save(path)
        return str(path)

    @todo
    def centre_crop(self, width: int, height: int) -> dict:
        """Step 1, move 1: not built yet."""
        return {"status": "not built"}

    @todo
    def detect_focal_point(self) -> dict:
        """Step 1, move 2: not built yet."""
        return {"status": "not built"}

    @todo
    def crop(self, width: int, height: int, left: int = -1, top: int = -1, right: int = -1, bottom: int = -1) -> dict:
        """Step 1, move 2: not built yet."""
        return {"status": "not built"}

    @todo
    def expand_canvas(self, width: int, height: int, colour: str = "") -> dict:
        """Step 1, move 2: not built yet."""
        return {"status": "not built"}

    @todo
    def scale(self, width: int, height: int) -> dict:
        """Step 1, move 2: not built yet."""
        return {"status": "not built"}

    def entries(self) -> list[Entry]:
        return [
            Entry("centre_crop", "cut the approved poster to a new size from its centre", "read", needs_picture(self.centre_crop)),
            Entry("detect_focal_point", "find where the product sits in the approved poster", "read", needs_picture(self.detect_focal_point)),
            Entry("crop", "cut any window out of the approved poster at a new size", "read", needs_picture(self.crop)),
            Entry("expand_canvas", "fit the whole approved poster into a new size, with bars of a brand colour", "read", needs_picture(self.expand_canvas)),
            Entry("scale", "stretch the approved poster to a new size", "read", needs_picture(self.scale)),
        ]
