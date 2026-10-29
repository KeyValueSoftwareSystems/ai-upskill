# Step 5 · Permissions: read freely, ask before you write

Maya: "Put the new sizes on the Tidal card." The card already holds last week's approved files. The agent attaches the new sizes and, trying to keep the card clean, removes last week's approved files. She never asked for a delete. It usually behaves. Usually.

Every tool already says what it does: read (looks only) or write (changes something outside LaunchKit). The board's server says it for its own tools. The fix: `run_tool` lets reads run, and a write stops and asks Maya, with exactly what it is about to change. She says yes or no. The model cannot talk its way past this, because the rule lives in code.

Step 3 made `run_tool` the one door for every tool. So one rule covers every tool, today's and tomorrow's, including the ones an outside MCP server adds, and every caller.

This is Session 1's leash, grown up. The leash caps how much the agent can spend; this caps what it can change. Paid tools (`generate_image`, `text_to_speech`) stay under the budget leash; only outside writes ask Maya.

## The slot

- `launchkit/harness/catalogue.py` · `run_tool`. Today it runs a write without asking.

## Break it first

```
uv run launchkit main harbor "Put the new sizes on the Tidal card." --model fake:tools
```

```
  tool      run_tool("remove_files", {'card': 'tidal', 'files': ['tidal-feed-1080x1080-approved.png', …]}) → Removed 2 files from tidal.
```

The fake runs on the local board and shows the cleanup every time. On the real model it is rare: if it does not happen on the day, show it here and say so.

## Prompt card, for your coding agent

```
In launchkit/harness/catalogue.py, in run_tool, after the inputs check and before
the tool runs: if entry.kind == "write" and not self.approve(name, inputs), record
self.trace.refused(name, "Maya said no") and return "Maya did not allow {name}. Do
not try it again; tell her what you wanted to do." Reads never ask.
```

`self.approve` is ready-made: in the terminal it prints the tool and its inputs and asks "Allow? [y/N]".

## Prove it

```
uv run launchkit check tools5
```

- A write asks Maya first, with what it is about to change; a no means it never runs.
- A yes lets the write through; a read never asks.
- Putting the sizes on the Tidal card, last week's approved files survive.

## Run it again

The same ask on the fake. The terminal asks before each write. Say yes to `attach_files` and `update_status`, no to `remove_files`. The card ends up with both weeks' files, ready for review.

Then on the real model and your Notion: `uv run launchkit main harbor "Put these new sizes on the Tidal card: tidal-feed-1080x1350.png, tidal-web-1200x628.png. Then move it to Ready for review."` Notion's server marks its own tools, and the same rule asks before `notion-update-page` and `notion-create-comment`. Read what each one is about to change before you say yes. `uv run launchkit notion` sets the card back.

## Stuck?

The answer is on the branch `session-02-tools-step5`.
