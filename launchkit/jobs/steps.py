"""Ready-made: steps on disk, so a restart carries on and nothing is done twice.

The answer to the moment the room watches live: the server restarted the server halfway through the fourteen sizes and found the job's record
still saying "running" with nothing running it. A job lived on a thread, and a thread does not survive its process.

Each tool call a job makes is a step with a key. The key is the job and the label the agent gave the run, such as
j7:size-1080x1350, or the job, the tool and a short fingerprint of its inputs when there is no label. Before a step
runs it is written down as started; when it has run it is written down as done, with its result. A step whose key is
already done is not run again: its recorded result is handed back instead. That is what makes a step idempotent,
meaning running it twice has the same effect as running it once.

A key can come up more than once in one job: the agent may list the files before and after it writes one. So the key
also carries which time this is (#2, #3), counted from the start of the run. A run that starts again counts from the
start again, so its first list_files meets the first one's result, and its second meets the second's.

When the server starts, resume_jobs finds every job whose record says running and starts its turn again, with the same
job id and the same steps. The steps that were done come back from disk in a moment, and the job carries on from the
first one that was not. A job that was stopping when the server went down is marked stopped.

What this does not cover, and the room should say so: a step that was started and never written down as done. It ran
partway, or all the way and the server died before the line was written. It runs again. For a file the code writes
that is harmless; for an email or a payment it is not, which is where an idempotency key has to go to the service
that does the effect, and where a durable-execution engine starts to pay for itself.

Reference page 14, Durable execution, and page 15, Checkpoints and resuming.
"""

import hashlib
import json
from collections import Counter

from launchkit.jobs.record import ACTIVE, LOCK, all_jobs, append_event, jobs_dir, save


def step_key(job_id: str, function_name: str, arguments: dict) -> str:
    """j7:size-1080x1350 when the agent labelled the run, otherwise j7:<tool>:<fingerprint of its inputs>."""
    through_door = function_name == "run_tool" and isinstance(arguments.get("inputs"), dict)
    name = arguments.get("name", function_name) if through_door else function_name
    inputs = arguments["inputs"] if through_door else arguments
    if isinstance(inputs.get("label"), str) and inputs["label"]:
        return f"{job_id}:{inputs['label']}"
    digest = hashlib.sha1(json.dumps([name, inputs], sort_keys=True, default=str).encode()).hexdigest()[:10]
    return f"{job_id}:{name}:{digest}"


class Steps:
    """One job's steps, data/jobs/<id>/steps.jsonl: a line when a step starts, a line with its result when it is done."""

    def __init__(self, settings, job_id: str):
        self.file = jobs_dir(settings) / job_id / "steps.jsonl"

    def done(self, key: str) -> dict | None:
        if not self.file.exists():
            return None
        for line in self.file.read_text(encoding="utf-8").splitlines():
            try:
                step = json.loads(line)
            except json.JSONDecodeError:
                continue
            if step["key"] == key and step["state"] == "done":
                return step
        return None

    def write(self, key: str, state: str, result=None) -> None:
        with LOCK:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file, "a", encoding="utf-8") as log:
                log.write(json.dumps({"key": key, "state": state, "result": result}, default=str) + "\n")


def step_hook(settings, job_id: str, emit=None):
    """An Agno tool hook: run each tool call once per key, and hand back the recorded result after that."""
    steps, seen = Steps(settings, job_id), Counter()

    def hook(function_name: str, function_call, arguments: dict):
        base = step_key(job_id, function_name, arguments)
        seen[base] += 1
        key = base if seen[base] == 1 else f"{base}#{seen[base]}"
        found = steps.done(key)
        if found is not None:
            if emit is not None:
                emit({"type": "trace", "kind": "step", "line": f"step      {key} was done before, not done again"})
            return found["result"]
        steps.write(key, "started")
        result = function_call(**arguments)
        steps.write(key, "done", result)
        return result

    return hook


def resume_jobs(settings, run_turn) -> list[str]:
    """Start again every job a restart left running. Returns their ids."""
    import threading

    from launchkit.jobs.runner import run_job

    resumed = []
    for job in all_jobs(settings):
        if job.status not in ACTIVE:
            continue
        if job.status == "stopping":
            job.status = "stopped"
            save(settings, job)
            append_event(settings, job.id, {"type": "end", "status": "stopped"})
            continue
        append_event(settings, job.id, {"type": "trace", "kind": "note", "line": "resumed   the server restarted; the job carries on from its last finished step"})
        threading.Thread(target=run_job, args=(settings, job, run_turn), daemon=True, name=f"job-{job.id}").start()
        resumed.append(job.id)
    return resumed
