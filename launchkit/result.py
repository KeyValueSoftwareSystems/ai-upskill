from dataclasses import dataclass, field

from .spec import PosterSpec


@dataclass
class Result:
    """What every approach returns for one request."""
    spec: PosterSpec | None = None
    images: list[str] = field(default_factory=list)
    error: str | None = None
