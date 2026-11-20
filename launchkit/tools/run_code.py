"""Stage 1: a tool that runs Python the agent wrote, on this conversation's files.

The model is bad at arithmetic by eye: asked for the cheapest channel in Breeze's results, it gave two different
answers in two conversations, and neither matched the sums. run_code lets it write the sums as code instead, run
them, and answer from what the code printed.

Stage 2 moved the run into a throwaway container (launchkit/sandbox/container.py) that sees only this conversation's
workspace, at /work, and the brand's own files, read only, at /brand. The code still opens
uploads/breeze-results.csv by that name. A run has a time limit; past it, the container and everything in it are
killed and the agent is told why. Without Docker the code does not run at all: the tool fails closed. What it printed goes back cut to a set size, with a line saying how much was cut. Every file it wrote or changed
goes into the record, so the chat page shows it with the message that asked for it.

What stage 2 does not do, on purpose: limit memory, processor, processes or disk. Stage 3 is that failure.

Reference page 3, Why an agent runs code, and page 4, What a code tool hands back.
"""

from pathlib import Path

from launchkit.files.record import Record
from launchkit.sandbox.container import run_in_container
from launchkit.sandbox.engine import docker_problem
from launchkit.sandbox.limits import RunLimits
from launchkit.tools.catalogue import Entry

NOT_ARTIFACTS = {"artifacts.jsonl", "pictures.json"}  # the workspace's own bookkeeping, never something the code made

NOTE = (
    "pick me to work out figures, totals, averages, rankings or a table from a file in this conversation, such as "
    "uploads/breeze-results.csv, by writing Python that reads the file and prints the answer; also to make files with "
    "code, such as a chart or every size of a picture. The code runs in a sandbox, in this conversation's folder at "
    "/work, with the brand's own files read-only at /brand. pandas, matplotlib, numpy and Pillow are there; there is "
    "no internet. label names what the run makes, such as cost-per-signup"
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


def make_run_code(workspace, trace, message: str = "", limits: RunLimits | None = None) -> Entry:
    limits = limits or RunLimits()
    record = Record(workspace.root)
    reasons = {"time": f"the run went past its time limit of {limits.seconds} seconds"}

    def run_code(code: str, label: str = "") -> str:
        """Run Python on this conversation's files and return what it printed."""
        workspace.root.mkdir(parents=True, exist_ok=True)
        problem = docker_problem()
        if problem:  # fail closed: without the sandbox the code does not run at all, rather than run unguarded
            trace.refused("run_code", f"no sandbox: {problem}")
            return f"The code did not run: the sandbox is not available ({problem})."
        before = snapshot(workspace.root)
        ran = run_in_container(workspace, code, limits)
        files = written_since(workspace.root, before)
        for path in files:
            record.add(Path(path), "run_code", message)
        shown = cut(ran.output, limits.output_chars)
        trace.code_run(code, ran.exit_code, ran.stopped, ran.seconds, len(shown), files, label)
        head = f"Stopped: {reasons.get(ran.stopped, ran.stopped)}." if ran.stopped else f"Exit code {ran.exit_code}, after {ran.seconds:.1f} s."
        tail = "Files written: " + ", ".join(files) if files else "No files written."
        return f"{head}\n{shown.rstrip()}\n{tail}"

    return Entry("run_code", NOTE, "read", run_code)
