"""The hands-on: run the agent's code in an OpenSandbox sandbox, with limits.

Not built yet. The room builds it after watching fake:peek and fake:runaway (docs/run-1.md).

The ready-made runner in local.py starts the code as a child of the server. On the chat page, the code Jonas's agent
wrote to tidy his results printed LaunchKit's keys and listed Harbor's folder, and `fake:runaway` took every core
and a gigabyte of memory while Jonas's poster waited. Turning off a file tool does not take away the ability to read
files, because code can open them itself. So the code runs somewhere that cannot see them, with a budget it cannot
exceed.

What it must do. One sandbox per run. run_in_sandbox asks the OpenSandbox server (engine.py) for a new sandbox,
runs the code in it, and destroys it, whatever happened. The sandbox:

    image        engine.IMAGE: Python with pandas, matplotlib, numpy and Pillow
    /work        this conversation's folder, read and write; the code starts there
    /brand       the brand's own files, read only
    env          nothing from the server; Python starts under `env -i`, so not even what the image sets
    network      a deny-all policy, enforced by the egress sidecar on every packet
    user         the host's own user, never root, so files the code writes belong to the person running LaunchKit
    limits       the request carries memory and processor; the command carries the time limit; the server holds
                 every sandbox to the process limit
    metadata     engine.labels(brand, conversation), so Stop can find it

After a run that failed, the sandbox's own cgroup says whether the kernel killed it for memory: the oom_kill line of
/sys/fs/cgroup/memory.events. The exit code alone does not say, and the sandbox has to be asked before it is
destroyed. limits.stop_reason turns that into one word for the trace and the agent.

Reference page 6, How strong the isolation is, page 9, The network, and page 10, Resource limits.
"""

import os

from launchkit.files.workspace import Workspace
from launchkit.sandbox import Ran
from launchkit.sandbox.limits import RunLimits
from launchkit.tools.catalogue import todo

# An empty environment: env -i drops even what the image set, and only what Python needs is put back.
CLEAN_ENV = ["env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/tmp", "MPLCONFIGDIR=/tmp", "LANG=C.UTF-8"]


def sandbox_user() -> tuple[int, int]:
    """The host's own user and group, or 10001 when the host user is root or has none. Never root."""
    if hasattr(os, "getuid") and os.getuid() != 0:
        return os.getuid(), os.getgid()
    return 10001, 10001


@todo
def oom_kills(sandbox) -> int:
    """How many times the kernel has killed a process in this sandbox for memory: the oom_kill line of
    /sys/fs/cgroup/memory.events, read inside the sandbox. 0 when it cannot be read."""
    raise NotImplementedError("the hands-on builds oom_kills")


@todo
def run_in_sandbox(workspace: Workspace, code: str, limits: RunLimits) -> Ran:
    """Run `code` with Python in a new sandbox that sees only this conversation, and give back what happened."""
    raise NotImplementedError("the hands-on builds run_in_sandbox")
