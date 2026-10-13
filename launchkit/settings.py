import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from launchkit.harness.limits import Limits

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    model: str = _env("LAUNCHKIT_MODEL", "openai:gpt-5.4-mini")
    image_mode: str = _env("LAUNCHKIT_IMAGE", "real")
    image_model: str = _env("LAUNCHKIT_IMAGE_MODEL", "gpt-image-2")
    image_size: str = _env("LAUNCHKIT_IMAGE_SIZE", "1024x1536")
    workspaces_dir: Path = Path(_env("LAUNCHKIT_WORKSPACES_DIR", str(ROOT / "workspaces")))
    data_dir: Path = ROOT / "data"
    limits: Limits = Limits()
    budgets: dict = field(default_factory=lambda: {"rules": 1500, "task": 400, "facts": 1500, "history": 2000})


settings = Settings()
