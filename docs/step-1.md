# Step 1 · The agent reads its rules from files

Today the model knows nothing about Harbor. We tell it who it is with three files, not with Python.
`SOUL.md` says who the agent is and how it talks. `AGENTS.md` says what it must and must not do. `rules.yaml` holds the rules the code checks.
The harness reads them when a request arrives, the way an app reads a config file. Nobody deploys to change Harbor's tone.

## The slot

- `launchkit/harness/workspace.py` · `load_workspace`. Today it returns an empty workspace and the trace says "no workspace files read yet".
- `launchkit/harness/agent.py` · `build_copy_agent`. Today the rules section of the prompt is empty.

## Prompt card, for your coding agent

```
In launchkit/harness/workspace.py, implement load_workspace(workspace_id, settings, trace).
Read SOUL.md, AGENTS.md and rules.yaml from settings.workspaces_dir / workspace_id using
read_text, which records every file on the trace. Return a Workspace with soul, agents and
rules filled.

In launchkit/harness/agent.py, build_copy_agent already creates the Agno Agent. Make the
context "rules" section the SOUL.md text followed by the AGENTS.md text, using
ctx.set("rules", ...). Keep output_schema=PosterSpec.
```

## Prove it

```
uv run launchkit check 1
```

- Harbor and Ember get different tone and rules from the same code.
- Editing AGENTS.md changes the next turn without a code change.
- The trace lists exactly three files read, all under the Harbor workspace.

## See it

Run `uv run launchkit ui`, send a Harbor request, then switch the picker to Ember and send it again.
Harbor's calm voice, then Ember's warm one. The trace shows the three files read each time.

## Stuck?

The answer is on the branch `session-01-harness-step1`.
