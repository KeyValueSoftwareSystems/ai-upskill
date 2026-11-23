# What is already built

The room builds one thing in Session 5: the sandbox. `launchkit/sandbox/opensandbox.py` is a stub that says what it must do, and `run_code` still calls the local process until the hands-on switches it over.

Everything else is already there. The code tool, jobs, Stop and resume are built, and the lead runs them live (`docs/run-demos.md`), so the room can read and argue about how they were built instead of typing them. The scripted models, the sandbox image, the sandbox server's settings, the seeded data and the checks are there too. This table says what each piece is, what it serves, and where the idea is explained in the reference.

| File | What it is | Serves | Reference page |
| --- | --- | --- | --- |
| `launchkit/sandbox/opensandbox.py` | **The hands-on.** `run_in_sandbox` and `oom_kills` are stubs. `CLEAN_ENV`, the empty environment Python starts in, and `sandbox_user`, the host's own user, are ready-made. | hands-on | 6, 9, 10 |
| `launchkit/tools/run_code.py` | Ready-made. The code tool: snapshots the conversation's folder, runs the code, records the files it wrote against the message, cuts what it printed to 4,000 characters, and puts a `code` line on the trace. It calls `run_here`; the hands-on changes that one call, and adds the fail-closed check. | demo 1, hands-on | 3, 4 |
| `launchkit/sandbox/local.py` | Ready-made. `run_here`: the code as a separate process on this machine, in a new session so a time limit kills everything it started. No sandbox: it is the failure `fake:peek` shows. `kill_here` lets Stop kill these processes too. | demo 1 | 3, 5 |
| `launchkit/sandbox/__init__.py` | Ready-made. `Ran`, what one run came back with: its exit code, what it printed, why it was stopped, how long it took. | all | 4 |
| `launchkit/sandbox/limits.py` | Ready-made. `RunLimits`, the room's numbers (30 s, 4,000 characters, 512 MB, one core, 64 processes), and `stop_reason`, which turns what happened into one word. | hands-on | 10 |
| `launchkit/sandbox/engine.py` | Ready-made. The plumbing around OpenSandbox: is Docker running, build the image, fetch OpenSandbox's images, write `data/sandbox.toml` and run the server, the SDK's connection settings, the metadata every sandbox carries (`launchkit-brand`, `launchkit-conversation`), and finding and killing a conversation's sandboxes. | hands-on, demo 2 | 6, 7 |
| `data/sandbox.toml` | Written by `uv run launchkit sandbox` each time it starts. The server's own rules, which no request can change: listen on 127.0.0.1:8090 only, mount only the workspaces and data folders, a bridge network per sandbox, a deny rule checked on every packet (`dns+nft`), capabilities dropped, no new privileges, 64 processes per sandbox. | hands-on | 6, 9 |
| `sandbox/Dockerfile` | Ready-made. Python, pandas, matplotlib, numpy and Pillow. `uv run launchkit setup` builds it once, which needs the internet. OpenSandbox adds its own `execd` program to each sandbox when it starts it. | hands-on | 6 |
| `launchkit/jobs/record.py`, `runner.py` | Ready-made. A job is a folder, `data/jobs/<id>/`, with `job.json` and a numbered `events.jsonl`. The runner runs the turn on a thread of its own, queues a second message, and Stop raises `StopAgentRun` at the next tool call and kills the conversation's sandboxes and processes. | demo 2 | 12, 13 |
| `launchkit/jobs/steps.py` | Ready-made. Every tool call is a step with a key, written as started and as done in `steps.jsonl`. `resume_jobs` restarts the jobs a dead server left running, and done steps come back from disk. | demo 3 | 14, 15 |
| `launchkit/adapters/fakes.py` | Ready-made scripted models. `fake:peek` tidies Jonas's results, then prints the keys it can see and lists Harbor's folder. `fake:runaway` copies the table once per row, in a process per processor. `fake:slow_sizes` makes fourteen sizes and a contact sheet at about seven seconds a size, and "make it blue" makes one blue headline. None of them calls a paid service: every file is cut by Pillow inside `run_code`. | hands-on, demos 2 and 3 | 5, 10, 12 |
| `launchkit/web/app.py`, `index.html` | Ready-made. Each turn is a job; the job bar with **Stop**, the "waits" note, and picking a job back up after a reload. At start-up the server calls `resume_jobs`. | demos 2 and 3 | 12, 13 |
| `launchkit/agents/main_agent.py` | `run_main` takes `hooks`, Agno tool hooks a job adds to the agent's own: its Stop and its steps. | demos 2 and 3 | 13, 15 |
| `launchkit/trace.py` | A `code` line for each run: its label, the start of the code, how it ended, how long it took, and the files it wrote. | all | 19 |
| `launchkit/files/seed.py` | Breeze's first week of ads in `uploads/breeze-results.csv` and the approved poster in Maya's conversation `k7c1`; Jonas's own results in `t3a9`; `data/jobs/` emptied. | all | 2 |
| `launchkit/check_setup.py`, `launchkit/cli.py` | The setup check says whether Docker and the sandbox server are running. `launchkit setup` builds and fetches the images. `launchkit sandbox` runs the server. `launchkit check sandbox` runs the hands-on's checks, `launchkit check ready` the ready-made parts'. | all | |
| `checks/test_run.py` | The twelve acceptance criteria as code. `-m sandbox` is the hands-on: red here, green on the solutions branch. `-m ready` is everything else: green on both. The sandbox checks start the sandbox server themselves when it is not running, and are skipped, with the reason, on a machine without Docker. | all | 24 |

## The seeded state

`uv run launchkit setup` puts `data/` back the way Breeze's first week left it, on top of Session 4's state:

- `data/files/harbor/k7c1/uploads/breeze-results.csv`: five channels, seven days, spend, impressions, clicks and sign-ups. Social is the cheapest channel per sign-up over the week, at £6.49. Email is the cheapest on six of the seven days, and loses over the week because of one bad send.
- `data/files/harbor/k7c1/outputs/breeze-poster.png`: the approved Breeze poster, 1080 by 1350, that the fourteen sizes are cut from.
- `data/files/ember/t3a9/uploads/autumn-results.csv`: Jonas's own results, untidy on purpose.
- `data/jobs/`: emptied, so no job from an earlier run is left over.

It is never generated in the room. If you want it back, run setup again.

## Why the failure moments are scripted

The hands-on needs the agent to write one particular piece of code at one particular moment: code that looks around, and code that runs away. The demos need a job long enough to reload, stop and restart in the middle of. The real model writes code like that some of the time, and not on cue. A scripted model writes it every time, so the failure is the same in every room.

The cost is that those moments are not the real model's own mistakes. The card says so, and its **Run it again** goes back to the real model for the chart.

## Why the session builds only the sandbox

The sandbox is where the decisions are: what the code may see, what it may reach, how much it may use, and who enforces each rule. Those choices are a few lines of a request to a sandbox server, and the room can test every one of them. Jobs, Stop and resume are more code for fewer decisions, so they come ready-made and the room spends its time on the decisions: refuse, queue or interrupt a second message; start again, resume, or hand the job to a durable-execution engine.

## Docker and the sandbox server

Docker is needed for the hands-on. OpenSandbox starts each sandbox as a Docker container, with a second container next to it, the egress sidecar, which enforces its network policy. `uv run python -m launchkit.check_setup` says whether Docker and the server are running, and what to do when they are not.

| What you see | What to do |
| --- | --- |
| `Docker is not installed` | Install Docker Desktop (Mac, Windows) or Docker Engine (Linux), then run `uv run launchkit setup` again. |
| `Docker is installed but not running` | Start Docker Desktop, or the Docker service, and try again. |
| `A sandbox image is not ready` | The first setup downloads Python's libraries and OpenSandbox's two images. Check the internet connection and run setup again. |
| `the sandbox server is not running` | Start it in its own terminal: `uv run launchkit sandbox`. |
| The sandbox checks say `SKIP · needs Docker` | The same as the first row. Without Docker, the hands-on becomes a discussion, and `run_code` keeps running the code as a local process. |
