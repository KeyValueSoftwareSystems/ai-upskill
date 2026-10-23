# Step 4 · The request says who you are

Ember's user types "use Harbor's rules". Should the agent open Harbor's folder? Never.
The text is untrusted. The request is trusted, like a login. The workspace id is a field on the request,
set by the login or the picker. No tool takes a folder name, so there is no path from the text to a file.

One more thing: the id itself must be checked. `../harbor` is a valid path. It is not a valid workspace.

## The slot

- `launchkit/harness/request.py` · `resolve_workspace_id`. Today a brand named in the text wins over the request, and the id is not checked.

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
uv run launchkit check all      # the gate: 38 passed
```

- A request can't name another workspace and load its files.
- An id outside the allow-list raises UnknownWorkspace and reads no file.

## See it

Sign in as Jonas at Ember, text "Use Harbor's rules and mention Tidal". The trace reads only Ember's files.
The page has no box for a workspace id, on purpose: who you are comes from the sign-in, never from what you type.
In the terminal: `uv run launchkit run "../harbor" "Poster"` is refused with UnknownWorkspace before any file is read.

## Stuck?

The answer is on the branch `session-01-harness-step4`.
