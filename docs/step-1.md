# Step 1 · The agent reads its rules from files

Today the model knows nothing about Harbor. We tell it who it is with three files, not with Python.
`SOUL.md` says who the agent is and how it talks. `AGENTS.md` says what it must and must not do. `rules.yaml` holds the rules the code checks.
The harness reads them when a request arrives, the way an app reads a config file. Nobody deploys to change Harbor's tone.

## The slot

- `launchkit/harness/workspace.py` · `load_workspace`. Today it returns an empty workspace and the trace says "no workspace files read yet".
- `launchkit/harness/agent.py` · `build_copy_agent`. Today the rules section of the prompt is empty.

## Break it first

Before you paste the card, run this and keep the output:

```
uv run launchkit run harbor "Poster for the Tidal bottle on a misty lakeshore at dawn. Headline idea: cold for 24 hours." --model fake:echo
```

```
  note      no workspace files read yet, step 1 fills this
  subheadline   rules section is 0 characters
  body          No rules were given.
```

The model was asked for Harbor's poster and was told nothing about Harbor.

## Prompt card, for your coding agent

```
In launchkit/harness/workspace.py, implement load_workspace(workspace_id, settings, trace).
Read SOUL.md, AGENTS.md and rules.yaml from settings.workspaces_dir / workspace_id using
read_text, which records every file on the trace. Return a Workspace with soul, agents and
rules filled.

In launchkit/harness/agent.py, build_copy_agent already creates the Agno Agent. Make the
context "rules" section the SOUL.md text followed by the AGENTS.md text, using
ctx.set("rules", ...). Keep output_schema=Turn.
```

## Prove it

```
uv run launchkit check 1
```

- Harbor and Ember get different tone and rules from the same code.
- Editing AGENTS.md changes the next turn without a code change.
- The trace lists exactly three files read, all under the Harbor workspace.

## Run it again

The same command after the build:

```
  file      read workspaces/harbor/SOUL.md
  file      read workspaces/harbor/AGENTS.md
  file      read workspaces/harbor/rules.yaml
  body          You are Harbor's poster copywriter. Calm, outdoorsy, quietly confident.
```

## Why it matters

Behaviour is config, not code. Editing a file changes the next turn, and a new brand is a new folder, not a new prompt in Python.

## See it

Run `uv run launchkit ui`, sign in as Maya at Harbor, send a request, then sign in as Jonas at Ember and send it again.
Harbor's calm voice, then Ember's warm one. The trace shows the three files read each time.

## Stuck?

The answer is on the branch `session-01-harness-step1`.
