"""Routing: which model does a job, and what happens when that model is down.

Slot for build C, ticket 8, and the second fork. Reference: page 13, "Who decides", and page 14, "When a
model fails".

Two functions. `route` answers "which models, in what order" before any call is made. `on_failure`
answers "and now what" after a call has failed. `Jobs` in jobs.py does the calling; it only asks these
two questions.

As memory shipped there was one setting, `LAUNCHKIT_MODEL`, and every job used it. That is what the
placeholders do.
"""

from __future__ import annotations

from launchkit.settings import DEFAULT_MODEL


def route(job: str, settings, ask: str | None = None, pick: str | None = None, skill: str | None = None) -> tuple[str, list[tuple[str, str]]]:
    """The job to run and the models to try for it, in order, each with the reason it is on the list.

    `pick` is a model the person chose for this turn (the Model box, or --model). `skill` is a model a
    skill pins for this job with a `Model: <job> = <model>` line. `ask` is the person's message, for the
    one job the code cannot name: the main reply is `long_text` unless the ask is a short question, and
    then it is `short_text`.

    Build C fills this in: the pick first (for the main jobs), then the skill's pin, then the rank list
    from ranking.json with disabled models left out, reasons "pick", "skill", "rank 1", "rank 2", ...
    The placeholder gives every job the one configured model.
    """
    return job, [(pick or settings.model or DEFAULT_MODEL, "the one setting")]


def on_failure(job: str, tried: list[str], remaining: list[str], error: Exception) -> str | None:
    """The model to try next after `tried[-1]` failed, or None to stop with a clear error.

    Build C decides this at the second fork. Path A: the next model on the list, so the launch carries
    on and the trace says "fallback". Path B: the same model once more, then None, so the run stops with
    an error the person can read. The placeholder stops at once.
    """
    return None
