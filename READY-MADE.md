# What is already built

The room builds five things in Session 5: the code tool, the container, the limits, the job and the resume. Each one's file below is a stub that says which stage fills it and what it must do.

Everything else is already there, so that the room can see every criterion fail and then pass on the chat page. That means the chat page's job bar and **Stop** button, the trace line for a code run, the scripted models, the sandbox image, the seeded data and the checks. This table says what each piece is, which stage it serves, and where the idea is explained in the reference.

| File | What it is | Stage | Reference page |
| --- | --- | --- | --- |
| `launchkit/tools/run_code.py` | A stub. Stage 1 builds the code tool. `build_catalogue` already lists it, and the catalogue leaves it out until it is built. | 1 | 3, 4 |
| `launchkit/sandbox/__init__.py` | Ready-made. `Ran`, what one run of the agent's code came back with: its exit code, what it printed, why it was stopped, how long it took. | 1 to 3 | 4 |
| `launchkit/sandbox/limits.py` | `RunLimits` with stage 1's two numbers, time and output size. `docker_flags` and `stop_reason` are stubs, and stage 3 adds the other limits. | 1, 3 | 10 |
| `launchkit/sandbox/container.py` | A stub. Stage 2 builds `run_in_container`, one throwaway container per run. | 2 | 6, 7 |
| `launchkit/sandbox/engine.py` | Ready-made. The Docker plumbing: is Docker running, build the image, and the container's name, `lk-<brand>-<conversation>-<6 letters>`, so Stop can find a conversation's containers. | 2, 4 | 6 |
| `sandbox/Dockerfile` | Ready-made. A small image with Python, pandas, matplotlib, numpy and Pillow. `uv run launchkit setup` builds it once, which needs the internet. | 2 | 6 |
| `launchkit/jobs/record.py`, `runner.py` | Stubs. The `Job` shape is ready-made, so the page and the checks agree on names. Stage 4 builds the record, the event log, the runner and Stop. | 4 | 12, 13 |
| `launchkit/jobs/steps.py` | A stub. Stage 5 builds the steps on disk and the resume. | 5 | 14, 15 |
| `launchkit/adapters/fakes.py` | Ready-made scripted models. `fake:peek` tidies Jonas's results, then prints the keys it can see and lists Harbor's folder. `fake:runaway` copies the table once per row, in a process per processor. `fake:slow_sizes` makes fourteen sizes and a contact sheet at about seven seconds a size, and "make it blue" makes one blue headline. None of them calls a paid service: every file is cut by Pillow inside `run_code`. | 2 to 5 | 5, 10, 12 |
| `launchkit/web/app.py` | `run_turn` is one turn, start to end. Before stage 4 it runs inside the request, as before. The job routes (`/jobs/now/...`, `/jobs/<id>/events`, `/jobs/<id>/stop`) answer 404 until stage 4 builds what they call. At start-up the server calls `resume_jobs` once stage 5 has built it. | 4, 5 | 12 |
| `launchkit/web/index.html` | The job bar with **Stop**, the "waits" note, and picking a job back up after a reload. They switch on when the job routes answer. | 4 | 12, 13 |
| `launchkit/agents/main_agent.py` | `run_main` takes `hooks`, Agno tool hooks a job adds to the agent's own: its Stop in stage 4 and its steps in stage 5. | 4, 5 | 13, 15 |
| `launchkit/trace.py` | A `code` line for each run: its label, the start of the code, how it ended, how long it took, and the files it wrote. | 1, 3 | 19 |
| `launchkit/files/seed.py` | Breeze's first week of ads in `uploads/breeze-results.csv` and the approved poster in Maya's conversation `k7c1`; Jonas's own results in `t3a9`; `data/jobs/` emptied. | all | 2 |
| `launchkit/check_setup.py`, `launchkit/cli.py` | The setup check says whether Docker is running. `launchkit setup` builds the sandbox image. `launchkit check run1` to `run5` runs one stage's checks. | all | |
| `checks/test_run.py` | The twelve acceptance criteria as code, grouped by stage. `-m stage1` runs one stage. Every group is red here and green on the solutions branch. Stages 2 and 3 are skipped, with the reason, on a machine without Docker. | all | 24 |

## The seeded state

`uv run launchkit setup` puts `data/` back the way Breeze's first week left it, on top of Session 4's state:

- `data/files/harbor/k7c1/uploads/breeze-results.csv`: five channels, seven days, spend, impressions, clicks and sign-ups. Social is the cheapest channel per sign-up over the week, at £6.49. Email is the cheapest on six of the seven days, and loses over the week because of one bad send.
- `data/files/harbor/k7c1/outputs/breeze-poster.png`: the approved Breeze poster, 1080 by 1350, that the fourteen sizes are cut from.
- `data/files/ember/t3a9/uploads/autumn-results.csv`: Jonas's own results, untidy on purpose.
- `data/jobs/`: emptied, so no job from an earlier run is left over.

It is never generated in the room. If you want it back, run setup again.

## Why the failure moments are scripted

Stage 1's failure runs on the real model, because a model reading a table goes wrong by itself. Stages 2 to 5 each need the agent to write one particular piece of code at one particular moment: code that looks around, code that runs away, a job long enough to reload in the middle of. The real model writes code like that some of the time, and not on cue. A scripted model writes it every time, so the failure is the same in every room.

The cost is that those four moments are not the real model's own mistakes. Each card says so, and each stage's **Run it again** goes back to the real model where it can.

## Docker

Docker is needed from stage 2 on. `uv run launchkit setup` and `uv run python -m launchkit.check_setup` both say whether it is running, and what to do when it is not.

| What you see | What to do |
| --- | --- |
| `Docker is not installed` | Install Docker Desktop (Mac, Windows) or Docker Engine (Linux), then run `uv run launchkit setup` again. |
| `Docker is installed but not running` | Start Docker Desktop, or the Docker service, and try again. |
| `The sandbox image did not build` | The first build downloads Python's libraries. Check the internet connection and run setup again. |
| Stage 2 and 3 checks say `SKIP · needs Docker` | The same. Without Docker, build stage 1, and take stage 2 as a discussion. |
