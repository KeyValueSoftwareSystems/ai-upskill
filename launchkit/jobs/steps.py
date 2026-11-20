"""Stage 5: steps on disk, so a restart carries on and nothing is done twice.

Not built yet. The room builds this in stage 5, after restarting the server halfway through the fourteen sizes and
finding the job's record still saying "running" with nothing running it.

What it must do. Each tool call a job makes is a step with a key, such as j7:size-1080x1350. Before a step runs it is
written down as started; when it has run it is written down as done, with its result. A step whose key is already
done is not run again: its recorded result is handed back instead. That is what makes a step idempotent, meaning
running it twice has the same effect as running it once.

When the server starts, resume_jobs finds every job whose record says running and starts its turn again, with the
same job id and the same steps. The steps that were done come back from disk in a moment, and the job carries on
from the first one that was not.

Reference page 14, Durable execution, and page 15, Checkpoints and resuming.
"""

from launchkit.tools.catalogue import todo


@todo
def step_hook(settings, job_id: str, emit=None):
    """An Agno tool hook: run each tool call once per key, and hand back the recorded result after that."""
    raise NotImplementedError("stage 5 builds steps")


@todo
def resume_jobs(settings, run_turn) -> list[str]:
    """Start again every job a restart left running. Returns their ids."""
    raise NotImplementedError("stage 5 builds steps")
