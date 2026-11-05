"""describe_image: looks at the photo the marketer attached and says what it shows. With the fakes it reads a saved
answer, so the checks run offline."""

import base64
import json
from pathlib import Path

from launchkit.adapters.models import now, timed_vision_call
from launchkit.memory.attached_pictures import NoPicture, sidecar
from launchkit.settings import ROOT
from launchkit.tools.catalogue import Entry

# A shoot photo, ready to attach in the chat. The tools never read it unless the marketer attaches it.
SHOOT_PHOTO = ROOT / "samples" / "shoot" / "tidal-shoot.jpg"


def is_fake(settings, model) -> bool:
    return settings.image_mode == "fake" or model is None or getattr(model, "provider", "") == "fake"


def make_describe_image(settings, model, desk=None):
    def describe_image() -> dict:
        """Look at the photo the marketer attached, the newest picture in this conversation: describe it, and say whether it shows any words or another brand's logo.
        A clean photo becomes the picture the picture tools work on. Asks a vision model."""
        try:
            photo = desk.source if desk is not None else None
        except NoPicture:
            photo = None
        if photo is None:
            return {"status": "no photo given", "reason": "Attach the photo to this conversation first."}
        chosen = now(model)
        if is_fake(settings, chosen):
            saved = sidecar(photo, ".describe.json")
            if saved is None:
                return {"status": "unknown photo", "reason": "The fake model only knows the sample photos in samples/."}
            seen = json.loads(saved.read_text())
        else:
            seen = look_at(photo, chosen)
        if desk is not None and not seen.get("text") and not seen.get("other_brand"):
            desk.use_photo(photo)
            seen["now_working_on"] = "the marketer's photo"
        return seen

    return describe_image


def look_at(photo: Path, model) -> dict:
    """Ask a vision model what the photo shows."""
    ask = 'Describe this photo in one sentence. Reply with JSON only: {"text": true|false, "other_brand": true|false, "description": "..."}. text means any visible words; other_brand means any logo or brand name.'
    image = base64.b64encode(photo.read_bytes()).decode()
    reply = timed_vision_call(
        model,
        messages=[{"role": "user", "content": [{"type": "text", "text": ask}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}}]}],
        extra_body={"cache": {"no-cache": True}},
    )
    text = reply.choices[0].message.content or ""
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


def describe_image_entry(settings, model, desk=None) -> Entry:
    return Entry("describe_image", "look at a photo the marketer gave and say what it shows", "read", make_describe_image(settings, model, desk))
