# Runtime stage 5 · Survive a restart

> Maya, Harbor: "LaunchKit was updated during our Monday report. The report never arrived, and nothing said it had failed."

A deploy restarts the server. A job is a thread of the server, and a thread doesn't outlive its process.

## The slot

- `launchkit/jobs/steps.py` · `step_hook`, `resume_jobs`. Today each raises.
- `launchkit/jobs/runner.py` · `run_job`: stage 4 gives the turn the Stop hook only.

The server already calls `resume_jobs` when it starts, once it is built (`resume_on_start` in `launchkit/web/app.py`).

## Break it first

As **Maya at Harbor**, in `k7c1`, with **Model** set to `fake:slow_sizes`, ask for every size again:

> Every size of the Breeze poster, please, and a contact sheet.

When the Trace shows about six sizes, restart the server. Either stop `uv run launchkit ui` with Ctrl+C and start it again, or save any `.py` file under `launchkit/`, which restarts it by itself. The page reloads and picks the job up from its record. The job bar says it is running, and nothing happens. Open `data/jobs/<id>/job.json`: the status is `running`, and nothing is running it.

If anything started it again from the top, it would make sizes one to six a second time. For a size cut by Pillow that only costs time. For a picture from a paid model, it would be Harbor's money twice.

## Prompt card, for your coding agent

```
A job lives on a thread, and a restart leaves its record saying running with nothing running it. Build stage 5 of
Session 5: steps on disk, and resume at start-up. Read TICKETS.md (Stage 5) and launchkit/jobs/steps.py.

1. launchkit/jobs/steps.py.
   - step_key(job_id, function_name, arguments): for a call through run_tool, the tool is arguments["name"] and its
     inputs are arguments["inputs"]; otherwise the function and its arguments. When the inputs have a non-empty
     "label", the key is "<job_id>:<label>", e.g. j7:size-1080x1350. Otherwise it is "<job_id>:<tool>:<first ten
     hex letters of sha1 of json.dumps([tool, inputs], sort_keys=True, default=str)>".
   - Steps(settings, job_id) keeps data/jobs/<id>/steps.jsonl: write(key, state, result=None) appends
     {"key", "state", "result"} under record.LOCK; done(key) returns the line whose key matches and whose state is
     "done", or None.
   - step_hook(settings, job_id, emit=None): an Agno tool hook. It counts how many times each key has come up in this
     run, and from the second time adds "#2", "#3" to the key. If the key is done, it returns the recorded result
     without calling the tool, and emits a trace event with the line "step      <key> was done before, not done
     again". Otherwise it writes "started", calls the tool, writes "done" with the result, and returns it.
   - resume_jobs(settings, run_turn): for every job whose status is "running", append a trace event with the line
     "resumed   the server restarted; the job carries on from its last finished step" and start runner.run_job on a
     daemon thread. A job left "stopping" is marked "stopped" and gets its {"type": "end", "status": "stopped"} event.
     Return the ids it started. Import runner inside the function, because runner imports steps.

2. launchkit/jobs/runner.py: run_job passes [stop_hook(...), step_hook(settings, job.id, emit), *hooks], so every job
   writes its steps from the start, not only after a restart.

Do NOT: try to undo a step that started and never finished; add a durable-execution library.

Done when `uv run pytest checks/test_run.py -m stage5` passes, and all of `uv run pytest checks/test_run.py` passes.
```

## Prove it

```
uv run pytest checks/test_run.py -m stage5
uv run pytest checks/test_run.py
```

- A step with a key runs once. Calling it again hands back the first result.
- A job a restart left running starts again, carries on from its last done step, and repeats none of them.
- A job that had finished is not started again.

## Run it again

Start the fourteen sizes again and restart the server at about size six. The server prints `resumed job j<N>`, and the page picks the job up again. The Trace shows a `resumed` line, then a `step … was done before, not done again` line for each size already made. Then it carries on. The size that was being made when the server died is made again, because it was written down as started and never as done. The job ends with fourteen sizes and a contact sheet, and the reply lists every one of them.

## Why it matters

The decision this stage settles is what "carries on" means:

- **The same job.** The resumed turn keeps the same job id, the same message, and the files recorded against it.
- **The same steps.** Each step is keyed, so a step that was done is not done again.

That is durable execution, built by hand: the job's progress is recorded step by step, so it survives a crash.

The gap is the step that started and never finished. It runs again. For a file that is harmless. For an email or a payment it is not, and there the key has to travel to the service that does the effect, so that the service refuses a second one.

Building steps by hand stops paying for itself when jobs wait for hours: a schedule, an approval, a person who is away. That is where an engine such as Temporal, Restate or LangGraph's checkpointer takes over the recording. It is the discussion after the build.
