"""Stage 1: a tool that runs Python the agent wrote, on this conversation's files.

Not built yet. The room builds this in stage 1, after watching the agent read Breeze's results table and give two
different "cheapest channels" in two conversations, neither of them right.

What it must do. Take a piece of Python and run it as a separate process, in this conversation's workspace, so the
code can open uploads/breeze-results.csv by that name. A run has a time limit and is stopped when it passes it. What
the code printed goes back to the model cut to a set size, with a line saying how much was cut. Every file the code
wrote or changed is added to the record (launchkit/files/record.py), so the chat page shows it with the message that
asked for it. Each run is one code_run line on the trace.

Reference page 3, Why an agent runs code, and page 4, What a code tool hands back.
"""

from launchkit.sandbox.limits import RunLimits
from launchkit.tools.catalogue import Entry, todo


@todo
def run_code(code: str, label: str = "") -> str:
    """Run Python on this conversation's files and return what it printed."""
    raise NotImplementedError("stage 1 builds run_code")


def make_run_code(workspace, trace, message: str = "", limits: RunLimits | None = None) -> Entry:
    return Entry("run_code", "run Python on this conversation's files", "read", run_code)
