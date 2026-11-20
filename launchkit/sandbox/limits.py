"""How much one run of the agent's code may use, and why a run was stopped.

Stage 1 gave a run a time limit and a cap on what it prints back. Stage 3 adds the rest, after the room watched one
analysis copy the table once per row in a process per processor, eat a gigabyte and every core, and Jonas's poster
wait behind it. A container with no limits isolates what the code can see, not how much it can use.

Each limit is a number the room put on the board first:

    seconds       30     wall-clock time, the real time that passes; past it the container is killed
    output_chars  4000   how much of what the code printed goes back to the model
    memory_mb     512    memory, with no swap on top; past it the kernel kills the run (out of memory)
    cpus          1      processor time: one core's worth, however many processes the code starts
    processes     64     processes and threads together, so a fork loop hits a wall instead of the machine
    disk_mb       100    /tmp, the one writable place outside /work, kept in memory at this size

The disk limit covers /tmp only. /work is a folder on the host's disk, and Docker cannot cap a folder it mounts;
counting what a run wrote there, and refusing it after the fact, is a step this stage does not take.

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
    disk_mb: int = 100


def docker_flags(limits: RunLimits) -> list[str]:
    """The `docker run` options that hold a container to these limits. Time is held by the caller, which kills the
    container by name."""
    return [
        "--memory", f"{limits.memory_mb}m", "--memory-swap", f"{limits.memory_mb}m",
        "--cpus", str(limits.cpus),
        "--pids-limit", str(limits.processes),
        "--tmpfs", f"/tmp:rw,size={limits.disk_mb}m",
    ]


# What a run prints when it runs into a limit the kernel enforces by refusing, rather than by killing.
SIGNS = {
    "processes": ("Resource temporarily unavailable", "can't start new thread"),
    "disk": ("No space left on device",),
}


def stop_reason(exit_code: int | None, timed_out: bool, oom_killed: bool, output: str) -> str | None:
    """Why a run was stopped, in one word, or None when it ended on its own."""
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
