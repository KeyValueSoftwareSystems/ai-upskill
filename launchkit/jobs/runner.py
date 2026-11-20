"""Stage 4: start a job apart from the page, stop it, and one job at a time per conversation.

Not built yet. The room builds this in stage 4, with the record in record.py.

What it must do.

start_job(settings, body, run_turn) starts the turn on a thread of its own and returns at once, so closing the page
does not stop it. The turn's events go into the job's log, not to the page that asked. When the conversation already
has a job running, the new message is not started: it is added to that job's waiting list, the job's log says so, and
start_job returns {"job_id": <the running job>, "waiting": True}. When a job ends, the first waiting message starts as
the next job.

stop_job(settings, job_id) marks the job as stopping, kills every container this conversation has running (they are
named with launchkit/sandbox/engine.py's name_prefix), and the turn ends at its next tool call. The job's status ends
as stopped.

Two events are the runner's own, because the page that is ready-made reads them. A message that has to wait adds
{"type": "waiting", "text": ...} to the running job's log. When a turn ends, the runner adds one last event,
{"type": "end", "status": <the job's final status>}, which tells the page the job is over.

run_turn is the chat page's turn (launchkit/web/app.py), passed in so the checks can hand in a short one. It is called
as run_turn(body, emit, hooks): emit(event) puts one event in the log, and hooks are Agno tool hooks the turn adds to
the agent, each called as hook(function_name, function_call, arguments).

Reference page 12, A turn that outlives its request, and page 13, Stopping a run.
"""

from launchkit.tools.catalogue import todo


@todo
def start_job(settings, body: dict, run_turn) -> dict:
    """Start this message as a job, or queue it behind the job already running in its conversation."""
    raise NotImplementedError("stage 4 builds jobs")


@todo
def stop_job(settings, job_id: str):
    """Mark the job as stopping and kill what it started. It ends within a few seconds."""
    raise NotImplementedError("stage 4 builds jobs")
