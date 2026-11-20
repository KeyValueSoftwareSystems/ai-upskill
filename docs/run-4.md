# Runtime stage 4 · A job that outlives the page

> Sam, Harbor: "I asked for the poster in all fourteen sizes. After a minute I reloaded the page and it was gone. I asked again and got two sets." Maya, a minute later: "I gave it the wrong headline. There's no way to stop it. And I sent 'also make it blue', and one of the two replies vanished."

Fourteen sizes and a contact sheet take about two minutes. A turn lives inside the web request that started it, and reports only to that page.

## The slot

- `launchkit/jobs/record.py` · `create`, `load`, `save`, `all_jobs`, `current`, `append_event`, `events_after`. Today each raises. The `Job` shape is ready-made.
- `launchkit/jobs/runner.py` · `start_job`, `stop_job`. Today each raises.

The page's job bar, its **Stop** button and its "waits" note are ready-made, and so are the routes they call. The routes answer 404 until this stage builds what they call. `run_turn` in `launchkit/web/app.py` is one turn, start to end. The runner calls it.

## Break it first

Sign in as **Maya at Harbor**, open `k7c1`, set **Model** to `fake:slow_sizes` and send:

> Every size of the Breeze poster, please, and a contact sheet.

The Trace shows one `code` line per size, about seven seconds each. `fake:slow_sizes` cuts each size with Pillow inside `run_code`. It calls no paid image service.

1. After about a minute, reload the page. The progress is gone: no trace, no "Working…", nothing in the chat. The run is still going on the server, and nothing on the page can find it.
2. Send the same message again. Now two runs make the same sizes.
3. While they run, send:

   > Also make the headline blue.

   It starts a third run beside the others.
4. Wait for all of them to end, then reload. Replies are missing from the conversation, and messages too. Each run loaded the conversation when it started and saved it when it ended, so the last save won.

There is no Stop button anywhere.

## Prompt card, for your coding agent

```
A turn lives inside the request that started it: a reload loses it, nothing stops it, and two messages to one
conversation run at once. Build stage 4 of Session 5: jobs. Read TICKETS.md (Stage 4), launchkit/jobs/record.py,
launchkit/jobs/runner.py, and run_turn and the /jobs routes in launchkit/web/app.py.

1. launchkit/jobs/record.py. A job is a folder data/jobs/<id>/ (jobs_dir(settings) / id), ids j1, j2, ... from the
   highest one already there. One threading.RLock, LOCK, guards every write.
   - create(settings, body): a new Job with brand, user and conversation from body's workspace_id, user_id and
     session_id, status "running", started now; writes job.json.
   - save writes job.json to a .tmp file and os.replace()s it over the old one. load reads it.
   - all_jobs(settings): every job, in id order. current(settings, brand, conversation): the one with status
     running or stopping (ACTIVE), or None.
   - append_event(settings, job_id, event): adds one line to events.jsonl, the event plus "seq", numbered 1, 2, 3
     per job, and returns the number. events_after(settings, job_id, seq): every event with a number above seq,
     skipping a last line cut short.

2. launchkit/jobs/runner.py.
   - start_job(settings, body, run_turn): under LOCK, if current() finds a job for the conversation, append body to
     its waiting list, save it, add {"type": "waiting", "text": "This message waits until the job that is running
     now finishes, then runs on its own. It is not lost."} to its log, and return {"job_id": <that job>, "waiting":
     True}. Otherwise create a job, start run_job on a daemon thread, and return {"job_id": <id>, "waiting": False}.
   - stop_hook(settings, job_id): an Agno tool hook, hook(function_name, function_call, arguments), that raises
     agno.exceptions.StopAgentRun when the job's status is "stopping", and otherwise returns
     function_call(**arguments).
   - run_job(settings, job, run_turn, hooks=()): calls run_turn({**job.body, "job_id": job.id}, emit,
     [stop_hook(...), *hooks]), where emit appends to the job's log. Under LOCK afterwards: the status becomes
     "stopped" if it was stopping, "failed" if run_turn raised, otherwise "done"; ended is set; the waiting list is
     taken and emptied; the job is saved; {"type": "end", "status": <status>} is appended; and each waiting body is
     started with start_job, in order.
   - stop_job(settings, job_id): if the job is active, mark it "stopping" and save it; append a trace event with the
     line "stop      Stop pressed: the job ends at its next step, and its sandbox is killed"; then docker kill
     every running container whose name is engine.name_prefix(brand, conversation) plus six hex letters, matched in
     full with re.fullmatch, never by "starts with". Return the job.

Do NOT: change run_turn, the routes or the page; write steps down or resume after a restart. Stage 5 does that.

Done when `uv run pytest checks/test_run.py -m stage4` passes.
```

## Prove it

```
uv run pytest checks/test_run.py -m stage4
```

- A job runs with nobody watching. Its events are numbered in order, and a page can replay them from any number.
- Stop ends a job within a few seconds, and the job's log ends with `stopped`.
- Stop kills the container the job started.
- A second message to a conversation with a job running waits for it, the log says so, and it never runs beside the first. A message to another conversation doesn't wait.

## Run it again

Send the fourteen sizes again, with `fake:slow_sizes`.

1. A job bar appears above the message box, with **Stop**.
2. Reload in the middle. The page picks the job up again and replays its trace from the start.
3. Send "also make the headline blue". The chat says the message waits, and it runs when the sizes are done. Both replies stay in the conversation.
4. Start the sizes once more and press **Stop**. The job ends within a second or two, the chat says it was stopped, and no container is left running.

The room's own criterion is the waiting note. Harbor didn't ask for it, and Maya would notice if it were missing.

## Why it matters

The decision this stage settles is who owns a job once the page is gone. The answer is the server: it keeps a record on disk and an event log the page can replay.

The room also picks one policy for a second message:

- **Refuse it.** Nothing is lost, and the person has to send it again.
- **Queue it.** Nothing is lost, and the person waits.
- **Interrupt the job.** The work done so far may be thrown away.
- **Roll back and restart.** The work done so far is thrown away for certain.

The room queued it. Products differ here: LangGraph's server offers all four as "double-texting" options.

Stop has to reach the container as well as the thread, or the run keeps going after the job says it stopped. Containers are found by their full name, for the same reason as Session 4's `t3a9-old`: `lk-harbor-k7c1-` is also the start of `lk-harbor-k7c1-old-…`.

The job lives on a thread of this server. Restart the server and the thread is gone, while the record still says running. Stage 5 is that failure.
