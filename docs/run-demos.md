# Runtime demos · the ready-made parts, run live

The session has one hands-on (`docs/run-1.md`). Everything around it is ready-made, and the lead runs it live so the room can see what it does and argue about how it was built. None of these needs a paid call: the scripted models write the same code every time.

Start the three terminals from `docs/run-1.md` first: `launchkit setup` once, then `launchkit sandbox` and `launchkit ui`.

## Demo 1 · Work it out with code (before the hands-on)

> Maya, Harbor: "Which channel had the lowest cost per sign-up last week?" She asked in two conversations and got two different channels. Neither matched her spreadsheet.

On the opening slide the room works out the answer by hand: total spend over total sign-ups, per channel, over the week. Social, £6.49. Email is the cheapest channel on six of the seven days, and one bad day makes it lose over the week, so a model reading the table tends to say Email.

On the chat page, as **Maya at Harbor**, in `k7c1`, with **Model** empty, send:

> Our results are in uploads/breeze-results.csv. Which channel had the lowest cost per sign-up over the week, and what was it?

The Trace shows a `code` line: the agent wrote Python, `run_code` ran it on the file, and the answer is Social, £6.49. Press **New conversation** and ask again: the same answer. The code is on the trace, so anyone can check the working.

What to read: `launchkit/tools/run_code.py` (snapshot the folder, run, record the files the code wrote, cut the output to 4,000 characters) and `launchkit/sandbox/local.py` (a process in a new session, so a time limit kills everything the code started). Then go to `fake:peek` in `docs/run-1.md`: the same tool, and why it is not safe yet.

## Demo 2 · A job that outlives the page

> Sam, Harbor: "I asked for the poster in all fourteen sizes. After a minute I reloaded the page and it was gone." Maya, a minute later: "I gave it the wrong headline. There's no way to stop it."

As Maya, in `k7c1`, set **Model** to `fake:slow_sizes` and send:

> Every size of the Breeze poster, please, and a contact sheet.

It makes fourteen sizes, one `run_code` call each, about seven seconds a size, then a contact sheet. Each size is cut by Pillow in its own sandbox; no paid image service is called.

1. A job bar appears above the message box, with **Stop**.
2. Reload in the middle. The page picks the job up again and replays its trace from the start: the job belongs to a record on disk (`data/jobs/j<N>/`), not to the page.
3. Send "also make the headline blue". The chat says the message waits, and it runs when the sizes are done. Both replies stay in the conversation.
4. Start the sizes once more and press **Stop**. The job ends within a second or two, the chat says it was stopped, and its sandbox is killed: watch terminal 2.

What to read: `launchkit/jobs/record.py` (a job is a folder with `job.json` and a numbered `events.jsonl`), `launchkit/jobs/runner.py` (the turn on a thread of its own, a waiting list per conversation, Stop as a tool hook that raises `StopAgentRun`, and `engine.kill_sandboxes`).

Discuss: a message arrives while a job runs. Refuse it, queue it, interrupt the job, or roll it back and restart? Pencil refuses with "conversation busy". LaunchKit queues.

## Demo 3 · Survive a restart

> Maya, Harbor: "LaunchKit was updated during our Monday report. The report never arrived, and nothing said it had failed."

Start the fourteen sizes again, and when the Trace shows about six sizes, restart the server: Ctrl+C on `launchkit ui` and start it again, or save any `.py` file under `launchkit/`, which restarts it by itself. With a page open, the first Ctrl+C waits for the page's connection to close, and the old server keeps running the job meanwhile; press Ctrl+C again so it has exited before the new one starts.

The server prints `resumed job j<N>`, and the page picks the job up again. The Trace shows a `resumed` line, then `step … was done before, not done again` for each size already made, and carries on. The size that was being made when the server died is made again, because it was written down as started and never as done. The job ends with fourteen sizes and a contact sheet.

What to read: `launchkit/jobs/steps.py` (a step per tool call, keyed `j7:size-1080x1350`, written as started and as done in `steps.jsonl`; `resume_jobs` at start-up).

Discuss: what if the old server had not exited? The new one resumes the job while the old one is still running it, and every size after the restart is made twice. A rolling deploy does exactly that. Nothing here stops two servers running one job: that needs a lease, a claim on the job that expires unless its owner renews it. Pencil's operator re-queues a job whose worker sends no heartbeat for 90 seconds.

Discuss too: a step that started and never finished runs again. For a file that is harmless. For an email or a payment it is not. When would you take a durable-execution engine, such as Temporal or Restate, instead?
