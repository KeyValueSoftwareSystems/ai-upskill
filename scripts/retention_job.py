"""Ticket 5: the retention job. Run it on a schedule, never per run:

    uv run python scripts/retention_job.py --days 90               # what it would do; nothing written
    uv run python scripts/retention_job.py --days 90 --apply       # prune, then Summarize whoever still has more than 100 rows
    # cron, every night at 03:00:  0 3 * * *  cd /path/to/launchkit && uv run python scripts/retention_job.py --days 90 --apply
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from launchkit.adapters.models import resolve_model  # noqa: E402
from launchkit.memory.long_term import memory_manager  # noqa: E402
from launchkit.memory.retention import retain  # noqa: E402
from launchkit.settings import settings  # noqa: E402
from launchkit.trace import Trace  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune long-term memory by age, then Summarize what is left.")
    parser.add_argument("--days", type=int, required=True, help="keep rows updated in the last N days")
    parser.add_argument("--summarise-over", type=int, default=100, help="fold a person's rows into one when more than this many remain")
    parser.add_argument("--apply", action="store_true", help="write the changes; without it nothing is written")
    args = parser.parse_args()
    trace = Trace()
    manager = memory_manager(settings, trace, resolve_model(settings, trace))
    print(f"{'person':<16}{'rows':>6}{'tokens':>8}{'pruned':>8}{'left':>6}{'tokens':>8}" + ("" if args.apply else "   (dry run: nothing written)"))
    for r in retain(manager, args.days, args.summarise_over, args.apply):
        print(f"{r['user']:<16}{r['before']:>6}{r['tokens_before']:>8}{r['pruned']:>8}{r['after']:>6}{r['tokens_after']:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
