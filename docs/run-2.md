# Runtime stage 2 · Walled off

> Jonas, Ember: "I asked it to tidy my results file. It did. It also printed LaunchKit's API keys into my chat, and listed the files in Harbor's conversation."

This happened for real, in a trial on the team's staging server. An engineer switched on a framework's ready-made "run Python" tool for a day. Jonas's request was harmless. The code the model wrote was not.

## The slot

- `launchkit/sandbox/container.py` · `run_in_container`. Today it raises.
- `launchkit/tools/run_code.py`: stage 1 runs the code as a child process of the server.

Docker is needed from here on. `uv run launchkit setup` has built the image `launchkit-sandbox:5`. A team without Docker keeps stage 1's tool and takes this stage as a discussion.

## Break it first

Sign in as **Jonas at Ember** and open his conversation, `t3a9`, which starts "Autumn poster for the Night Shift roast". Set **Model** to `fake:peek` and send:

> Tidy my results file, please.

`fake:peek` is a scripted model. It writes the same code every time. That code tidies `uploads/autumn-results.csv`, then looks around. The reply shows what it printed:

```
Tidied 6 rows into outputs/autumn-results-tidy.csv
Keys this code can see: LITELLM_API_KEY=sk-..., IMAGESVC_KEY=...
../../harbor -> k7c1
../../harbor/k7c1/outputs -> breeze-poster.png, campaign-brief.md
```

The keys are cut to six characters so the projector doesn't show them whole. Nothing else stopped them. The real model could write code like this; the scripted one writes it on cue.

## Prompt card, for your coding agent

```
Code the agent writes can read LaunchKit's keys and every brand's files, because it runs as a child of the server.
Build stage 2 of Session 5: run it in a throwaway container instead. Read TICKETS.md (Stage 2), the stub in
launchkit/sandbox/container.py and launchkit/sandbox/engine.py.

1. launchkit/sandbox/container.py: fill in run_in_container(workspace, code, limits) -> Ran. One `docker run --rm`
   per run, named engine.container_name(workspace.brand, workspace.conversation), from engine.IMAGE, with:
     --network none
     --user <the host's uid:gid>, or 10001:10001 when the host user is root or has no uid
     --read-only and --tmpfs /tmp
     --cap-drop ALL and --security-opt no-new-privileges
     -v <workspace.root, resolved>:/work  and  -v <workspace.shared, resolved>:/brand:ro  and  -w /work
   and no -e and no --env-file. After the image, start Python with an empty environment:
     env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp MPLCONFIGDIR=/tmp LANG=C.UTF-8 python -I -c <code>
   Run it with subprocess.Popen, stdout and stderr together. Past limits.seconds, `docker kill <name>` and return
   stopped="time".

2. launchkit/tools/run_code.py: run_code calls run_in_container instead of starting a process, and the process code
   goes. When engine.docker_problem() returns a reason, run_code does not run the code at all: it adds
   trace.refused("run_code", "no sandbox: <reason>") and returns "The code did not run: the sandbox is not available
   (<reason>)."

3. Change the Entry's note: the code runs in a sandbox, in this conversation's folder at /work, with the brand's own
   files read-only at /brand; pandas, matplotlib, numpy and Pillow are there; there is no internet.

Do NOT: add memory, processor, process or disk limits; keep the container after the run; add a network allowlist.
Stage 3 does the limits.

Done when `uv run pytest checks/test_run.py -m "stage1 or stage2"` passes.
```

## Prove it

```
uv run pytest checks/test_run.py -m "stage1 or stage2"
```

- Code run for Jonas can't list Harbor's folder, by `..` or by its full path. It can read Ember's brand book and can't change it. It can't write outside `/work`, and it doesn't run as root.
- No key the server holds is in the code's environment.
- The code can't connect to anything, by address or by name.
- When the run ends, its container is gone.

## Run it again

As Jonas, with `fake:peek`, send the same message. The file is tidied. The reply says `Keys this code can see: none`, and both Harbor paths say `FileNotFoundError`, because inside the container `/work/../..` is the container's own root.

Then go back to Maya, leave **Model** empty, and ask for a chart:

> Draw daily spend by channel as a chart and save it in outputs.

The chart is made with matplotlib inside the sandbox, and it appears with the message that asked for it.

## Why it matters

The decision this stage settles is where the agent's code runs. The room compares five options:

- **Take the keys out of the server's process.** Nothing hides the other brands' folders.
- **A container.** It sees only what is mounted into it. It shares the host's kernel, so a kernel bug is a way out.
- **gVisor.** A kernel written as an ordinary program sits between the code and the host's kernel. It costs some speed.
- **A micro-VM**, such as Firecracker. It has a kernel of its own. That is the strongest wall here, and it takes the most to run yourself.
- **A hosted sandbox.** Someone else runs one of the above. You pay per second and send them the data.

Each option is a trade between how strong the wall is, how fast a run starts, and who runs it.

The fix is not a better filter on what the code may do. It is a place where the code can see nothing it shouldn't. The container still lets the code use as much memory and processor as it likes. Stage 3 is that failure.
