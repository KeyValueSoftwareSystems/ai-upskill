"""Ready-made: start a job apart from the page, stop it, and one job at a time per conversation.

Ready-made, with the record in record.py and the steps in steps.py. The room runs it live and discusses it.

start_job(settings, body, run_turn) starts the turn on a thread of its own and returns at once, so closing the page
does not stop it. The turn's events go into the job's log, not to the page that asked. When the conversation already
has a job running, the new message is not started: it is added to that job's waiting list, the job's log says so,
and start_job returns {"job_id": <the running job>, "waiting": True}. When a job ends, its waiting messages start, in
order, as the next jobs. The room chose to queue a second message, not to refuse it or interrupt the job.

stop_job(settings, job_id) marks the job as stopping, kills everything this conversation's code is running in, and
the turn ends at its next tool call: the stop hook raises Agno's StopAgentRun. The job's status ends as stopped. The
code runs in an OpenSandbox sandbox once the hands-on is built, and as a local process before it; Stop kills both.
Sandboxes are found by their metadata, brand and conversation matched exactly, for the same reason as Session 4's
t3a9-old: a prefix match on k7c1 would also find k7c1-old.

Two events are the runner's own, because the page that is ready-made reads them. A message that has to wait adds
{"type": "waiting", "text": ...} to the running job's log. When a turn ends, the runner adds one last event,
{"type": "end", "status": <the job's final status>}, which tells the page the job is over.

A second hook after Stop, launchkit/jobs/steps.py's step_hook, makes every tool call a step on disk, and a server
that starts again resumes the jobs it left running.

Reference page 12, A turn that outlives its request, and page 13, Stopping a run.
"""

import threading
import time

from agno.exceptions import StopAgentRun

from launchkit.jobs.record import ACTIVE, LOCK, append_event, create, current, load, save
from launchkit.jobs.steps import step_hook
from launchkit.sandbox.engine import kill_sandboxes
from launchkit.sandbox.local import kill_here

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
        run_turn({**job.body, "job_id": job.id}, emit, [stop_hook(settings, job.id), step_hook(settings, job.id, emit), *hooks])
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
    kill_here(job.brand, job.conversation)
    kill_sandboxes(job.brand, job.conversation)
    return job
