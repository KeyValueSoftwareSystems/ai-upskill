"""The pictures in one conversation: the ones the marketer attached and the ones the agent made. The picture tools
work on the newest one. They are kept with the conversation, like its chat history; a new conversation starts with none.
"""

import hashlib
import json
import shutil
from pathlib import Path

from launchkit.settings import ROOT

NO_PICTURE = ("No poster in this conversation yet. Stop here and tell the marketer: attach the poster to the chat, "
              "or ask for a new poster first.")


class NoPicture(Exception):
    pass


def sidecar(picture: Path, suffix: str) -> Path | None:
    """A saved answer next to a picture (the bottle's box, a description) for the fakes. A sample picture copied in by
    an upload keeps its answers: the same bytes as a file under samples/ means the same picture."""
    here = picture.with_suffix(suffix)
    if here.exists():
        return here
    digest = hashlib.sha256(picture.read_bytes()).hexdigest()
    for sample in (ROOT / "samples").rglob("*" + picture.suffix):
        if sample.with_suffix(suffix).exists() and hashlib.sha256(sample.read_bytes()).hexdigest() == digest:
            return sample.with_suffix(suffix)
    return None


class Pictures:
    def __init__(self, settings, workspace_id: str, user_id: str, session_id: str):
        self.dir = settings.data_dir / "pictures" / workspace_id / user_id / session_id
        self.index = self.dir / "pictures.json"

    def all(self) -> list[dict]:
        return json.loads(self.index.read_text(encoding="utf-8")) if self.index.exists() else []

    def _add(self, path: Path, by: str):
        self.dir.mkdir(parents=True, exist_ok=True)
        items = self.all() + [{"file": str(path), "name": Path(path).name, "by": by}]
        self.index.write_text(json.dumps(items, indent=2), encoding="utf-8")

    def attach(self, source: Path, name: str | None = None) -> Path:
        """The marketer attached a picture: keep a copy with this conversation."""
        self.dir.mkdir(parents=True, exist_ok=True)
        dest = self.dir / Path(name or Path(source).name).name
        shutil.copyfile(source, dest)
        self._add(dest, "attached")
        return dest

    def made(self, path: Path):
        """The agent made a picture in this conversation."""
        self._add(Path(path), "made")

    def newest(self) -> Path | None:
        items = self.all()
        return Path(items[-1]["file"]) if items else None

    def describe(self) -> str:
        items = self.all()
        if not items:
            return "No pictures in this conversation yet."
        listed = ", ".join(f"{i['name']} ({'attached by the marketer' if i['by'] == 'attached' else 'made by you'})" for i in items)
        return f"Pictures in this conversation: {listed}. The picture tools work on the newest one, {items[-1]['name']}."
