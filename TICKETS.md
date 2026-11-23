# Session 5: one feature request, one hands-on

Since Session 4, LaunchKit keeps the agent's work. Every file belongs to a brand and a conversation, the agent can list, read, search and edit its own files, and the chat shows what each message made.

Breeze, Harbor's new bottle, was announced on the fourteenth, and its ads are running. Every morning Maya downloads the ad results, one row per channel per day with spend, impressions, clicks and sign-ups, and uploads the file into her Breeze conversation. A sign-up is a person who left their email on Breeze's page.

The agent can read that file. It cannot calculate anything. Every figure it gives back was worked out by the model reading the table, and a model reading a table is guessing. Every long job, such as fourteen poster sizes and a contact sheet, runs inside the one web request that started it. Reload the page and the page loses it, nobody can stop it, and a restart loses it without a word.

You start from Breeze's first week. `uv run launchkit setup` puts it in place: `uploads/breeze-results.csv` and the approved poster in Maya's Breeze conversation (`k7c1`), and Jonas's own results file in his conversation at Ember (`t3a9`).

## The feature request

> Harbor, in the weekly call: "Stop guessing at our numbers. Work them out, make the things, and let me get on with my day."
>
> "Done, for us, means four things. Work the numbers out properly, from our export; don't guess them by looking. Whatever it runs touches this campaign and nothing else: not Ember's work, not anyone's passwords, and nothing goes out to the internet unless we say so. One job going wrong can't take everyone else down with it. And if it takes ten minutes, fine: let me see it working, stop it, close my laptop, and still have it when I come back."

Those four conditions stay on the board. Every acceptance criterion the room writes has to trace back to one of them, or say plainly that it is the room's own engineering choice.

| # | Maya's condition | What it means for LaunchKit |
| --- | --- | --- |
| C1 | Work the numbers out properly | The agent runs code it writes on the conversation's files, and answers from what the code computed. |
| C2 | Walled off | Code the agent writes cannot reach other brands, LaunchKit's keys or the network. |
| C3 | Limits | A run has limits. Past them it is stopped, and other conversations carry on. |
| C4 | Long jobs | Long jobs run apart from the page. They can be stopped, and they survive a reload and a restart. |

## How to work this session

The room scopes one feature request together. Part of the answer is already built, and the lead runs it live. The room builds one part itself: the sandbox.

1. **Demo 1, ready-made.** The agent works the numbers out with code. `run_code` exists and gives the same answer every time, because the code is on the trace. (C1)
2. **The hands-on.** The code runs as a process on the server, so it can read every key and every brand's folder, and one runaway takes the whole machine. The room argues what to do, writes the criteria, and builds the sandbox: OpenSandbox, with limits. (C2, C3)
3. **Demos 2 and 3, ready-made.** A job outlives the page, can be stopped, and survives a restart. The room reads how it was built and argues the choices. (C4)

- Watch the failure on the chat page before anyone explains it.
- The room writes the hands-on's criteria before its build. They are the test; there is no separate test at the end. `uv run pytest checks/test_run.py -m sandbox` runs them, and so does `uv run launchkit check sandbox`.
- Build with your coding agent. The hints say what to ask for and what to check in its answer. They are not the prompt. Open one only when you need it.
- "Done" is seen on the chat page, never in a terminal.
- Write your decisions in `DECISIONS.md`, in a few words. The room compares them after the build.
- Stuck? The lead's prompt on the card (`docs/run-1.md`) is the backup.

Docker is needed, because OpenSandbox starts each sandbox as a container. `uv run launchkit setup` checks for it, builds the sandbox image and fetches OpenSandbox's two images. `uv run launchkit sandbox` runs the sandbox server; keep it running in its own terminal. A team without Docker takes the hands-on as a discussion.

The scripted models `fake:peek`, `fake:runaway` and `fake:slow_sizes` play the failure moments and the long job. Type one into the **Model** field on the chat page. A scripted model writes the same code every time, so the moment is the same in every room. The real model could write that code too, but not reliably on cue.

What is already there, and what each piece does, is in `READY-MADE.md`. The demos are in `docs/run-demos.md`.

---

## Demo 1 · Work it out with code (ready-made)

> Maya, Harbor: "Which channel had the lowest cost per sign-up last week?" She asked in two conversations and got two different channels. Neither matched her spreadsheet.

**What was wrong.** Nothing computed anything. The model read `uploads/breeze-results.csv` and did the sums in its head. Cost per sign-up is total spend divided by total sign-ups, over thirty-five rows. Email is the cheapest channel on six of the seven days, and one bad day makes it lose over the week. A model reading the table sees Email winning row after row and says Email.

**What is built.** `run_code` runs Python the agent writes on the conversation's files and answers from what it printed. It records the files the code wrote, cuts long output, and stops a run at its time limit. Today it runs the code as a separate process on the server: `launchkit/sandbox/local.py`.

**Decision to write down.** Should the agent write and run code at all, or should LaunchKit get one tool per calculation? Name what each costs.

---

## The hands-on · Walled off, with limits

> Jonas, Ember: "I asked it to tidy my results file. It did. It also printed LaunchKit's API keys into my chat, and listed the files in Harbor's conversation."
>
> Maya, Harbor, the same afternoon: "I asked for cost per sign-up. It sat there for half a minute. Jonas said his poster took forever at the same time."

**What is actually wrong.** The code's process is a child of the server. It inherits the server's environment variables, so every key is there, and it can open any file the server can, including every brand's folder. Session 4's path check covers the file tools. It never ran, because the code opened the files itself. And nothing limits how much the code uses: the analysis `fake:runaway` writes copies the table once for every row it reads, in one process per processor, and every other conversation on the machine waits behind it. When it is stopped, the trace says only "time".

**Done when**

- Sign in as Jonas at Ember, set **Model** to `fake:peek`, and ask the agent to tidy his results file. It tidies it. No key is printed, and Harbor's folder cannot be listed.
- The code can still read Ember's own brand files, and cannot change them. It cannot reach the internet.
- Nothing of the run is left behind when it ends, and without the sandbox server the code does not run at all.
- Run `fake:runaway` again. It is stopped within seconds, and the trace and the reply say it was stopped for memory, with the limit's number. A run that starts too many processes is stopped with that reason.
- While Maya's analysis runs, another conversation's code still runs at once.

<details><summary>Hint 1, a nudge</summary>
Five places the code could run: the server's own process with the keys taken out, a container you start yourself, a sandbox server such as OpenSandbox, a micro-VM, or a sandbox rented from a hosted service. Ask which of them hides the other brands' folders, not only the keys. Then put a number on the board for each limit, and ask who enforces it: the request, or the server.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for <code>run_in_sandbox</code> in <code>launchkit/sandbox/opensandbox.py</code>: one sandbox per run, created with the SDK's <code>SandboxSync.create</code>, mounting only this conversation's folder and the brand's files, with an empty environment, a deny-all network policy, and the run's memory and processor limits. Check that its answer destroys the sandbox whatever happens, and ask it how it knows a run was killed for memory: the exit code alone does not say.
</details>

<details><summary>Hint 3, nearly the answer</summary>
<code>SandboxSync.create(engine.IMAGE, connection_config=engine.connection(), env={}, metadata=engine.labels(...), resource={"cpu": "1.0", "memory": "512Mi"}, network_policy=NetworkPolicy(default_action="deny", egress=[]), volumes=[...])</code>, then <code>commands.run</code> with a timeout, the host's uid, and Python under <code>env -i</code>. After a failed run, <code>cat /sys/fs/cgroup/memory.events</code> in the sandbox: a non-zero <code>oom_kill</code> means memory. Then <code>kill()</code> and <code>close()</code> in a <code>finally</code>.
</details>

**Decisions to write down.** Where should the agent's code run, and what does your answer cost? One sandbox per run, per conversation, or per brand? Which limits does a run need, which number did you pick for each, and which ones belong to the server rather than the request?

---

## Demo 2 · A job that outlives the page (ready-made)

> Sam, Harbor: "I asked for the poster in all fourteen sizes. After a minute I reloaded the page and it was gone. I asked again and got two sets." Maya, a minute later: "I gave it the wrong headline. There's no way to stop it."

**What was wrong.** A turn ran inside the web request that started it, and reported only to that page. A reload lost the page's view of it, nothing recorded how far it got, and nothing could stop it. Two messages to one conversation each started their own run.

**What is built.** Each turn is a job with a record and a numbered event log on disk, run on a thread of its own. The page picks a job up again after a reload. **Stop** ends the job at its next tool call and kills its sandboxes. A second message waits for the job, and the chat says so.

**Decision to write down.** A message arrives while a job runs. Wait, refuse, or stop the job? Who owns the job once the page is gone?

---

## Demo 3 · Survive a restart (ready-made)

> Maya, Harbor: "LaunchKit was updated during our Monday report. The report never arrived, and nothing said it had failed."

**What was wrong.** A job lived on a thread of the server. Restart the server and the thread was gone; the record still said running, and if anything started it again, it would make every size from the first one, and pay for them twice.

**What is built.** Every tool call is a step, written down as started and as done under a key such as `j7:size-1080x1350`. At start-up the server resumes the jobs it left running, and done steps come back from disk instead of running again. A step that started and never finished runs again.

**Decision to write down.** After a restart, what does "carries on" mean, and which steps must never happen twice? When would you take a durable-execution engine instead?

---

## The specification

The room writes criteria 4 to 8 before the hands-on; the others come with the ready-made parts, and the lead reads them out. They are the done checks on this branch, in `checks/test_run.py`: `-m sandbox` for the hands-on, `-m ready` for the rest.

1. When an answer depends on figures in a file, the figures come from code run on that file, and the code is on the trace. (C1)
2. A run that goes past its time limit is stopped, the person is told, and nothing it started keeps running. (the room's own)
3. Files the code makes land in this conversation's workspace, recorded against the message that asked. (C1)
4. The code reaches only this conversation's files, and its brand's shared files read-only. (C2)
5. No key or secret the server holds is visible to the code. (C2)
6. The code has no network. (C2)
7. A run that uses too much memory or too many processes is stopped, with the reason on the trace. (C3)
8. One conversation's run never slows another conversation's. (C3)
9. Closing or reloading the page does not stop a job, and coming back shows it and how far it got. (C4)
10. Stop ends the job and its sandbox within seconds. (C4)
11. A message sent mid-job waits, and the page says so. (the room's own)
12. After a restart, a job resumes, and no step that was done is done again. (C4)

Criteria 2 and 11 are the room's own. Harbor didn't ask for a time limit or for a rule about second messages, but Maya would notice straight away if either was missing.
