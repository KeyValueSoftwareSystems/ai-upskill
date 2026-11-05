"""The rank list: launchkit/ranking.json, one list per job. Ready-made; route() reads it.

Each model on a job's list has three scores from 0 to 1 (eval, latency, cost; higher is better) and each job has its
own weights. A model's total is each score times its weight, added up. The highest total is rank 1, which is "Auto".
"""

import json
from functools import lru_cache
from pathlib import Path

JOBS = ("long_text", "short_text", "research", "memory_write", "vision")


@lru_cache(maxsize=4)
def _load(path: str, mtime: float) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))["jobs"]


def ranking(settings) -> dict:
    """The rank file as written, read again whenever it changes, so an edit needs no restart."""
    path = Path(settings.ranking)
    return _load(str(path), path.stat().st_mtime)


def total(scores: dict, weights: dict) -> float:
    return round(sum(scores[name] * weight for name, weight in weights.items()), 3)


def rank_list(job: str, settings) -> list[str]:
    """The job's models, best first: highest weighted total first."""
    entry = ranking(settings).get(job)
    if entry is None:
        raise KeyError(f"no rank list for job {job!r}; jobs: {', '.join(ranking(settings))}")
    return sorted(entry["models"], key=lambda name: total(entry["models"][name], entry["weights"]), reverse=True)


def is_enabled(name: str, settings) -> bool:
    """A model is enabled unless LAUNCHKIT_DISABLED_MODELS switches it off."""
    return name not in settings.disabled_models
