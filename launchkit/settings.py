import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from launchkit.guardrails.limits import Limits

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# The model every job used before routing existed, and the one the rank file falls back to.
DEFAULT_MODEL = "gpt-4.1-mini"


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # Empty means "let the rank list decide". A model here is the person's pick for the main jobs.
    model: str = field(default_factory=lambda: _env("LAUNCHKIT_MODEL", ""))
    image_mode: str = field(default_factory=lambda: _env("LAUNCHKIT_IMAGE", "real"))
    image_model: str = field(default_factory=lambda: _env("LAUNCHKIT_IMAGE_MODEL", "gpt-image-2"))
    image_size: str = field(default_factory=lambda: _env("LAUNCHKIT_IMAGE_SIZE", "1024x1536"))
    image_quality: str = field(default_factory=lambda: _env("LAUNCHKIT_IMAGE_QUALITY", "medium"))
    timeout: int = field(default_factory=lambda: int(_env("LAUNCHKIT_TIMEOUT", "90")))
    board: str = field(default_factory=lambda: _env("LAUNCHKIT_BOARD", "notion"))
    search: str = field(default_factory=lambda: _env("LAUNCHKIT_SEARCH", "web"))
    search_delay: float = field(default_factory=lambda: float(_env("LAUNCHKIT_SEARCH_DELAY", "0")))
    workspaces_dir: Path = field(default_factory=lambda: Path(_env("LAUNCHKIT_WORKSPACES_DIR", str(ROOT / "workspaces"))))
    data_dir: Path = ROOT / "data"
    ranking: Path = field(default_factory=lambda: Path(_env("LAUNCHKIT_RANKING", str(ROOT / "launchkit" / "ranking.json"))))
    # Models switched off by hand, comma-separated. How the room simulates a provider outage.
    disabled_models: tuple = field(default_factory=lambda: tuple(m.strip() for m in _env("LAUNCHKIT_DISABLED_MODELS", "").split(",") if m.strip()))
    # Models that are "down", comma-separated: still on the rank list, but every call to them fails. How the room
    # acts out an outage and watches on_failure decide.
    down_models: tuple = field(default_factory=lambda: tuple(m.strip() for m in _env("LAUNCHKIT_DOWN_MODELS", "").split(",") if m.strip()))
    limits: Limits = Limits()
    budgets: dict = field(default_factory=lambda: {"rules": 1500, "task": 400, "brand_facts": 400, "memory": 1500, "facts": 1500, "history": 2000})


settings = Settings()
