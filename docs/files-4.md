# Files stage 4 · How a file gets changed

> The reviewer, on Breeze: "Take out the lifetime-guarantee line." The trace shows the whole brief written again for one line.

The only way to change a file today is to write it again. The agent reads the brief, rewrites all of it, and sends every line back through `write_file`. Nothing checks that the line it was asked about was there, or was there once, and nothing can tell the line that was asked for from the lines that were not.

## Before you start

The page is running on the working copy where stage 3's checks went green. Harbor's brief must hold the line the reviewer objects to. As **Maya at Harbor**, in the Breeze conversation, send:

```
Replace the whole of outputs/campaign-brief.md with this text, exactly as written:

# Breeze campaign brief

## Positioning

avoid the lifetime-guarantee framing, two competitors use it

Breeze is the one you keep using, not the one you bought once.

## Tone

warm, plain, never clever

## Placements

square for social, tall for print
```

## The slot

- `launchkit/tools/edit_file.py` · `make_edit_file`. Today it does not exist, and nothing registers it.

## Break it first

As Maya, in the same conversation:

> The reviewer says the lifetime-guarantee line is wrong. In outputs/campaign-brief.md, change "avoid the lifetime-guarantee framing, two competitors use it" to "lead with the five-year warranty", and leave everything else in the file exactly as it is.

The agent uses `read_file` and then `write_file`, to write `outputs/campaign-brief.md` again rather than editing just the one line. The Trace shows `read outputs/campaign-brief.md` and then `wrote outputs/campaign-brief.md` with the whole file's characters counted: every line went back through the write tool for one line's change.

## Prompt card, for your coding agent

```
Build stage 4 of Session 4: an edit tool that changes one piece of a file and refuses when it is not sure.

launchkit/tools/edit_file.py: make_edit_file(workspace, trace, message="") returning an Entry with kind "read" and
edit_file(path, old_text, new_text). Join the path onto workspace.root the way the other tools do. Count
how many times old_text appears. If it appears zero times, change nothing and return a message that begins
"Not found". If it appears more than once, change nothing and return a message that begins "Ambiguous" and says how
many times. If exactly once, replace it, write the file and return "Edited <path>.". Like write_file, build a Record(workspace.root)
from launchkit/files/record.py when the tool is built, and call its add(path relative to the root, "edit_file",
message) after a successful edit. Also add a file_written trace line, showing the path and the number of characters in
new_text. Register it in build_catalogue, and word its Entry note this way: "pick me to edit, change, update or fix one line
or phrase in a saved file, brief or document without rewriting the rest: give the exact old text and the new text".

Do NOT: add an append mode, a line-range replace or a regular-expression mode; make it
check whether the file changed since the agent last read it.

Done when `uv run pytest checks/test_files.py -m "stage1 or stage2 or stage3 or stage4"` passes.
```

The last "do not" is why stage 2's bug gets past this tool. It checks the text it was given, not whether the file changed since it was read. It refuses when another writer has already removed its old text, and it allows a write that loses someone else's lines as long as its own old text is still there exactly once.

## Prove it

```
uv run pytest checks/test_files.py -m "stage1 or stage2 or stage3 or stage4"
```

- An edit replaces the text it was asked to replace and nothing else.
- It refuses when the old text is missing, and the file is untouched.
- It refuses when the old text appears more than once, and says how many.
- An edit is recorded the way a write is, so the **Files** panel lists the changed file.

## Run it again

Send the reviewer's ask again. The Trace shows one `edit_file` call that returns `Edited outputs/campaign-brief.md`, and one `wrote` line whose character count is the new text's, not the whole file's.

Then ask for a change that matches more than one place:

> In outputs/campaign-brief.md, change "the" to "a".

The Trace shows `edit_file` returning `Ambiguous: that text appears 3 times…`, and nothing is changed. The agent then usually reads the file and retries with more of the surrounding text, so its reply reports the change it made. Sometimes it widens the text on its own and the refusal never shows. Ask again in a fresh conversation, or rely on the check, which always shows it.

The other refusal, `Not found`, is covered by the checks and is rarely seen live: asked to change text that is not in the file, the agent usually searches the file first and tells you it is not there, without calling the edit tool.

## Why it matters

There are five ways to change a file: write it all again, replace a line range, replace an exact piece of text, apply a patch, or run a shell command. Four of them can change the wrong thing without telling you. What the room builds is one function that replaces exactly the text it was given, refuses when that text is missing, and refuses when it appears more than once. Hold on to that check, because stage 2's bug gets past it without a single failed match. Versioning and rollback are the other half of write safety, and every undo tool covers what it saw change and nothing else, so a file changed by something outside the tool does not come back.

What if the old text appears more than once? The tool refuses and says how many, because the agent cannot count well and a short word such as "the" is almost never meant everywhere. Other tools handle it in three ways. The agent adds surrounding text until the match is unique. An explicit replace-all flag, off unless the agent asks for it. Or an occurrence number, which breaks when the file changes between the read and the edit. Replace-all is right for renaming a term across a file, such as "lifetime guarantee" to "five-year warranty", and dangerous for a short word, and one flag does both jobs. So the room has three questions: who decides that every match is meant, should a replace-all ask Maya first, and should the refusal list each match with a line of context so the agent can pick one?

## Optional stretch: close the gap

Only if your team finishes early. Stage 4 left a gap on purpose: the edit tool checks the text it was given, and it does not check whether the file changed since the agent read it. A production system closes that gap. This stretch does it for one machine.

```
Stretch after stage 4 of Session 4: make edit_file refuse when the file moved on.

launchkit/tools/read_file.py: when it reads a file in the conversation's workspace, remember a SHA-256 fingerprint of the
file's bytes in workspace.seen, keyed by the file's resolved path. Add a `seen` dict field to Workspace in
launchkit/files/workspace.py (default empty, left out of equality and repr).

launchkit/tools/edit_file.py: take a lock for the file (one threading.Lock per resolved path, kept in a small helper
module launchkit/files/versions.py) and, inside the lock, in this order: read the file's bytes; if workspace.seen has no
fingerprint for the file, change nothing and return a message that begins "Read first"; if the fingerprint of the bytes
differs from the remembered one, change nothing and return a message that begins "Changed"; then do the existing
Not found, Ambiguous and replace steps, and after a successful write remember the new fingerprint. The check and the
write must both happen inside the lock.

Do NOT: change write_file, the record or the path check; check outside the lock.

Done when the stage 4 checks still pass once they read the file before they edit it. Not part of the five stages' checks.
```

Why one step matters: a check followed by a separate write leaves a gap where another writer can slip in. This lock closes that gap for writers in one process. Two processes need a file lock, and a bucket needs a conditional write, as Cloud Storage and S3 offer.

The solution is on its own branch, `session-04-filesystem-solutions-stretch`, one commit on top of the stage 5 solution. Its three checks run with `uv run pytest checks/test_files.py -m stretch`. The stage 4 checks on that branch read the file before they edit it. This stretch has not been run against a coding agent, so treat the prompt as a draft.
