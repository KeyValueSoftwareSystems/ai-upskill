"""Ready-made: run the agent's code as a separate process on this machine. No sandbox.

This is where run_code starts the session. The code runs as a child of the server, in the conversation's folder, so
it opens uploads/breeze-results.csv by that name. A run has a time limit; past it, the process and everything it
started are killed, because a new session puts them all in one process group.

What it does not do, on purpose: the child inherits the server's environment, keys included, and it can open any
file the server can, every brand's folder included. On the chat page, the code Jonas's agent wrote to tidy his
results printed LaunchKit's keys and listed Harbor's folder. The hands-on replaces this with an OpenSandbox sandbox
(launchkit/sandbox/opensandbox.py).

Stop finds these processes through RUNNING, by conversation, and kills their process groups.

Reference page 3, Why an agent runs code, and page 5, What running code can reach.
"""

import os
import signal
import subprocess
import sys
import threading
import time

from launchkit.files.workspace import Workspace
from launchkit.sandbox import Ran
from launchkit.sandbox.limits import RunLimits

RUNNING: dict[tuple[str, str], set[int]] = {}   # (brand, conversation) -> process group ids running now
_LOCK = threading.Lock()


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL) if hasattr(os, "killpg") else os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_here(workspace: Workspace, code: str, limits: RunLimits) -> Ran:
    """Python in a separate process, in the conversation's folder. Past the time limit the whole group is killed."""
    key = (workspace.brand, workspace.conversation)
    started = time.monotonic()
    process = subprocess.Popen(
        [sys.executable, "-I", "-c", code], cwd=workspace.root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, start_new_session=True,
    )
    with _LOCK:
        RUNNING.setdefault(key, set()).add(process.pid)
    try:
        output, _ = process.communicate(timeout=limits.seconds)
        return Ran(process.returncode, output, "killed" if process.returncode == -9 else None, time.monotonic() - started)
    except subprocess.TimeoutExpired:
        _kill_group(process.pid)
        output, _ = process.communicate()
        return Ran(None, output or "", "time", time.monotonic() - started)
    finally:
        with _LOCK:
            RUNNING.get(key, set()).discard(process.pid)


def kill_here(brand: str, conversation: str) -> list[int]:
    """Kill every process group this conversation's code is running in. Stop calls it."""
    with _LOCK:
        pids = list(RUNNING.get((brand, conversation), ()))
    for pid in pids:
        _kill_group(pid)
    return pids
