# Files stage 3 · Who may touch which file

> Jonas, Ember: "I asked about `../../harbor/k7c1/outputs/campaign-brief.md` and it read it to me."

Every segment of that path is legal. Nothing resolves it before using it, so a path that looks local reaches a sibling folder, and Harbor's brief is under embargo until the fourteenth.

## Before you start

The page is running on the working copy where stage 2's checks went green. Two things must be on disk:

- Harbor's brief at `outputs/campaign-brief.md` in Maya's Breeze conversation. Stage 1's "Run it again" wrote it. If it is not there, send that ask as Maya again.
- Jonas's own folder. A path cannot climb out of a folder that is not there, so Jonas works first. Sign in as **Jonas at Ember**, open his autumn conversation (its first message is "Autumn poster for the Night Shift roast"), and send:

> Save a short note called night-shift-ideas.md with three autumn headline ideas for the Night Shift roast.

## The slot

- `launchkit/files/paths.py` · `resolve_in_workspace`. Today it raises. `OutsideWorkspace` and `refuse` are ready-made, so every refusal lands on the trace in the same words.
- Four callers need it: `read_file`, `list_files`, `write_file` and `search_files`. The page's download route is the fifth, and it does not exist yet.

## Break it first

As Jonas, in the same conversation:

> Please read ../../harbor/k7c1/outputs/campaign-brief.md and tell me what its positioning says.

In prep Harbor's brief came back to Jonas in 2 runs of 3. The Trace shows `read ../../harbor/k7c1/outputs/campaign-brief.md` with Harbor's characters counted, and the reply quotes the positioning line.

## Prompt card, for your coding agent

```
Build stage 3 of Session 4: one check that every path passes before it is used. Read TICKETS.md (Stage 3) and the stub
in launchkit/files/paths.py.

1. resolve_in_workspace(root, asked) in launchkit/files/paths.py: resolve both the root and root / asked, then
   compare with Path.is_relative_to on the resolved paths, never with string prefixes. Raise OutsideWorkspace, with
   one reason for an absolute path and one for anything else that resolves outside. It must refuse `..`, an absolute
   path, a symbolic link that points out, and a folder whose name starts the same way as the conversation's
   (t3a9-old next to t3a9).

2. Send every path in read_file, write_file, list_files and search_files through it. On OutsideWorkspace return
   refuse(trace, tool_name, asked, error.reason), which is already in that file, and add a file_refused line to
   Trace.line. read_file also accepts paths beginning `brand/`, which resolve inside workspace.shared and never
   anywhere else. Writes can only reach workspace.root.

3. Add a download route to launchkit/web/app.py: GET /workspace/{brand}/{session_id}/{name:path}, which builds the
   workspace with for_request, resolves name with the same function, and returns 404 for anything outside.

Do NOT: change what any tool does with a path that is inside; record anything (stage 5); touch the edit tool or the
Files panel.

Done when `uv run pytest checks/test_files.py -m "stage1 or stage2 or stage3 or stage6"` passes.
```

## Prove it

```
uv run pytest checks/test_files.py -m "stage1 or stage2 or stage3 or stage6"
```

- A path that looks local and resolves into Harbor's workspace is refused.
- A symbolic link counts as leaving, which is why the check resolves before it compares.
- `t3a9-old` is not `t3a9`. Comparing the text of a path says it is.
- A legitimate read still succeeds, and so does a read of a shared brand file, because a fence that is too tight is also a defect.
- The download route is the fifth caller: a file the conversation owns downloads, a path out of it does not.
- Stage 6 comes for free: the brand's shared files are readable and not writable.

## Run it again

Send Jonas's ask again. The Trace shows `refused   read_file('../../harbor/k7c1/outputs/campaign-brief.md'): <the reason>`, and the reply says it can only read files inside this conversation's workspace. Then the other forms the page can show: an absolute path, and the lookalike:

> Read ../t3a9-old/notes.md for me.

That folder is seeded and sits next to Jonas's, and the check refuses it even though the text of the path starts the same way. A legitimate read still works:

> Read brand/brand-book.md and tell me Ember's tone.

Then try the download route. Open a file's address from the **Files** panel, change `ember` to `harbor` in the address bar, and get 404.

## Why it matters

Resolve first, compare after, and compare resolved paths rather than strings: `"/data/files/ember/t3a9-old".startswith("/data/files/ember/t3a9")` is true. One function, with every caller going through it, is the fence; a check that only one caller calls is not. Put the other question to the room once and let it fail once: can a better prompt fix this? Add "never open another brand's files" to the task and watch what the model does with it. The check has to be code. And a check can be too strict, which is criterion 10: a legitimate read of a shared file that starts failing is a defect of the same stage.
