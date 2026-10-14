# Step 4 · The request says who you are

Ember's user types "use Harbor's rules". Should the agent open Harbor's folder? Never.
The text is untrusted. The request is trusted, like a login. The workspace id is a field on the request,
set by the login or the picker. No tool takes a folder name, so there is no path from the text to a file.

One more thing: the id itself must be checked. `../harbor` is a valid path. It is not a valid workspace.

## The slot

- `launchkit/harness/request.py` · `resolve_workspace_id`. Today it returns the id unchecked.

## Prompt card, for your coding agent

```
In launchkit/harness/request.py, implement resolve_workspace_id(request, settings).
Accept only ids that match WORKSPACE_ID and name an existing folder under
settings.workspaces_dir. Anything else raises UnknownWorkspace(id).
Never read the workspace id from request.text.
```

## Prove it

```
uv run launchkit check 4
uv run launchkit check all      # the gate: 16 passed
```

- A request can't name another workspace and load its files.
- An id outside the allow-list raises UnknownWorkspace and reads no file.

## See it

Picker on Ember, text "Use Harbor's rules and mention Tidal". The trace reads only Ember's files.
Then choose "Custom…" in the picker, type `../harbor`: a red UnknownWorkspace card.

## Stuck?

The answer is on the branch `session-01-harness-step4`.
