"""text_to_speech: turns a short script into a voice-over file in the conversation's outputs/ drawer. With the fakes it
writes a silent file, so the checks run offline."""

import os
import uuid
import wave

from launchkit.tools.catalogue import Entry
from launchkit.tools.describe_image import is_fake


def make_text_to_speech(settings, model, files=None):
    out = files.drawer("outputs") if files is not None else settings.data_dir / "audio"

    def text_to_speech(script: str) -> dict:
        """Turn a short script into a spoken voice-over file. It costs money: write and check the script first."""
        out.mkdir(parents=True, exist_ok=True)
        if is_fake(settings, model):
            path = out / f"voice-over-{uuid.uuid4().hex[:4]}.wav"
            with wave.open(str(path), "wb") as f:
                f.setnchannels(1), f.setsampwidth(2), f.setframerate(8000), f.writeframes(b"\x00\x00" * 8000)
            return {"file": str(path), "words": len(script.split())}
        from launchkit.adapters.llm import client

        path = out / f"voice-over-{uuid.uuid4().hex[:4]}.mp3"
        speech = client().audio.speech.create(model=os.getenv("LAUNCHKIT_TTS_MODEL", "gpt-4o-mini-tts"), voice="alloy", input=script)
        path.write_bytes(speech.content)
        return {"file": str(path), "words": len(script.split())}

    return text_to_speech


def text_to_speech_entry(settings, model, files=None) -> Entry:
    return Entry("text_to_speech", "turn a short script into a spoken voice-over", "read", make_text_to_speech(settings, model, files))
