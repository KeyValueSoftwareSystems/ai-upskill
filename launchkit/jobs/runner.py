"""Stage 4: start a job apart from the page, stop it, and one job at a time per conversation.

Built in stage 4, with the record in record.py.

start_job(settings, body, run_turn) starts the turn on a thread of its own and returns at once, so closing the page
does not stop it. The turn's events go into the job's log, not to the page that asked. When the conversation already
has a job running, the new message is not started: it is added to that job's waiting list, the job's log says so,
and start_job returns {"job_id": <the running job>, "waiting": True}. When a job ends, its waiting messages start, in
order, as the next jobs. The room chose to queue a second message, not to refuse it or interrupt the job.

stop_job(settings, job_id) marks the job as stopping, kills every container this conversation has running, and the
turn ends at its next tool call: the stop hook raises Agno's StopAgentRun. The job's status ends as stopped. The
containers are found by name with a full match, not by "starts with", for the same reason as Session 4's t3a9-old:
lk-harbor-k7c1- is also the start of lk-harbor-k7c1-old-....

Two events are the runner's own, because the page that is ready-made reads them. A message that has to wait adds
{"type": "waiting", "text": ...} to the running job's log. When a turn ends, the runner adds one last event,
{"type": "end", "status": <the job's final status>}, which tells the page the job is over.

What this stage does not do, on purpose: survive a restart. A job lives on a thread of this server; restart the
server and the record still says running, with nothing running it. Stage 5 is that failure.

Reference page 12, A turn that outlives its request, and page 13, Stopping a run.
"""

import re
import shutil
import subprocess
import threading
import time

from agno.exceptions import StopAgentRun

from launchkit.jobs.record import ACTIVE, LOCK, append_event, create, current, load, save
from launchkit.sandbox.engine import name_prefix

WAITS = "This message waits until the job that is running now finishes, then runs on its own. It is not lost."


def start_job(settings, body: dict, run_turn) -> dict:
    """Start this message as a job, or queue it behind the job already running in its conversation."""
    with LOCK:
        running = current(settings, body["workspace_id"], body.get("session_id") or "")
        if running is not None:
            running.waiting.append(dict(body))
            save(settings, running)
            append_event(settings, running.id, {"type": "waiting", "text": WAITS})
            return {"job_id": running.id, "waiting": True}
        job = create(settings, body)
    threading.Thread(target=run_job, args=(settings, job, run_turn), daemon=True, name=f"job-{job.id}").start()
    return {"job_id": job.id, "waiting": False}


def stop_hook(settings, job_id: str):
    """An Agno tool hook: before each tool call, end the run if the job has been asked to stop."""

    def hook(function_name: str, function_call, arguments: dict):
        if load(settings, job_id).status == "stopping":
            raise StopAgentRun("Stopped by the marketer")
        return function_call(**arguments)

    return hook


def run_job(settings, job, run_turn, hooks=()) -> None:
    """Run one job's turn to the end, write how it ended, then start whatever was waiting for it."""
    emit = lambda event: append_event(settings, job.id, event)  # noqa: E731
    final = "done"
    try:
        run_turn({**job.body, "job_id": job.id}, emit, [stop_hook(settings, job.id), *hooks])
    except StopAgentRun:
        final = "stopped"
    except Exception as error:
        emit({"type": "error", "kind": type(error).__name__, "message": str(error)})
        final = "failed"
    with LOCK:
        ended = load(settings, job.id)
        ended.status = "stopped" if ended.status == "stopping" else final
        ended.ended = time.time()
        waiting, ended.waiting = ended.waiting, []
        save(settings, ended)
        emit({"type": "end", "status": ended.status})
        for body in waiting:
            start_job(settings, body, run_turn)


def stop_job(settings, job_id: str):
    """Mark the job as stopping and kill what it started. It ends within a few seconds."""
    with LOCK:
        job = load(settings, job_id)
        if job.status not in ACTIVE:
            return job
        job.status = "stopping"
        save(settings, job)
    append_event(settings, job_id, {"type": "trace", "kind": "stop", "line": "stop      Stop pressed: the job ends at its next step, and its sandbox is killed"})
    kill_containers(job.brand, job.conversation)
    return job


def kill_containers(brand: str, conversation: str) -> list[str]:
    """Kill every container this conversation's code is running in, found by its full name."""
    if shutil.which("docker") is None:
        return []
    names = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True).stdout.split()
    mine = [n for n in names if re.fullmatch(re.escape(name_prefix(brand, conversation)) + r"[0-9a-f]{6}", n)]
    if mine:
        subprocess.run(["docker", "kill", *mine], capture_output=True)
    return mine
