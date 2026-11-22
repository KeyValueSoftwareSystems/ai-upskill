# Files stage 2 · How a file gets changed

> The reviewer, on Breeze: "Take out the lifetime-guarantee line." The trace shows the whole brief written again for one line.

The only way to change a file today is to write it again. The agent reads the brief, rewrites all of it, and sends every line back through `write_file`. Nothing checks that the line it was asked about was there, or was there once, and nothing can tell the line that was asked for from the lines that were not.

## Before you start

The page is running on the working copy where stage 1's checks went green. Harbor's brief must hold the line the reviewer objects to. As **Maya at Harbor**, in the Breeze conversation, send:

```
Create my finalized campaign brief with this content, exactly as written:

# Breeze campaign brief

## Positioning

avoid the lifetime-guarantee framing, two competitors use it

Breeze is the one you keep using, not the one you bought once.

## Tone

warm, plain, never clever

## Placements

square for social, tall for print
```

The agent chooses the file's name, for example `outputs/breeze_campaign_brief_….md`, so yours may differ. Later steps say "the campaign brief" and do not name a path.

## The slot

- `launchkit/tools/edit_file.py` · `make_edit_file`. A stub with its signature, its note and a comment saying what to do. Today it raises, and the agent is not offered it.

- `launchkit/tools/search_files.py` · `make_search_files`. Ready-made and working, with its note in `launchkit/tools/notes.py`. The agent is not offered it yet: stage 1 did not register it.

Already there, so you do not build them: the tool's note (`launchkit/tools/notes.py`), the `file_written` trace line, and the `edit_a_line` skill (`launchkit/skills/edit_a_line/skill.md`). The skill tells the agent to search for the line, read around it, then edit. It is offered to the agent only once `edit_file` is built, because it needs that tool.

## Break it first

As Maya, in the same conversation, first ask the question from the end of stage 1:

> Look in our saved briefs: which of them mention a holiday, and what do they say?

The agent can list and read, and it has no search. The Trace shows `list_files` and `read` lines for some of the briefs, or for none, and no `search`. The reply may sound as if it had read them all, and several of them mention a holiday. Fixing that needs no new code: the search is ready-made and only has to be offered to the agent.

Then ask for the change:

> The reviewer says the lifetime-guarantee line in our Breeze campaign brief is wrong. Change "avoid the lifetime-guarantee framing, two competitors use it" to "lead with the five-year warranty", and leave everything else in the file exactly as it is.

The agent uses `read_file` and then `write_file`, to write the campaign brief again rather than editing just the one line. The Trace shows a `read` of the brief and then a `wrote` line for the same file with the whole file's characters counted: every line went back through the write tool for one line's change.

## Prompt card, for your coding agent

```
Build stage 2 of Session 4: an edit tool that changes one piece of a file and refuses when it is not sure.

launchkit/tools/edit_file.py: fill in the stub make_edit_file(workspace, trace, message=""). Replace the raise with the
body and remove @todo. Join the path onto workspace.root the way the other tools do. Count how many times old_text
appears. If it appears zero times, change nothing and return a message that begins "Not found". If it appears more than
once, change nothing and return a message that begins "Ambiguous" and says how many times. If exactly once, replace it,
write the file and return "Edited <path>.". Like write_file, build a Record(workspace.root) from
launchkit/files/record.py when the tool is built, and call its add(path relative to the root, "edit_file", message)
after a successful edit. Also make the file_written trace call, with the path and the number of characters in new_text.
Its note is already in launchkit/tools/notes.py.

In build_catalogue in launchkit/agents/main_agent.py, add two tools to the file_tools list, after the ones stage 1
put there: the search that is already built, make_search_files(files, trace), and make_edit_file(files, trace, message).

Do NOT make it check whether the file changed since the agent last read it.

Done when `uv run pytest checks/test_files.py -m "stage1 or stage2"` passes.
```

The last "do not" leaves a gap on purpose. This tool checks the text it was given, not whether the file changed since it was read. It refuses when another writer has already removed its old text, and it allows a write that loses someone else's lines as long as its own old text is still there exactly once.

## Prove it

```
uv run pytest checks/test_files.py -m "stage1 or stage2"
```

- An edit replaces the text it was asked to replace and nothing else.
- It refuses when the old text is missing, and the file is untouched.
- It refuses when the old text appears more than once, and says how many.
- The search is offered to the agent, and a question about which briefs mention a word ranks it near the top of `find_tool`.
- An edit is recorded the way a write is, so the **Files** panel lists the changed file.
- The edit skill is offered once the tool exists, and a person's way of asking for a change ("take out the lifetime-guarantee line") ranks the skill or the tool near the top of `find_tool`, while a question about saved work does not.

## Run it again

In the same conversation, where the briefs from stage 1 are still saved, ask the holiday question again. The Trace shows one `search 'holiday'` line and perhaps one `read`, not a read of every brief, and the reply names the briefs and quotes the lines.

Then, still in that conversation, where the brief was created, send the reviewer's ask again. The agent often loads the `edit_a_line` skill first, then searches for a word in the line and reads the lines around it. Because the ask quotes the old text exactly, it may also go straight to `edit_file`, which is fine. Either way the Trace shows one `edit_file` call that returns `Edited` and the brief's path, and one `wrote` line whose character count is the new text's, not the whole file's.

Then ask for a change that matches more than one place:

> In the campaign brief, change "the" to "a".

Several lines contain "the". The `edit_a_line` skill tells the agent to list the matches and ask which one, and not to choose. Watch what it does. It may ask, which is the right answer. It may call `edit_file` with "the" alone, and the Trace then shows `Ambiguous: that text appears …` and nothing is changed. Or it may pick one line and edit it without asking, so a line you did not mean has changed. Ask the room which of these it expected, and what should stop the third.

The other refusal, `Not found`, is covered by the checks and is rarely seen live: asked to change text that is not in the file, the agent usually searches the file first and tells you it is not there, without calling the edit tool.

## Why it matters

There are five ways to change a file: write it all again, replace a line range, replace an exact piece of text, apply a patch, or run a shell command. Four of them can change the wrong thing without telling you. What the room builds is one function that replaces exactly the text it was given, refuses when that text is missing, and refuses when it appears more than once. Hold on to that check: it looks at content, and it cannot tell that the file changed after the agent read it. The stretch below closes that. Versioning and rollback are the other half of write safety, and every undo tool covers what it saw change and nothing else, so a file changed by something outside the tool does not come back.

What if the old text appears more than once? The tool refuses and says how many, because the agent cannot count well and a short word such as "the" is almost never meant everywhere. Other tools handle it in three ways. The agent adds surrounding text until the match is unique. An explicit replace-all flag, off unless the agent asks for it. Or an occurrence number, which breaks when the file changes between the read and the edit. Replace-all is right for renaming a term across a file, such as "lifetime guarantee" to "five-year warranty", and dangerous for a short word, and one flag does both jobs. So the room has three questions: who decides that every match is meant, should a replace-all ask Maya first, and should the refusal list each match with a line of context so the agent can pick one?

## Optional stretch: close the gap

Only if your team finishes early. Stage 2 left a gap on purpose: the edit tool checks the text it was given, and it does not check whether the file changed since the agent read it. A production system closes that gap. This stretch does it for one machine.

```
Stretch after stage 2 of Session 4: make edit_file refuse when the file moved on.

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

Done when the stage 1 and stage 2 checks still pass once they read the file before they edit it. Not part of the three stages' checks.
```

Why one step matters: a check followed by a separate write leaves a gap where another writer can slip in. This lock closes that gap for writers in one process. Two processes need a file lock, and a bucket needs a conditional write, as Cloud Storage and S3 offer.

The solution is on its own branch, `session-04-filesystem-solutions-stretch`, one commit on top of the stage 3 solution. Its three checks run with `uv run pytest checks/test_files.py -m stretch`. The stage 2 checks on that branch read the file before they edit it. This stretch has not been run against a coding agent, so treat the prompt as a draft.
