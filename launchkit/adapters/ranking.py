"""The rank file: which models a job may use, and in what order.

Ready-made for ticket 8. Reference: page 12, "Rank lists as data".

`launchkit/ranking.json` holds, for every job, three scores per model (quality, cost, speed, each from 0
to 1, higher is better) and the weights the job gives them. A model's total is each score times its
weight, added up. The weights are a product decision: launch copy is quality first, a one-line answer is
cost first. The file is data, so the order changes without a code change.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

JOBS = ("long_text", "short_text", "research", "memory_write", "vision")
SCORES = ("eval", "cost", "latency")


@lru_cache(maxsize=8)
def _read(path: str, modified: float) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ranking(settings) -> dict:
    """The rank file as a dict, re-read when the file changes."""
    path = Path(settings.ranking)
    return _read(str(path), path.stat().st_mtime)


def total(scores: dict[str, float], weights: dict[str, float]) -> float:
    """One model's total for one job: each score times its weight, added up."""
    return sum(float(scores.get(k, 0.0)) * float(weights.get(k, 0.0)) for k in SCORES)


def is_enabled(model: str, settings) -> bool:
    """A model is off when it is named in LAUNCHKIT_DISABLED_MODELS. That is how the room simulates an outage."""
    return model not in settings.disabled_models


def rank_list(job: str, settings) -> list[str]:
    """The job's models, best total first, with the disabled ones left out."""
    entry = ranking(settings)["jobs"][job]
    scored = sorted(entry["models"].items(), key=lambda item: total(item[1], entry["weights"]), reverse=True)
    return [name for name, _ in scored if is_enabled(name, settings)]


def job_table(settings) -> dict:
    """Every job with its weights and its models in rank order, with scores and totals. For `launchkit models` and GET /models."""
    data = ranking(settings)
    out = {}
    for job, entry in data["jobs"].items():
        rows = [
            {"model": name, **{k: scores.get(k) for k in SCORES}, "total": round(total(scores, entry["weights"]), 3), "enabled": is_enabled(name, settings)}
            for name, scores in entry["models"].items()
        ]
        rows.sort(key=lambda r: r["total"], reverse=True)
        out[job] = {"about": entry.get("about", ""), "weights": entry["weights"], "models": rows}
    return {"about": data.get("about", ""), "jobs": out}
