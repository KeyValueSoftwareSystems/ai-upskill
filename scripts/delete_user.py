"""Ticket 6: delete everything LaunchKit keeps about one person, and show what still names them.

    uv run python scripts/delete_user.py agency-manager --name "Dana Whitlock"            # what it would remove; nothing written
    uv run python scripts/delete_user.py agency-manager --name "Dana Whitlock" --apply    # remove it, then search again
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from launchkit.memory.forget import delete_user, still_naming  # noqa: E402
from launchkit.settings import settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete one person from long-term memory, with a cascade.")
    parser.add_argument("user_id")
    parser.add_argument("--name", action="append", default=[], help="a name they go by, to search for after the delete")
    parser.add_argument("--apply", action="store_true", help="delete; without it nothing is written")
    args = parser.parse_args()
    print(f"Before: {args.user_id} appears in")
    for line in still_naming(settings, args.user_id, args.name):
        print(f"  {line}")
    print("\nRemoved:" if args.apply else "\nWould remove (dry run):")
    for what, count in delete_user(settings, args.user_id, args.apply):
        print(f"  {count:>4}  {what}")
    if args.apply:
        left = still_naming(settings, args.user_id, args.name)
        print("\nAfter: still names them" if left else "\nAfter: nothing names them.")
        for line in left:
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
