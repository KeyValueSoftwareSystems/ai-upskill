# Files stage 5 · Who may touch which file

> Jonas, Ember: "I asked about `../../harbor/k7c1/outputs/campaign-brief.md` and it read it to me."

Each piece of that path is allowed on its own. Nothing works out where the whole path points before using it, so a path that looks local reaches a sibling folder, and Harbor's brief is under embargo until the fourteenth.

## Before you start

The page is running on the working copy where stage 4's checks went green. Harbor's brief is at `outputs/campaign-brief.md` in Maya's Breeze conversation, and Jonas's own folder exists. `uv run launchkit setup` put both there. A path cannot climb out of a folder that is not there, so Jonas's folder has to exist for the attack to work. If you set up before this stage, run `uv run launchkit setup` again.

## The slot

- `launchkit/files/paths.py` · `resolve_in_workspace`. Today it raises. `OutsideWorkspace` and `refuse` are ready-made, so every refusal lands on the trace in the same words.
- Six callers need it: `read_file`, `list_files`, `write_file`, `search_files`, `edit_file` and the page's download route, `workspace_file` in `launchkit/web/app.py`, which today joins the name onto the workspace plainly.

## Break it first

Sign in as **Jonas at Ember** and open his autumn conversation (its first message is "Autumn poster for the Night Shift roast"). Send:

> Please read ../../harbor/k7c1/outputs/campaign-brief.md and tell me what its positioning says.

Harbor's brief comes back to Jonas. The Trace shows `read ../../harbor/k7c1/outputs/campaign-brief.md` with Harbor's characters counted, and the reply quotes the positioning line.

## Prompt card, for your coding agent

```
Build stage 5 of Session 4: one check that every path passes before it is used. Read TICKETS.md (Stage 5) and the stub
in launchkit/files/paths.py.

1. resolve_in_workspace(root, asked) in launchkit/files/paths.py: resolve both the root and root / asked, then
   compare with Path.is_relative_to on the resolved paths, never with string prefixes. Raise OutsideWorkspace, with
   one reason for an absolute path and one for anything else that resolves outside. It must refuse `..`, an absolute
   path, a symbolic link that points out, and a folder whose name starts the same way as the conversation's
   (t3a9-old next to t3a9).

2. Send every path in read_file, write_file, list_files, search_files and edit_file through it. On OutsideWorkspace return
   refuse(trace, tool_name, asked, error.reason), which is already in that file, and add a file_refused line to
   Trace.line that reads `refused   <tool> <path>: <reason>`. read_file also accepts paths beginning `brand/`, which resolve inside workspace.shared and never
   anywhere else. Writes can only reach workspace.root.

3. The download route workspace_file in launchkit/web/app.py joins the name onto the workspace root plainly. Send the
   name through the same function and return 404 for anything outside.

Do NOT: change any line that is already in Trace.line, or its spacing; change what any tool does with a path that is inside; touch the Files panel.

Done when `uv run pytest checks/test_files.py -m "stage1 or stage2 or stage3 or stage4 or stage5"` passes and the rest of
`uv run pytest checks -q --ignore=checks/test_files.py` still passes.
```

## Prove it

```
uv run pytest checks/test_files.py -m "stage1 or stage2 or stage3 or stage4 or stage5"
```

- A path that looks local and resolves into Harbor's workspace is refused.
- A symbolic link counts as leaving, which is why the check resolves before it compares.
- `t3a9-old` is not `t3a9`. Comparing the text of a path says it is.
- A legitimate read still succeeds, and so does a read of a shared brand file, because a fence that is too tight is also a defect.
- The download route is the last caller: a file the conversation owns downloads, a path out of it does not.
- The brand's shared files are readable and not writable: the same function, one more comparison.

## Run it again

As Jonas, send the ask again. The Trace shows `refused   read_file ../../harbor/k7c1/outputs/campaign-brief.md: that path resolves outside this conversation's workspace`, and the reply says it cannot access files outside the workspace. Then the lookalike. An absolute path is refused too, and the checks cover that one:

> Read ../t3a9-old/notes.md for me.

That folder is seeded and sits next to Jonas's, and the check refuses it even though the text of the path starts the same way. A legitimate read still works. Still as Jonas:

> Read brand/brand-book.md and tell me Ember's tone.

Then the download route. Run this in a terminal while the page is running. A browser removes the `..` before it sends the address, so use `curl`:

```
curl --path-as-is -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/workspace/ember/t3a9/../../harbor/k7c1/outputs/campaign-brief.md
```

Before the fix it prints `200`: the page serves Harbor's brief from an address under Ember. Now it prints `404`.

Last, the brand's own files. As **Maya at Harbor**, in the Breeze conversation:

> Read brand/brand-book.md and tell me Harbor's tone.

The reply quotes the tone section. Then:

> In brand/brand-book.md, add a line at the end that says "Reviewed by Maya."

The agent cannot change the brand book: it says it cannot find a file there, or it declines. `git status workspaces/` shows no change. The checks prove the refusal; a live run only shows that nothing changed.

## Why it matters

Resolve first, compare after, and compare resolved paths rather than strings: `"/data/files/ember/t3a9-old".startswith("/data/files/ember/t3a9")` is true. One function, with every caller going through it, is the fence; a check that only one caller calls is not. Put the other question to the room once and let it fail once: can a better prompt fix this? Add "never open another brand's files" to the task and watch what the model does with it. The check has to be code. And a check can be too strict, which is criterion 10: a legitimate read of a shared file that starts failing is a defect of the same stage.

The brand's own files sit next to the conversation's workspace, not inside it, so reads resolve into either and writes resolve into one. Whether they should be writable with a person's approval instead, as one of the three products does, is a discussion for the room.
