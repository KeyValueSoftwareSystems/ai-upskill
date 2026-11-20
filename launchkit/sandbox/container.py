"""Stage 2: run the agent's code in a throwaway container.

Stage 1's process could read every key the server holds and open every brand's files: on the chat page, the code
Jonas's agent wrote to tidy his results printed LaunchKit's keys and listed Harbor's folder. Turning off a file tool
does not take away the ability to read files, because code can open them itself. So the code runs somewhere that
cannot see them at all.

One `docker run` per run, from the image in launchkit/sandbox/engine.py, that sees only what this conversation may
see:

    /work     this conversation's workspace, read and write, and the folder the code starts in
    /brand    the brand's own files, read only
    nothing   no environment variables from the server, no network, a user that is not root, a read-only root disk
              (with /tmp, in memory, as the one other place to write), no Linux capabilities, no way to gain any

The container is named after its conversation (engine.container_name), lives for one run, and is removed after it.
Past the time limit it is killed by that name.

Reference page 6, How strong the isolation is, and page 7, What running code can reach.
"""

import os
import subprocess
import time

from launchkit.files.workspace import Workspace
from launchkit.sandbox import Ran
from launchkit.sandbox.engine import IMAGE, container_name
from launchkit.sandbox.limits import RunLimits


def sandbox_user() -> str:
    """The host's own user, so files the code writes in /work belong to the person running LaunchKit. Never root."""
    if hasattr(os, "getuid") and os.getuid() != 0:
        return f"{os.getuid()}:{os.getgid()}"
    return "10001:10001"


def run_in_container(workspace: Workspace, code: str, limits: RunLimits) -> Ran:
    """Run `code` with Python in a new container that sees only this conversation, and give back what happened."""
    name = container_name(workspace.brand, workspace.conversation)
    command = [
        "docker", "run", "--rm", "--name", name,
        "--network", "none",
        "--user", sandbox_user(),
        "--read-only", "--tmpfs", "/tmp",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "-v", f"{workspace.root.resolve()}:/work",
        "-v", f"{workspace.shared.resolve()}:/brand:ro",
        "-w", "/work",
        # An empty environment: env -i drops even what the image set, and only what Python needs is put back.
        IMAGE, "env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/tmp", "MPLCONFIGDIR=/tmp", "LANG=C.UTF-8",
        "python", "-I", "-c", code,
    ]
    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        output, _ = process.communicate(timeout=limits.seconds)
        return Ran(process.returncode, output, None, time.monotonic() - started)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", name], capture_output=True)
        output, _ = process.communicate()
        return Ran(None, output or "", "time", time.monotonic() - started)
