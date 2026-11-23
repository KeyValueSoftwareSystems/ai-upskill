"""Where the agent's own code runs (Session 5).

run_code (launchkit/tools/run_code.py) hands a piece of Python to one of two places. The ready-made local.py runs
it as a separate process on this machine, with no sandbox. The hands-on, opensandbox.py, runs it in an OpenSandbox
sandbox, with the limits in limits.py; engine.py is the plumbing around the sandbox server. Both give back the same
thing: a Ran.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Ran:
    """What one run of the agent's code came back with."""

    exit_code: int | None   # None when the run never finished on its own
    output: str             # what it printed, stdout and stderr together, not yet cut to size
    stopped: str | None     # why it was stopped, in one word ("time", "memory", "processes", "disk", "killed"), or None
    seconds: float
