"""route(): which models to try for one job, in order. Routing hands-on 1 builds it.

A slot until it is built: until then every job runs on one model, LAUNCHKIT_MODEL (or the default).

route(job, settings, ask=None, pick=None, skill=None) returns (job, [(model, reason), ...]):
- the job, which can change: a long_text ask that is a short question becomes short_text;
- the models to try, first choice first, each with the reason it is there: "pick", "skill", "rank N" or "fallback".
The caller tries them in that order, and moves to the next when a call fails.
"""


def todo(fn):
    """Marks a slot. Nothing calls it until it is built."""
    fn.todo = True
    return fn


@todo
def route(job: str, settings, ask: str | None = None, pick: str | None = None, skill=None) -> tuple[str, list[tuple[str, str]]]:
    raise NotImplementedError("routing hands-on 1 builds this")
