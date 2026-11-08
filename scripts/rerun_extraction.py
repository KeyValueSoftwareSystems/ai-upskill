"""Ticket 1's live moment: rerun memory extraction on one message, several times, and show what each run saved.

    uv run python scripts/rerun_extraction.py "Cairnline's whole launch leads with 'lifetime guarantee' and it's working. Write me a Tidal headline with that same confidence."
    uv run python scripts/rerun_extraction.py --times 5 --user maya "<message>"

Each run starts from a fresh copy of the snapshot, so runs do not see each other's rows, and nothing in data/ changes.
It uses the memory manager the main agent would use: ticket 1's (capture rules, LAUNCHKIT_MEMORY_MODEL) once it is
built, Agno's default on the main model before. The main agent's reply plays no part: Agno hands the manager only the
user's message.
"""

import argparse
import re
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agno.memory import MemoryManager  # noqa: E402

from launchkit.adapters.models import model_name, resolve_model  # noqa: E402
from launchkit.memory.chat_history import session_db  # noqa: E402
from launchkit.memory.long_term import memory_changes, memory_manager, user_memories  # noqa: E402
from launchkit.settings import settings as base  # noqa: E402
from launchkit.trace import Trace  # noqa: E402

NEGATION = re.compile(r"\b(never|not|no|avoid|don't|do not|without|banned|never-say)\b", re.I)


def once(text: str, user: str) -> list[tuple[str, str]]:
    data = Path(tempfile.mkdtemp())
    shutil.copyfile(ROOT / "fixtures" / "memory-snapshot.db", data / "sessions.db")
    settings = replace(base, data_dir=data)
    trace = Trace()
    manager = memory_manager(settings, trace, resolve_model(settings, trace)) or MemoryManager(model=resolve_model(settings, trace), db=session_db(settings))
    before = user_memories(manager.db, user)
    manager.create_user_memories(message=text, user_id=user)
    changes = memory_changes(before, user_memories(manager.db, user))
    shutil.rmtree(data, ignore_errors=True)
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Rerun memory extraction on one message and print what each run saved.")
    parser.add_argument("message")
    parser.add_argument("--user", default="maya")
    parser.add_argument("--times", type=int, default=5)
    args = parser.parse_args()
    trace = Trace()
    manager = memory_manager(base, trace, resolve_model(base, trace))
    print(f"memory manager: {'ticket 1 (capture rules), ' + model_name(manager.model) if manager else 'Agno default, ' + model_name(resolve_model(base, trace))}")
    with ThreadPoolExecutor(args.times) as pool:
        runs = list(pool.map(lambda _: once(args.message, args.user), range(args.times)))
    for n, changes in enumerate(runs, 1):
        lines = [f"{change}: {text}" for change, text in changes] or ["nothing saved"]
        flags = [" ← a never-say phrase saved as a wish" if "lifetime" in line.lower() and not NEGATION.search(line) else "" for line in lines]
        for i, (line, flag) in enumerate(zip(lines, flags)):
            print(f"run {n}  {line}{flag}" if i == 0 else f"       {line}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
