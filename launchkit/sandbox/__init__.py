"""Where the agent's own code runs (Session 5).

run_code (launchkit/tools/run_code.py) hands a piece of Python to one of two places. Stage 1 runs it as a separate
process on this machine. From stage 2 it runs in a throwaway container (container.py), with the limits in limits.py
from stage 3. Both give back the same thing: a Ran.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Ran:
    """What one run of the agent's code came back with."""

    exit_code: int | None   # None when the run never finished on its own
    output: str             # what it printed, stdout and stderr together, not yet cut to size
    stopped: str | None     # why it was stopped, in one word ("time", "memory", "processes", "disk", "killed"), or None
    seconds: float
