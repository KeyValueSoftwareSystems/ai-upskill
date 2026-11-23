# Runtime hands-on · Walled off, with limits

> Jonas, Ember: "I asked it to tidy my results file. It did. It also printed LaunchKit's API keys into my chat, and listed the files in Harbor's conversation."
>
> Maya, Harbor, the same afternoon: "I asked for cost per sign-up. It sat there for half a minute. Jonas said his poster took forever at the same time."

This is the session's one hands-on. The agent already has a code tool, `run_code`, and it works: asked for the cheapest channel, it writes Python, runs it on `uploads/breeze-results.csv`, and answers Social, £6.49, every time. But the code runs as a child process of LaunchKit's server, with everything the server has. You move it into a sandbox from OpenSandbox, an open-source sandbox server, and give every run a budget.

## Before you start

The room starts on `session-05-runtime-prd`. You need Docker running. Three terminals:

```
uv run launchkit setup       # once: puts data/ back, builds the sandbox image, fetches OpenSandbox's two images
uv run launchkit sandbox     # terminal 2: the OpenSandbox server, on 127.0.0.1:8090; leave it running
uv run launchkit ui          # terminal 3: the chat page
```

`launchkit sandbox` writes the server's settings to `data/sandbox.toml` and starts it. Read that file once. It decides things no request can change: which host folders a sandbox may mount, that every sandbox gets its own network, that a deny rule is checked on every packet, and the process limit.

## The slot

- `launchkit/sandbox/opensandbox.py` · `run_in_sandbox`, `oom_kills`. Today each raises.
- `launchkit/tools/run_code.py`: today `run_code` calls `run_here` from `launchkit/sandbox/local.py`, a process on this machine, with no sandbox.

Ready-made, and worth reading first: `launchkit/sandbox/engine.py`, the plumbing around the server (connection settings, the metadata every sandbox carries, finding and killing a conversation's sandboxes), and `launchkit/sandbox/limits.py`, the numbers and `stop_reason`.

## Break it first

**What the code can reach.** Sign in as **Jonas at Ember** and open his conversation, `t3a9`, which starts "Autumn poster for the Night Shift roast". Set **Model** to `fake:peek` and send:

> Tidy my results file, please.

`fake:peek` is a scripted model: it writes the same code every time. That code tidies `uploads/autumn-results.csv`, then looks around. The reply shows what it printed:

```
Tidied 6 rows into outputs/autumn-results-tidy.csv
Keys this code can see: LITELLM_API_KEY=sk-..., IMAGESVC_KEY=...
../../harbor -> k7c1
../../harbor/k7c1/outputs -> breeze-poster.png, campaign-brief.md
```

The keys are cut to six characters so the projector doesn't show them whole. Nothing else stopped them. Turning off a file tool doesn't help: the code opened the files itself.

**What the code can use.** Open a second window. As **Maya at Harbor**, in `k7c1`, set **Model** to `fake:runaway` and send:

> Work out the cost per sign-up by channel from the results.

In the first window, as Jonas, leave **Model** empty and ask for a poster. `fake:runaway`'s code copies the table once per row, in one process per processor. Watch the activity monitor: every core busy, memory past a gigabyte. After thirty seconds the run is stopped, and the trace says only `stopped: time`.

## Prompt card, for your coding agent

```
Code the agent writes runs as a child of LaunchKit's server: it reads every key and every brand's folder, and one
runaway takes the whole machine. Build Session 5's hands-on: run it in an OpenSandbox sandbox, with limits. Read
TICKETS.md (the hands-on), launchkit/sandbox/opensandbox.py, launchkit/sandbox/engine.py and launchkit/sandbox/limits.py.

1. launchkit/sandbox/opensandbox.py: fill in run_in_sandbox(workspace, code, limits) -> Ran. One sandbox per run,
   from opensandbox.sync.sandbox.SandboxSync.create(engine.IMAGE, connection_config=engine.connection(), ...) with:
     timeout          timedelta(seconds=limits.seconds + 60): a backstop the server enforces on its own
     env              {}
     metadata         engine.labels(workspace.brand, workspace.conversation)
     resource         {"cpu": str(limits.cpus), "memory": f"{limits.memory_mb}Mi"}
     network_policy   NetworkPolicy(default_action="deny", egress=[])
     volumes          Volume(name="work", host=Host(path=<workspace.root, resolved>), mount_path="/work", read_only=False)
                      Volume(name="brand", host=Host(path=<workspace.shared, resolved>), mount_path="/brand", read_only=True)
   Then sandbox.commands.run(shlex.join([*CLEAN_ENV, "python", "-I", "-c", code]), opts=RunCommandOpts(
   working_directory="/work", timeout=timedelta(seconds=limits.seconds), uid=<uid>, gid=<gid>)) with sandbox_user().
   The output is the stdout and stderr messages in timestamp order, each message's text joined with newlines. A run
   that took limits.seconds - 0.5 seconds or more timed out, and its exit code is None. If commands.run raises
   SandboxException, the sandbox went away mid-run: return stopped="killed". Return
   Ran(exit_code, output, stop_reason(exit_code, timed_out, oom_killed, output), seconds). Kill and close the sandbox
   in a finally, whatever happened.

2. oom_kills(sandbox) -> int: run `cat /sys/fs/cgroup/memory.events` in the sandbox and return its oom_kill count,
   0 if anything fails. run_in_sandbox calls it only when the exit code is not 0, and before the sandbox is killed.

3. launchkit/tools/run_code.py: run_code calls run_in_sandbox instead of run_here. When engine.server_problem() returns
   a reason, it does not run the code at all: trace.refused("run_code", "no sandbox: <reason>") and return "The code
   did not run: the sandbox is not available (<reason>)." Add the reasons "memory" ("the run used more than its memory
   limit of <memory_mb> MB") and "processes" ("the run tried to start more than <processes> processes"). Change the
   Entry's note: the code runs in a sandbox, in this conversation's folder at /work, with the brand's own files
   read-only at /brand; pandas, matplotlib, numpy and Pillow are there; there is no internet.

Do NOT: keep a sandbox between runs; allow any network; pass any environment variable from the server; change
engine.py or data/sandbox.toml.

Done when `uv run pytest checks/test_run.py -m sandbox` passes.
```

## Prove it

```
uv run pytest checks/test_run.py -m sandbox
```

- Code run for Jonas can't list Harbor's folder, by `..` or by its full path. It can read Ember's brand book at `/brand` and can't change it, and it doesn't run as root.
- No key the server holds is in the code's environment.
- The code can't connect to anything, by address or by name.
- The code runs in `/work`, and when the run ends its sandbox is gone. Without the sandbox server, the code doesn't run at all.
- The sandbox's own cgroup holds one core, 512 MB and 64 processes. A run past its memory or its processes is stopped, and the trace says which.
- While Jonas's code burns every core it can, Maya's code still runs at once.

`uv run pytest checks/test_run.py -m ready` checks the ready-made pieces. It passes before and after the hands-on.

## Run it again

As Jonas, with `fake:peek`, send the same message. The file is tidied. The reply says `Keys this code can see: none`, and both Harbor paths say `FileNotFoundError`: inside the sandbox, `/work/../..` is the sandbox's own root. Watch terminal 2: the server starts one sandbox for the run and removes it after.

As Maya, run `fake:runaway` again. It is stopped within seconds, and the trace and the reply say `memory`, with the number. Jonas's poster carries on.

Then, as Maya with **Model** empty, ask for a chart:

> Draw daily spend by channel as a chart and save it in outputs.

The chart is made with matplotlib inside the sandbox, and it appears with the message that asked for it.

## Why it matters

The decision is where the agent's code runs, and the room compares five options:

- **Take the keys out of the server's process.** Nothing hides the other brands' folders.
- **A container you start yourself**, with `docker run`. You choose every setting, and you write the lifecycle, the limits and the network rules yourself.
- **A sandbox server, such as OpenSandbox.** The same container underneath, behind an API: create, run, delete. The server owns the settings that must hold for every sandbox. Its Kubernetes runtime can use Firecracker micro-VMs, with the same API.
- **A micro-VM**, such as Firecracker, run yourself. A kernel of its own: the strongest boundary here, and the most to operate. Pencil does this.
- **A hosted sandbox**, such as E2B or Modal. Someone else runs one of the above. You pay per second and send them the data.

Two gaps to name before moving on. OpenSandbox's Docker runtime sets a memory limit and leaves swap on, so a runaway uses about as much again in swap before it is killed. Nothing caps how much a run writes into `/work`, which is a folder on the host's disk.

The fix is not a better filter on what the code may do. It is a place where the code can see nothing it shouldn't, and can't use more than its share.
