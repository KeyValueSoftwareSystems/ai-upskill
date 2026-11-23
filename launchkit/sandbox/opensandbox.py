"""The hands-on: run the agent's code in an OpenSandbox sandbox, with limits.

The ready-made runner in local.py starts the code as a child of the server. On the chat page, the code Jonas's agent
wrote to tidy his results printed LaunchKit's keys and listed Harbor's folder, and `fake:runaway` took every core
and a gigabyte of memory while Jonas's poster waited. Turning off a file tool does not take away the ability to read
files, because code can open them itself. So the code runs somewhere that cannot see them, with a budget it cannot
exceed.

One sandbox per run. run_in_sandbox asks the OpenSandbox server (engine.py) for a new sandbox, runs the code in it,
and destroys it, whatever happened. The sandbox:

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
import shlex
import time
from datetime import timedelta

from launchkit.files.workspace import Workspace
from launchkit.sandbox import Ran, engine
from launchkit.sandbox.limits import RunLimits, stop_reason

# An empty environment: env -i drops even what the image set, and only what Python needs is put back.
CLEAN_ENV = ["env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/tmp", "MPLCONFIGDIR=/tmp", "LANG=C.UTF-8"]


def sandbox_user() -> tuple[int, int]:
    """The host's own user and group, or 10001 when the host user is root or has none. Never root."""
    if hasattr(os, "getuid") and os.getuid() != 0:
        return os.getuid(), os.getgid()
    return 10001, 10001


def oom_kills(sandbox) -> int:
    """How many times the kernel has killed a process in this sandbox for memory. 0 when it cannot be read: a run
    that used up the process limit leaves no room to start `cat`."""
    try:
        execution = sandbox.commands.run("cat /sys/fs/cgroup/memory.events")
        text = "\n".join(m.text for m in execution.logs.stdout)
        counts = dict(line.split() for line in text.splitlines() if len(line.split()) == 2)
        return int(counts.get("oom_kill", 0))
    except Exception:
        return 0


def run_in_sandbox(workspace: Workspace, code: str, limits: RunLimits) -> Ran:
    """Run `code` with Python in a new sandbox that sees only this conversation, and give back what happened."""
    from opensandbox.exceptions import SandboxException
    from opensandbox.models.execd import RunCommandOpts
    from opensandbox.models.sandboxes import Host, NetworkPolicy, Volume
    from opensandbox.sync.sandbox import SandboxSync

    uid, gid = sandbox_user()
    sandbox = SandboxSync.create(
        engine.IMAGE,
        connection_config=engine.connection(),
        timeout=timedelta(seconds=limits.seconds + 60),   # a backstop: the server ends it even if LaunchKit never does
        env={},
        metadata=engine.labels(workspace.brand, workspace.conversation),
        resource={"cpu": str(limits.cpus), "memory": f"{limits.memory_mb}Mi"},
        network_policy=NetworkPolicy(default_action="deny", egress=[]),
        volumes=[
            Volume(name="work", host=Host(path=str(workspace.root.resolve())), mount_path="/work", read_only=False),
            Volume(name="brand", host=Host(path=str(workspace.shared.resolve())), mount_path="/brand", read_only=True),
        ],
    )
    started = time.monotonic()
    try:
        try:
            execution = sandbox.commands.run(
                shlex.join([*CLEAN_ENV, "python", "-I", "-c", code]),
                opts=RunCommandOpts(working_directory="/work", timeout=timedelta(seconds=limits.seconds), uid=uid, gid=gid),
            )
        except SandboxException:   # the sandbox went away mid-run: Stop killed it, or the machine did
            return Ran(None, "", "killed", time.monotonic() - started)
        seconds = time.monotonic() - started
        messages = sorted(execution.logs.stdout + execution.logs.stderr, key=lambda m: m.timestamp)
        output = "\n".join(m.text.rstrip("\n") for m in messages)
        timed_out = seconds >= limits.seconds - 0.5
        exit_code = None if timed_out else execution.exit_code
        oom_killed = bool(exit_code) and oom_kills(sandbox) > 0
        return Ran(exit_code, output, stop_reason(exit_code, timed_out, oom_killed, output), seconds)
    finally:
        try:
            sandbox.kill()
        finally:
            sandbox.close()
