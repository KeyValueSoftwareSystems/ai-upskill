"""Stage 4: a job's record and its event log, on disk.

Not built yet. The room builds this in stage 4, after watching Sam reload the page in the middle of the fourteen sizes
and lose all of it, and Maya send "also make it blue" into a job she could not stop.

What it must do. Each job is a folder, data/jobs/<job id>/, with two files:

    job.json       who asked, for which conversation, the message itself, and the job's status
    events.jsonl   every event the turn emitted, one line each, numbered 1, 2, 3 in the order they happened

The page reads the events through events_after, so it can come back after a reload and replay from any number. The
job's status is one of running, stopping, stopped, done or failed. A conversation has at most one job that is running
or stopping, and current() finds it.

The Job shape is ready-made, so the page and the checks agree on names. The functions are the build.

Reference page 12, A turn that outlives its request, and page 13, Stopping a run.
"""

from dataclasses import dataclass, field
from pathlib import Path

from launchkit.tools.catalogue import todo

ACTIVE = ("running", "stopping")


@dataclass
class Job:
    id: str             # j1, j2, ... in the order jobs were started on this machine
    brand: str
    user: str
    conversation: str
    body: dict          # the message as the page sent it: workspace_id, user_id, session_id, text, model, attached
    status: str = "running"
    started: float = 0.0
    ended: float | None = None
    waiting: list[dict] = field(default_factory=list)   # messages that arrived while this job ran, oldest first


def jobs_dir(settings) -> Path:
    return settings.data_dir / "jobs"


@todo
def create(settings, body: dict) -> Job:
    """A new job for this message, saved, with status running."""
    raise NotImplementedError("stage 4 builds the job record")


@todo
def load(settings, job_id: str) -> Job:
    raise NotImplementedError("stage 4 builds the job record")


@todo
def save(settings, job: Job) -> None:
    raise NotImplementedError("stage 4 builds the job record")


@todo
def all_jobs(settings) -> list[Job]:
    raise NotImplementedError("stage 4 builds the job record")


@todo
def current(settings, brand: str, conversation: str) -> Job | None:
    """The job running or stopping in this conversation, if there is one."""
    raise NotImplementedError("stage 4 builds the job record")


@todo
def append_event(settings, job_id: str, event: dict) -> int:
    """Add one event to the job's log and return its number."""
    raise NotImplementedError("stage 4 builds the job record")


@todo
def events_after(settings, job_id: str, seq: int) -> list[dict]:
    """Every event numbered after `seq`, oldest first, each with its "seq"."""
    raise NotImplementedError("stage 4 builds the job record")
