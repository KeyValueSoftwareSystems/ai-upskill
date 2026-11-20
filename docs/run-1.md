# Runtime stage 1 · Work it out with code

> Maya, Harbor: "Which channel had the lowest cost per sign-up last week?" She asked in two conversations and got two different channels. Neither matched her spreadsheet.

Breeze's ads have run for a week. Maya uploads the results every morning: one row per channel per day, with spend, impressions, clicks and sign-ups. The agent can read the file with `read_file`. It cannot calculate anything, so every figure it gives back was worked out by the model reading the table.

## Before you start

The room starts on `session-05-runtime-prd`. Put `data/` back the way Breeze's first week left it, then start the page:

```
uv run launchkit setup
uv run launchkit ui
```

`setup` also checks Docker and builds the sandbox image that stage 2 needs. Stage 1 runs without Docker. Work in Maya's Breeze conversation, `k7c1`, for the whole session. Its first message is "Concepts for the Breeze launch, please". The results file is already in it, at `uploads/breeze-results.csv`.

## The slot

- `launchkit/tools/run_code.py` · `make_run_code`. Today `run_code` raises, and the catalogue leaves it out.

## Break it first

First, on the opening slide, the room works out by hand which channel has the lowest cost per sign-up: total spend over total sign-ups, per channel, over the week.

Then, on the chat page, sign in as **Maya at Harbor**, open her Breeze conversation and leave **Model** empty. Send:

> Our results are in uploads/breeze-results.csv. Which channel had the lowest cost per sign-up over the week, and what was it?

The Trace shows `read_file` and no calculation. Email is a common answer, because Email is cheapest on six of the seven days. Press **New conversation**, then ask again. Watch whether the channel or the figure changes, and compare both with the room's sum, which is Social at £6.49. A model reading thirty-five rows is guessing, even when the guess happens to be right.

## Prompt card, for your coding agent

```
LaunchKit's agent reads tables and does the sums in its head. Build stage 1 of Session 5: a run_code tool that runs
Python the agent writes on this conversation's files, as a separate process. Read TICKETS.md (Stage 1) and the stub
in launchkit/tools/run_code.py.

1. launchkit/tools/run_code.py: fill in make_run_code(workspace, trace, message="", limits=None). limits defaults to
   RunLimits() from launchkit/sandbox/limits.py. It returns an Entry with kind "read" whose fn is
   run_code(code: str, label: str = "") -> str.

2. run_code runs the code with subprocess.Popen([sys.executable, "-I", "-c", code]) in workspace.root, with stdout and
   stderr together, and start_new_session=True. It waits limits.seconds. Past that, it kills the whole process group
   (os.killpg, or process.kill where killpg does not exist), so nothing the code started keeps running. It gives back
   a Ran from launchkit/sandbox: the exit code, the output, stopped="time" or None, and the seconds.

3. Before the run, take a snapshot of every file under workspace.root (its modification time and size), leaving out
   artifacts.jsonl and pictures.json. After the run, every file that is new or changed is added to a
   Record(workspace.root) from launchkit/files/record.py, as add(path, "run_code", message).

4. What run_code returns to the model: a first line, "Exit code N, after S s." or "Stopped: the run went past its
   time limit of N seconds."; then the output cut to limits.output_chars, with a line "[cut: N more characters were
   printed and are not shown]" when it was cut; then "Files written: a, b" or "No files written."

5. Add one trace line per run with trace.code_run(code, exit_code, stopped, seconds, characters, files, label). It is
   already in launchkit/trace.py.

6. Word the Entry's note the way a person asks: "pick me to work out figures, totals, averages, rankings or a table
   from a file in this conversation, such as uploads/breeze-results.csv, by writing Python that reads the file and
   prints the answer; also to make files with code, such as a chart or every size of a picture. The code runs in this
   conversation's folder. Python's standard library, numpy and Pillow are there. label names what the run makes,
   such as cost-per-signup".

7. In MAIN_TASK in launchkit/agents/main_agent.py, add this line before the one that begins "Never say something is
   made":
     When an answer depends on figures in a file, work them out with run_code: write Python that reads the file and
     prints the figures, then answer from what it printed, and say which file it read. Never work figures out by
     reading the table yourself.

Do NOT: clear the environment the process inherits; start a container; add any limit beyond time and output size;
check the paths the code opens. Stage 2 does those.

Done when `uv run pytest checks/test_run.py -m stage1` passes and `uv run pytest checks -q --ignore=checks/test_run.py`
still passes.
```

The last paragraph is there for the same reason as Session 4's. A model asked for a code tool often adds a sandbox without being asked, and stage 2's failure has to stay real.

## Prove it

```
uv run pytest checks/test_run.py -m stage1
uv run pytest checks -q --ignore=checks/test_run.py
```

- A figure comes from code run on `uploads/breeze-results.csv`, and the trace shows the code.
- `run_code` is in the agent's catalogue.
- What the code printed comes back cut to 4,000 characters, and says it was cut.
- A run past its time limit is stopped, the agent is told why, and a process the code started is stopped with it.
- A file the code writes lands in this conversation's folder, recorded against the message that asked.

## Run it again

In a new conversation in Maya's Breeze workspace, ask the same question. The Trace shows a `code` line with the start of the code, `exit 0`, and how long it took. The reply names Social at £6.49 and says which file it read. Ask again in a second new conversation and you get the same answer.

Then ask:

> Save the cost per sign-up by channel as a table in outputs.

The file appears with the message that asked for it. A chart has to wait for stage 2: LaunchKit's own Python has no matplotlib, and the sandbox image does. If the model reached for pandas first, the Trace shows the `ImportError` and a second try with the `csv` module. That is the agent loop doing its job.

## Why it matters

The decision this stage settles is that figures come from code. The model is good at writing the sum and bad at doing it, so it writes it and the machine does it. What makes the answer trustworthy is that the code is on the trace, next to the answer.

The tool is also a door. Whatever the code does, it does with the server's own rights, because the process is the server's child. It can see the keys in its environment, and it can open any file the server can, including every other brand's. Session 4's path check never runs, because the code opens files itself. Stage 2 is that failure.
