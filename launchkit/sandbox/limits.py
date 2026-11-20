"""How much one run of the agent's code may use, and why a run was stopped.

Stage 1 gives a run two limits: a time limit, and a cap on how much of what it printed goes back to the model.

Not built yet: stage 3. Stage 3 adds the rest, after the room watches one analysis eat the machine while Jonas's
poster waits: memory, processor, number of processes and disk, a docker_flags that turns them into `docker run`
options, and a stop_reason that says in one word why a run ended early. The room puts a number on each limit before
it builds them.

Reference page 10, Resource limits and noisy neighbours.
"""

from dataclasses import dataclass

from launchkit.tools.catalogue import todo


@dataclass(frozen=True)
class RunLimits:
    seconds: int = 30          # wall-clock time: the real time that passes, as on a clock
    output_chars: int = 4000   # how much of what the code printed goes back to the model


@todo
def docker_flags(limits: RunLimits) -> list[str]:
    """The `docker run` options that hold a container to these limits."""
    raise NotImplementedError("stage 3 builds the limits")


@todo
def stop_reason(exit_code: int | None, timed_out: bool, oom_killed: bool, output: str) -> str | None:
    """Why a run was stopped, in one word, or None when it ended on its own."""
    raise NotImplementedError("stage 3 builds the limits")
