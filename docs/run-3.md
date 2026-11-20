# Runtime stage 3 · Contain the damage

> Maya, Harbor: "I asked for cost per sign-up. It sat there for half a minute. Jonas said his poster took forever at the same time."

A container decides what the code can see. It doesn't decide how much the code can use. One analysis that goes wrong takes every processor core and a gigabyte of memory, and every other conversation on the machine waits behind it. That is a noisy neighbour.

## The slot

- `launchkit/sandbox/limits.py` · `RunLimits`, `docker_flags`, `stop_reason`. Today `RunLimits` has only time and output size, and the two functions raise.
- `launchkit/sandbox/container.py`: stage 2's container, with no limits.

## Break it first

Open two windows on the chat page. In the first, sign in as **Maya at Harbor**, open `k7c1`, set **Model** to `fake:runaway` and send:

> Work out the cost per sign-up by channel from the results.

In the second, sign in as **Jonas at Ember**, leave **Model** empty, and ask for a poster:

> Autumn poster for the Night Shift roast, dark and warm.

`fake:runaway`'s code copies the whole table for every row it reads, in one process per processor. Watch your machine's activity monitor. Every core is busy, and memory climbs past a gigabyte. Jonas's turn waits on the model, which runs elsewhere, so on a laptop the slowdown may be small. The activity monitor is the place to watch, and on a server shared by forty brands every other run would be in the same queue for the same cores. After thirty seconds Maya's run is stopped, and the trace says only `stopped: time`. Nothing says what the run was actually doing wrong.

## Prompt card, for your coding agent

```
A container with no limits lets one run take every core and a gigabyte of memory. Build stage 3 of Session 5: limits,
and the reason a run was stopped. Read TICKETS.md (Stage 3) and launchkit/sandbox/limits.py.

1. launchkit/sandbox/limits.py: RunLimits gets the room's numbers: seconds 30, output_chars 4000, memory_mb 512,
   cpus 1.0, processes 64, disk_mb 100.

2. docker_flags(limits) returns ["--memory", "<memory_mb>m", "--memory-swap", "<memory_mb>m", "--cpus", "<cpus>",
   "--pids-limit", "<processes>", "--tmpfs", "/tmp:rw,size=<disk_mb>m"]. Memory-swap equal to memory means no swap.

3. stop_reason(exit_code, timed_out, oom_killed, output) returns, in order: "memory" when oom_killed; "time" when
   timed_out; when the exit code is not 0, "processes" if the output says "Resource temporarily unavailable" or
   "can't start new thread", "disk" if it says "No space left on device", "killed" for exit code 137 or -9;
   otherwise None.

4. launchkit/sandbox/container.py: the container carries docker_flags(limits) in place of stage 2's --tmpfs /tmp.
   Drop --rm. After the run, read `docker inspect -f {{.State.OOMKilled}} <name>`, then `docker rm -f <name>`, and
   return stop_reason(...) as the Ran's stopped.

5. launchkit/tools/run_code.py: the first line of what the agent is told names the limit with its number, for each
   reason: "the run used more than its memory limit of 512 MB", "the run tried to start more than 64 processes", "the
   run wrote more than its disk limit of 100 MB in /tmp", "the run was killed from outside, by Stop or by the machine".

Do NOT: change what the container can see; measure what a run wrote in /work (Docker cannot cap a folder it mounts,
and the room discusses that, not builds it).

Done when `uv run pytest checks/test_run.py -m "stage2 or stage3"` passes.
```

## Prove it

```
uv run pytest checks/test_run.py -m "stage2 or stage3"
```

- Every limit has a number, and every number reaches `docker run`.
- A run that eats memory, starts too many processes or fills `/tmp` is stopped. The trace and the agent both name the reason.
- While one conversation's code burns every processor, another conversation's code still runs in a moment. This check fails on stage 2's container: without the processor limit, the second run waits.

## Run it again

Send the same two messages in the two windows. Maya's run is stopped within seconds, and the trace says `stopped: memory`. The reply says "the run used more than its memory limit of 512 MB". The activity monitor shows one core busy, not all of them, and the check `test_one_run_never_slows_another_conversation` measures the difference.

## Why it matters

The decision this stage settles is a number for each limit, and what happens when a run reaches it. Two kinds of limit behave differently:

- **Memory and time kill the run.** The kernel kills a run that goes past its memory, and LaunchKit kills one that goes past its time.
- **Processes and disk only refuse.** The next process isn't started, or the next write fails, and the code stops with an error that it might even catch.

Being stopped with a reason is what separates a bug from an attack, once someone counts the reasons.

The disk limit covers `/tmp` only. `/work` is a folder on the host, and Docker can't cap a folder it mounts. On a Mac, Docker Desktop runs Linux in a virtual machine, so check that the `/tmp` limit holds there before relying on it.

The limits make one run safe for the machine. They do nothing for a run that is slow on purpose. Stage 4 is that failure.
