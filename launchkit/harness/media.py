"""Two model tools for step 3's new asks: describe_image looks at the marketer's photo, text_to_speech makes a
voice-over. With the fakes they read a saved answer or write a silent file, so every check runs offline."""

import base64
import json
import os
import wave
from pathlib import Path

from launchkit.harness.catalogue import Entry
from launchkit.settings import ROOT

SHOOT_DIR = ROOT / "samples" / "shoot"


def shoot_photo() -> Path | None:
    """The photo the marketer gave. The harness binds it, so the model never names a file."""
    photos = sorted(SHOOT_DIR.glob("*.jpg"))
    return photos[-1] if photos else None


def is_fake(settings, model) -> bool:
    return settings.image_mode == "fake" or model is None or getattr(model, "provider", "") == "fake"


def make_describe_image(settings, model, desk=None):
    def describe_image() -> dict:
        """Look at the photo the marketer gave: describe it, and say whether it shows any words or another brand's logo.
        A clean photo becomes the picture the picture tools work on. Asks a vision model."""
        photo = shoot_photo()
        if photo is None:
            return {"status": "no photo given"}
        seen = json.loads(photo.with_suffix(".describe.json").read_text()) if is_fake(settings, model) else look_at(photo, model)
        if desk is not None and not seen.get("text") and not seen.get("other_brand"):
            desk.use_photo(photo)
            seen["now_working_on"] = "the marketer's photo"
        return seen

    return describe_image


def look_at(photo: Path, model) -> dict:
    """Ask a vision model what the photo shows."""
    from launchkit.llm import client

    ask = 'Describe this photo in one sentence. Reply with JSON only: {"text": true|false, "other_brand": true|false, "description": "..."}. text means any visible words; other_brand means any logo or brand name.'
    image = base64.b64encode(photo.read_bytes()).decode()
    reply = client().chat.completions.create(
        model=model.id,
        messages=[{"role": "user", "content": [{"type": "text", "text": ask}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}}]}],
        extra_body=None if "api.openai.com" in str(client().base_url) else {"cache": {"no-cache": True}},
    )
    text = reply.choices[0].message.content or ""
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


def make_text_to_speech(settings, model):
    out = settings.data_dir / "audio"

    def text_to_speech(script: str) -> dict:
        """Turn a short script into a spoken voice-over file. It costs money: write and check the script first."""
        out.mkdir(parents=True, exist_ok=True)
        if is_fake(settings, model):
            path = out / "voice-over.wav"
            with wave.open(str(path), "wb") as f:
                f.setnchannels(1), f.setsampwidth(2), f.setframerate(8000), f.writeframes(b"\x00\x00" * 8000)
            return {"file": str(path), "words": len(script.split())}
        from launchkit.llm import client

        path = out / "voice-over.mp3"
        speech = client().audio.speech.create(model=os.getenv("LAUNCHKIT_TTS_MODEL", "gpt-4o-mini-tts"), voice="alloy", input=script)
        path.write_bytes(speech.content)
        return {"file": str(path), "words": len(script.split())}

    return text_to_speech


def media_entries(settings, model, desk=None) -> list[Entry]:
    return [
        Entry("describe_image", "look at a photo the marketer gave and say what it shows", "read", make_describe_image(settings, model, desk)),
        Entry("text_to_speech", "turn a short script into a spoken voice-over", "read", make_text_to_speech(settings, model)),
    ]
