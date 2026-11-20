"""Stage 1: a tool that runs Python the agent wrote, on this conversation's files.

The model is bad at arithmetic by eye: asked for the cheapest channel in Breeze's results, it gave two different
answers in two conversations, and neither matched the sums. run_code lets it write the sums as code instead, run
them, and answer from what the code printed.

The code runs as a separate process, in this conversation's workspace, so it opens uploads/breeze-results.csv by
that name. A run has a time limit; past it, the process and everything it started are killed and the agent is told
why. What it printed goes back cut to a set size, with a line saying how much was cut. Every file it wrote or changed
goes into the record, so the chat page shows it with the message that asked for it.

What this stage does not do, on purpose: the process inherits the server's environment, keys included, and can open
any file the server can. Stage 2 is that failure.

Reference page 3, Why an agent runs code, and page 4, What a code tool hands back.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from launchkit.files.record import Record
from launchkit.sandbox import Ran
from launchkit.sandbox.limits import RunLimits
from launchkit.tools.catalogue import Entry

NOT_ARTIFACTS = {"artifacts.jsonl", "pictures.json"}  # the workspace's own bookkeeping, never something the code made

NOTE = (
    "pick me to work out figures, totals, averages, rankings or a table from a file in this conversation, such as "
    "uploads/breeze-results.csv, by writing Python that reads the file and prints the answer; also to make files with "
    "code, such as a chart or every size of a picture. The code runs in this conversation's folder. Python's standard "
    "library, numpy and Pillow are there. label names what the run makes, such as cost-per-signup"
)


def snapshot(root: Path) -> dict[str, tuple[int, int]]:
    found = {}
    for path in Path(root).rglob("*"):
        if path.is_file() and path.name not in NOT_ARTIFACTS:
            stat = path.stat()
            found[path.relative_to(root).as_posix()] = (stat.st_mtime_ns, stat.st_size)
    return found


def written_since(root: Path, before: dict) -> list[str]:
    """Files that are new, or changed, since the snapshot."""
    return sorted(path for path, mark in snapshot(root).items() if before.get(path) != mark)


def cut(output: str, limit: int) -> str:
    if len(output) <= limit:
        return output
    return output[:limit] + f"\n[cut: {len(output) - limit} more characters were printed and are not shown]"


def run_in_process(root: Path, code: str, limits: RunLimits) -> Ran:
    """Python in a separate process, in `root`. Past the time limit the whole process group is killed, so nothing the
    code started keeps running."""
    started = time.monotonic()
    process = subprocess.Popen(
        [sys.executable, "-I", "-c", code], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=limits.seconds)
        return Ran(process.returncode, output, None, time.monotonic() - started)
    except subprocess.TimeoutExpired:
        if hasattr(os, "killpg"):
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        output, _ = process.communicate()
        return Ran(None, output or "", "time", time.monotonic() - started)


def make_run_code(workspace, trace, message: str = "", limits: RunLimits | None = None) -> Entry:
    limits = limits or RunLimits()
    record = Record(workspace.root)
    reasons = {"time": f"the run went past its time limit of {limits.seconds} seconds"}

    def run_code(code: str, label: str = "") -> str:
        """Run Python on this conversation's files and return what it printed."""
        workspace.root.mkdir(parents=True, exist_ok=True)
        before = snapshot(workspace.root)
        ran = run_in_process(workspace.root, code, limits)
        files = written_since(workspace.root, before)
        for path in files:
            record.add(Path(path), "run_code", message)
        shown = cut(ran.output, limits.output_chars)
        trace.code_run(code, ran.exit_code, ran.stopped, ran.seconds, len(shown), files, label)
        head = f"Stopped: {reasons.get(ran.stopped, ran.stopped)}." if ran.stopped else f"Exit code {ran.exit_code}, after {ran.seconds:.1f} s."
        tail = "Files written: " + ", ".join(files) if files else "No files written."
        return f"{head}\n{shown.rstrip()}\n{tail}"

    return Entry("run_code", NOTE, "read", run_code)
