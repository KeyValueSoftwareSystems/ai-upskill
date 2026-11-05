import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from launchkit.guardrails.limits import Limits

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # Maya's pick: LAUNCHKIT_MODEL, --model or the chat page's Model field. Empty means no pick: before routing every job
    # runs on DEFAULT_MODEL; once route() is built, an empty pick lets the rank list decide.
    model: str = field(default_factory=lambda: _env("LAUNCHKIT_MODEL", ""))
    ranking: Path = field(default_factory=lambda: Path(_env("LAUNCHKIT_RANKING", str(ROOT / "launchkit" / "ranking.json"))))
    # Models switched off inside LaunchKit, comma-separated: route() skips them. The proxy itself still serves them.
    disabled_models: frozenset = field(default_factory=lambda: frozenset(m.strip() for m in _env("LAUNCHKIT_DISABLED_MODELS", "").split(",") if m.strip()))
    # 1: every model route() picks runs as a fake, for when the proxy is down. The trace still names the routed model.
    # Thinking effort for reasoning models: low, medium or high; empty leaves the model's default. A trainer demo (step 4).
    effort: str = field(default_factory=lambda: _env("LAUNCHKIT_EFFORT", ""))
    fake_models: bool = field(default_factory=lambda: _env("LAUNCHKIT_FAKE_MODELS", "") in ("1", "true", "yes"))
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
    limits: Limits = Limits()
    budgets: dict = field(default_factory=lambda: {"rules": 1500, "task": 400, "facts": 1500, "history": 2000})


DEFAULT_MODEL = "gpt-4.1-mini"  # the one model every job ran on before routing

settings = Settings()
