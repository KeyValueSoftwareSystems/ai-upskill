"""route(): which models to try for one job, in order. Built in routing hands-on 1.

route(job, settings, ask=None, pick=None, skill=None) returns (job, [(model, reason), ...]):
- the job, which can change: a long_text ask that is a short question becomes short_text;
- the models to try, first choice first, each with the reason it is there: "pick", "skill", "rank N" or "fallback".
The caller tries them in that order, and moves to the next when a call fails.
"""

from launchkit.adapters.ranking import is_enabled, rank_list

SHORT_QUESTION_WORDS = 12


def route(job: str, settings, ask: str | None = None, pick: str | None = None, skill=None) -> tuple[str, list[tuple[str, str]]]:
    if job == "long_text" and ask and ask.strip().endswith("?") and len(ask.split()) <= SHORT_QUESTION_WORDS:
        job = "short_text"
    order = [(pick, "pick")] if pick else []
    pinned = dict(skill.pins).get(job) if skill is not None else None
    if pinned:
        order.append((pinned, "skill"))
    order += [(name, f"rank {i}") for i, name in enumerate(rank_list(job, settings), 1)]
    chosen, seen, skipped = [], set(), False
    for name, reason in order:
        if name in seen:
            continue
        seen.add(name)
        if not is_enabled(name, settings):
            skipped = True
            continue
        chosen.append((name, "fallback" if skipped and not chosen else reason))
    return job, chosen
