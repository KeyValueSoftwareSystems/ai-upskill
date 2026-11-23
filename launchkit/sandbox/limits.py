"""Ready-made: how much one run of the agent's code may use, and why a run was stopped.

Each limit is a number the room puts on the board before the hands-on:

    seconds       30     wall-clock time, the real time that passes; past it the run is stopped
    output_chars  4000   how much of what the code printed goes back to the model
    memory_mb     512    memory; past it the kernel kills the run (out of memory)
    cpus          1      processor time: one core's worth, however many processes the code starts
    processes     64     processes and threads together, so a fork loop hits a wall instead of the machine

Where each one is enforced is the hands-on's question. Time, memory and processor go with each sandbox: the request
that creates it carries them. The process limit is a setting of the sandbox server (pids_limit in
data/sandbox.toml), one number for every sandbox it starts, so a run cannot ask for more or less.

Two gaps the room discusses rather than builds. OpenSandbox's Docker runtime sets a memory limit and leaves swap on,
so a run can use about as much again in swap, slowly, before the kernel kills it. And nothing caps how much a run
writes into /work, which is a folder on the host's disk.

Reference page 10, Resource limits and noisy neighbours.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RunLimits:
    seconds: int = 30
    output_chars: int = 4000
    memory_mb: int = 512
    cpus: float = 1.0
    processes: int = 64


# What a run prints when it runs into a limit the kernel enforces by refusing, rather than by killing.
SIGNS = {
    "processes": ("Resource temporarily unavailable", "can't start new thread"),
}


def stop_reason(exit_code: int | None, timed_out: bool, oom_killed: bool, output: str) -> str | None:
    """Why a run was stopped, in one word ("memory", "time", "processes", "killed"), or None when it ended on its own."""
    if oom_killed:
        return "memory"
    if timed_out:
        return "time"
    if exit_code:
        for reason, signs in SIGNS.items():
            if any(sign in output for sign in signs):
                return reason
        if exit_code in (137, -9):
            return "killed"
    return None
