# Session 5: one feature request, built in five stages

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

The session works as Session 4 did. The room scopes one feature request together and builds it in stages, like red and green in test-driven development, where a test fails first and then passes.

1. Something fails on the chat page.
2. The room argues what to do about it and writes that stage's acceptance criteria.
3. The lead explains the prompt and runs it, and that stage's checks go green.
4. The next failure appears on top of what you just built.

- Watch each stage fail on the chat page before anyone explains it.
- The room writes each stage's criteria before its build, one to four at a time. They are the test; there is no separate test at the end. `uv run pytest checks/test_run.py -m stage1` runs one stage's checks, and so does `uv run launchkit check run1`.
- Build with your coding agent. The hints say what to ask for and what to check in its answer. They are not the prompt. Open one only when you need it.
- "Done" is seen on the chat page, never in a terminal.
- Write your decision in `DECISIONS.md`, in a few words. The room compares them after the build.
- Stuck? Move on. The stages before yours stay as they are, and the lead's prompt for your stage is the backup.

Docker is needed from stage 2 on, because the agent's code runs in a container. `uv run launchkit setup` checks for it and builds the sandbox image. A team without Docker builds stage 1, and treats stage 2 as a discussion.

The scripted models `fake:peek`, `fake:runaway` and `fake:slow_sizes` play the failure moments of stages 2 to 5. Type one into the **Model** field on the chat page. A scripted model writes the same code every time, so the failure is the same in every room. The real model could write that code too, but not reliably on cue. Stage 1's failure runs on the real model.

What is already there, and what each piece does, is in `READY-MADE.md`.

---

## Stage 1 · Work it out with code

> Maya, Harbor: "Which channel had the lowest cost per sign-up last week?" She asked in two conversations and got two different channels. Neither matched her spreadsheet.

**What is actually wrong.** Nothing computes anything. The agent reads `uploads/breeze-results.csv` with `read_file`, and the model does the sums in its head. Cost per sign-up is total spend divided by total sign-ups, over thirty-five rows. Email is the cheapest channel on six of the seven days, and one bad day makes it lose over the week. A model reading the table sees Email winning row after row and says Email.

**Done when**

- Ask the same question in two new conversations. Both answers name the same channel and the same figure, and the figure matches the room's hand calculation.
- The Trace shows the code that ran, and the reply says which file it read.
- Ask for the cost per sign-up by channel saved as a table. The file appears with the message that asked for it. (A chart waits for stage 2: matplotlib is in the sandbox image, not in LaunchKit's own Python.)
- A run that never ends is stopped at its time limit, and the agent says so.

<details><summary>Hint 1, a nudge</summary>
Look at <code>launchkit/tools/run_code.py</code>, and at how <code>write_file</code> adds every file it writes to the record. The code the agent writes will write files too, and nobody tells the record about them unless run_code does.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for <code>make_run_code</code> that runs the code as a separate Python process in this conversation's workspace, with a time limit, and hands back what it printed cut to a set size. Check that its answer finds the files the code wrote by comparing the folder before and after, and that it kills everything the code started, not only the process it started itself, when the time runs out.
</details>

<details><summary>Hint 3, nearly the answer</summary>
<code>subprocess.Popen([sys.executable, "-I", "-c", code], cwd=workspace.root, start_new_session=True)</code>, then <code>communicate(timeout=...)</code>. A new session puts the code and everything it starts in one process group, so <code>os.killpg</code> ends all of it. Snapshot each file's modification time and size before the run and after, and record what changed.
</details>

**Decision to write down.** Should the agent write and run code at all, or should LaunchKit get one tool per calculation? Name what each costs.

---

## Stage 2 · Walled off

> Jonas, Ember: "I asked it to tidy my results file. It did. It also printed LaunchKit's API keys into my chat, and listed the files in Harbor's conversation."

**What is actually wrong.** Stage 1's process is a child of the server. It inherits the server's environment variables, so every key is there, and it can open any file the server can, including every brand's folder. Session 4's path check covers the file tools. It never ran, because the code opened the files itself. Turning off a file tool doesn't take away the ability to read files: code can read them anyway.

**Done when**

- Sign in as Jonas at Ember, set **Model** to `fake:peek`, and ask the agent to tidy his results file. It tidies it. No key is printed, and Harbor's folder cannot be listed.
- The code can still read Ember's own brand files, and cannot change them.
- The code cannot reach the internet.
- Nothing of the run is left behind when it ends.

<details><summary>Hint 1, a nudge</summary>
Five places the code could run: the server's own process with the keys taken out, a container, gVisor, a micro-VM, or a sandbox rented from a hosted service. Ask which of them hides the other brands' folders, not only the keys.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for <code>run_in_container</code> in <code>launchkit/sandbox/container.py</code>: one <code>docker run</code> per run, mounting only this conversation's folder and the brand's files. Check that its answer passes no environment variables, turns the network off, runs as a user that is not root, and makes the root disk read-only. Ask it what the code can still write to.
</details>

<details><summary>Hint 3, nearly the answer</summary>
<code>docker run --rm --network none --user &lt;uid&gt; --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges -v &lt;workspace&gt;:/work -v &lt;brand&gt;:/brand:ro -w /work</code>, then the image, then <code>env -i</code> and Python. The image sets a few variables of its own; <code>env -i</code> starts Python with none.
</details>

**Decision to write down.** Where should the agent's code run, and what does your answer cost? One sandbox per run, per conversation, or per brand?

---

## Stage 3 · Contain the damage

> Maya, Harbor: "I asked for cost per sign-up. It sat there for half a minute. Jonas said his poster took forever at the same time."

**What is actually wrong.** The container isolates what the code can see. It does nothing about how much the code can use. The analysis `fake:runaway` writes copies the table once for every row it reads, in one process per processor. It takes every core and over a gigabyte of memory until the time limit stops it, and every other conversation on the machine waits behind it. When it is stopped, the trace says only "time".

**Done when**

- Run `fake:runaway` again. It is stopped within seconds, and the trace and the reply say it was stopped for memory, with the limit's number.
- A run that starts too many processes, or fills its scratch disk, is stopped with that reason.
- While Maya's analysis runs, another conversation's code still runs at once, and the activity monitor shows one core busy, not all of them.

<details><summary>Hint 1, a nudge</summary>
Before anyone builds anything, put a number on the board for each limit: time, memory, processor, processes, disk. Then ask what the machine does when a run reaches each one. Some kill the run. Some only refuse the next request, and the run fails with an error message.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for <code>docker_flags</code> and <code>stop_reason</code> in <code>launchkit/sandbox/limits.py</code>, and for the container to carry the flags. Check how its answer knows a run was killed for memory: the exit code alone does not say. Docker remembers it, but only until the container is removed.
</details>

<details><summary>Hint 3, nearly the answer</summary>
<code>--memory 512m --memory-swap 512m --cpus 1 --pids-limit 64 --tmpfs /tmp:rw,size=100m</code>. Run without <code>--rm</code>, read <code>docker inspect -f '{{.State.OOMKilled}}'</code>, then <code>docker rm -f</code>. "Resource temporarily unavailable" in the output means the process limit, "No space left on device" means the disk.
</details>

**Decision to write down.** Which limits does a run need, and what number did you pick for each? Which one would you lower first if forty brands shared one machine?

---

## Stage 4 · A job that outlives the page

> Sam, Harbor: "I asked for the poster in all fourteen sizes. After a minute I reloaded the page and it was gone. I asked again and got two sets." Maya, a minute later: "I gave it the wrong headline. There's no way to stop it. And I sent 'also make it blue', and one of the two replies vanished."

**What is actually wrong.** A turn runs inside the web request that started it, and reports only to that page. A reload loses the page's view of it, nothing records how far it got, and nothing can stop it. Two messages to one conversation each start their own run, and each saves the conversation over the other when it ends.

**Done when**

- Ask for every size with `fake:slow_sizes` and reload in the middle. The page picks the job up again, with its trace, and it finishes.
- Press **Stop**. The job ends within a few seconds, and its container is gone.
- Send "also make it blue" while the job runs. The chat says the message waits. It runs after the job, and both replies stay in the conversation.

<details><summary>Hint 1, a nudge</summary>
Four options for a second message: refuse it, queue it, interrupt the job, or roll the job back and restart. Two of them can lose work Maya asked for. Pick before you build.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for the job record and its event log in <code>launchkit/jobs/record.py</code>, and <code>start_job</code> and <code>stop_job</code> in <code>launchkit/jobs/runner.py</code>. Check that its answer numbers every event so a page can ask for "everything after 41", and that Stop kills the conversation's containers, not only the thread.
</details>

<details><summary>Hint 3, nearly the answer</summary>
A folder per job with <code>job.json</code> and <code>events.jsonl</code>; the turn on a thread of its own; an Agno tool hook that raises <code>StopAgentRun</code> once the job is marked stopping; <code>docker kill</code> on every container whose full name is <code>lk-&lt;brand&gt;-&lt;conversation&gt;-</code> and six letters. A message to a conversation with a job running goes on that job's waiting list.
</details>

**Decision to write down.** A message arrives while a job runs. Wait, refuse, or stop the job? Who owns the job once the page is gone?

---

## Stage 5 · Survive a restart

> Maya, Harbor: "LaunchKit was updated during our Monday report. The report never arrived, and nothing said it had failed."

**What is actually wrong.** A job lives on a thread of the server. Restart the server and the thread is gone. The job's record still says running, the page waits for a job nothing is running, and if anything started it again, it would make every size from the first one, and pay for them twice.

**Done when**

- Start every size with `fake:slow_sizes` and restart the server halfway. The job carries on from where it had got to.
- The sizes made before the restart are not made again. The trace says which steps were done before.
- A job that had finished stays finished.

<details><summary>Hint 1, a nudge</summary>
Three options: start the job again from the beginning, write each step down and resume, or hand the job to a durable-execution engine. Ask which steps must never happen twice, and what makes a step the same step after a restart.
</details>

<details><summary>Hint 2, the approach</summary>
Ask your coding agent for a step hook in <code>launchkit/jobs/steps.py</code> that writes each tool call down as started and as done, under a key, and hands back the recorded result for a key that is done. Then <code>resume_jobs</code>, which runs at start-up. Check what its answer does with a step that started and never finished.
</details>

<details><summary>Hint 3, nearly the answer</summary>
The key is the job and the run's label, <code>j7:size-1080x1350</code>, or the tool and a fingerprint of its inputs, plus which time it is in this run. A resumed turn is the same turn run again: its done steps come back from <code>steps.jsonl</code> in a moment.
</details>

**Decision to write down.** After a restart, what does "carries on" mean, and which steps must never happen twice? When would you take a durable-execution engine instead?

---

## The specification

The room writes these on screen as it goes. They are the done checks on this branch, in `checks/test_run.py`.

1. When an answer depends on figures in a file, the figures come from code run on that file, and the code is on the trace. (C1)
2. A run that goes past its time limit is stopped, the person is told, and nothing it started keeps running. (the room's own)
3. Files the code makes land in this conversation's workspace, recorded against the message that asked. (C1)
4. The code reaches only this conversation's files, and its brand's shared files read-only. (C2)
5. No key or secret the server holds is visible to the code. (C2)
6. The code has no network. (C2)
7. A run that uses too much memory, too many processes or too much disk is stopped, with the reason on the trace. (C3)
8. One conversation's run never slows another conversation's. (C3)
9. Closing or reloading the page does not stop a job, and coming back shows it and how far it got. (C4)
10. Stop ends the job and its sandbox within seconds. (C4)
11. A message sent mid-job waits, and the page says so. (the room's own)
12. After a restart, a job resumes, and no step that was done is done again. (C4)

Criteria 2 and 11 are the room's own. Harbor didn't ask for a time limit or for a rule about second messages, but Maya would notice straight away if either was missing.
