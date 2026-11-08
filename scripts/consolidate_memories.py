"""Ticket 1: run Agno's Summarize strategy on one person's memories and print the rows before and after.

    uv run python scripts/consolidate_memories.py maya --match navy     # the eleven navy rows, folded; nothing written
    uv run python scripts/consolidate_memories.py maya --apply          # every row of Maya's, replaced by the summary

Without --apply nothing is written. Summarize folds every row it is given into one row and keeps every fact in them,
wrong ones included: it is a cleanup for duplicates, not a filter.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agno.memory.strategies.summarize import SummarizeStrategy  # noqa: E402
from agno.memory.strategies.types import MemoryOptimizationStrategyType  # noqa: E402

from launchkit.adapters.models import resolve_model  # noqa: E402
from launchkit.agents.prompt import approx_tokens  # noqa: E402
from launchkit.memory.long_term import memory_manager, user_memories  # noqa: E402
from launchkit.settings import settings  # noqa: E402
from launchkit.trace import Trace  # noqa: E402


def show(title: str, rows) -> None:
    print(f"\n{title}: {len(rows)} rows, about {approx_tokens(' '.join(m.memory for m in rows))} tokens")
    for m in rows:
        print(f"  - {m.memory}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("user")
    parser.add_argument("--match", help="only the rows that contain this text (case does not matter)")
    parser.add_argument("--apply", action="store_true", help="write the result (only without --match)")
    args = parser.parse_args()
    trace = Trace()
    manager = memory_manager(settings, trace, resolve_model(settings, trace))
    rows = user_memories(manager.db, args.user)
    if args.match:
        rows = [m for m in rows if args.match.lower() in m.memory.lower()]
    show("before", rows)
    if not rows:
        return 0
    if args.match:
        after = SummarizeStrategy().optimize(memories=rows, model=manager.get_model())
    else:
        after = manager.optimize_memories(user_id=args.user, strategy=MemoryOptimizationStrategyType.SUMMARIZE, apply=args.apply)
    show("after" + (" (written)" if args.apply and not args.match else " (not written)"), after)
    return 0


if __name__ == "__main__":
    sys.exit(main())
