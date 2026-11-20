"""Stage 4: a job's record and its event log, on disk.

Built in stage 4, after the room watched Sam reload the page in the middle of the fourteen sizes and lose all of it,
and Maya send "also make it blue" into a job she could not stop.

Each job is a folder, data/jobs/<job id>/, with two files:

    job.json       who asked, for which conversation, the message itself, and the job's status
    events.jsonl   every event the turn emitted, one line each, numbered 1, 2, 3 in the order they happened

The page reads the events through events_after, so it can come back after a reload and replay from any number. The
job's status is one of running, stopping, stopped, done or failed. A conversation has at most one job that is running
or stopping, and current() finds it.

Writes go through one lock, because the server writes a job's log from the job's own thread while a page asks for
it from another. job.json is written to a new file and then renamed over the old one, so a reader never sees half of
it. The log is append-only, as Session 4's record is: a line is added, never rewritten.

Reference page 12, A turn that outlives its request, and page 13, Stopping a run.
"""

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

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


LOCK = threading.RLock()
_SEQ: dict[str, int] = {}  # the last event number of each job's log this process has written or read


def _folder(settings, job_id: str) -> Path:
    return jobs_dir(settings) / job_id


def _write(settings, job: Job) -> None:
    file = _folder(settings, job.id) / "job.json"
    fresh = file.with_suffix(".tmp")
    fresh.write_text(json.dumps(asdict(job), indent=2), encoding="utf-8")
    os.replace(fresh, file)


def create(settings, body: dict) -> Job:
    """A new job for this message, saved, with status running."""
    with LOCK:
        folder = jobs_dir(settings)
        folder.mkdir(parents=True, exist_ok=True)
        numbers = [int(p.name[1:]) for p in folder.glob("j*") if p.name[1:].isdigit()]
        job = Job(id=f"j{max(numbers, default=0) + 1}", brand=body["workspace_id"], user=body["user_id"],
                  conversation=body.get("session_id") or "", body=dict(body), started=time.time())
        _folder(settings, job.id).mkdir()
        _write(settings, job)
        return job


def load(settings, job_id: str) -> Job:
    return Job(**json.loads((_folder(settings, job_id) / "job.json").read_text(encoding="utf-8")))


def save(settings, job: Job) -> None:
    with LOCK:
        _write(settings, job)


def all_jobs(settings) -> list[Job]:
    folder = jobs_dir(settings)
    found = [p.name for p in folder.glob("j*") if (p / "job.json").is_file()] if folder.is_dir() else []
    return [load(settings, job_id) for job_id in sorted(found, key=lambda name: int(name[1:]))]


def current(settings, brand: str, conversation: str) -> Job | None:
    """The job running or stopping in this conversation, if there is one."""
    return next((j for j in all_jobs(settings) if j.brand == brand and j.conversation == conversation and j.status in ACTIVE), None)


def _read(settings, job_id: str) -> list[dict]:
    file = _folder(settings, job_id) / "events.jsonl"
    if not file.exists():
        return []
    events = []
    for line in file.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:  # a last line cut short by a crash
            continue
    return events


def append_event(settings, job_id: str, event: dict) -> int:
    """Add one event to the job's log and return its number."""
    with LOCK:
        if job_id not in _SEQ:
            _SEQ[job_id] = max((e["seq"] for e in _read(settings, job_id)), default=0)
        _SEQ[job_id] += 1
        line = json.dumps({**event, "seq": _SEQ[job_id]}, default=str)
        with open(_folder(settings, job_id) / "events.jsonl", "a", encoding="utf-8") as log:
            log.write(line + "\n")
        return _SEQ[job_id]


def events_after(settings, job_id: str, seq: int) -> list[dict]:
    """Every event numbered after `seq`, oldest first, each with its "seq"."""
    return [e for e in _read(settings, job_id) if e["seq"] > seq]
