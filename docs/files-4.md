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

- `launchkit/tools/edit_file.py` · `make_edit_file`. Today it raises and is not registered.

## Break it first

As Maya, in the same conversation:

> The reviewer says the lifetime-guarantee line is wrong. In outputs/campaign-brief.md, change "avoid the lifetime-guarantee framing, two competitors use it" to "lead with the five-year warranty", and leave everything else in the file exactly as it is.

In prep the agent used `read_file` and then `write_file`, 3 runs of 3. The Trace shows `read outputs/campaign-brief.md` and then `wrote outputs/campaign-brief.md` with the whole file's characters counted: every line went back through the write tool for one line's change. With this model the other lines came back unchanged in all three runs, so what the room sees is the full-file rewrite in the Trace, not drift in the text. Then ask for a line that is not there:

> In outputs/campaign-brief.md, change "two years" to "five years".

Nothing stops a write when the text is missing. Whatever the model decides to do, no tool refused.

## Prompt card, for your coding agent

```
Build stage 4 of Session 4: an edit tool that changes one piece of a file and refuses when it is not sure.

launchkit/tools/edit_file.py: make_edit_file(workspace, trace, message="") returning an Entry with kind "read" and
edit_file(path, old_text, new_text). Resolve the path with resolve_in_workspace the way the other tools do. Count
how many times old_text appears. If it appears zero times, change nothing and return a message that begins
"Not found". If it appears more than once, change nothing and return a message that begins "Ambiguous" and says how
many times. If exactly once, replace it and write the file. Register it in build_catalogue, and word its Entry note this way: "pick me to edit, change, update or fix one line
or phrase in a saved file, brief or document without rewriting the rest: give the exact old text and the new text".

Do NOT: add an append mode, a line-range replace or a regular-expression mode; record anything (stage 5); make it
check whether the file changed since the agent last read it.

Done when `uv run pytest checks/test_files.py -m "stage1 or stage2 or stage3 or stage4"` passes.
```

The last "do not" is the beat the ticket turns on. This tool checks content. It catches a collision that overwrote your lines and permits one that did not.

## Prove it

```
uv run pytest checks/test_files.py -m "stage1 or stage2 or stage3 or stage4"
```

- An edit replaces the text it was asked to replace and nothing else.
- It refuses when the old text is missing, and the file is untouched.
- It refuses when the old text appears more than once, and says how many.

## Run it again

Send the reviewer's ask again. The Trace shows one `edit_file` call that returns `Edited outputs/campaign-brief.md`, and no `wrote` line for the whole file. Then the two refusals:

> In outputs/campaign-brief.md, change "two years" to "five years".

The reply begins "Not found", and the file is untouched.

> In outputs/campaign-brief.md, change "the" to "a".

The reply begins "Ambiguous" and says how many times that text appears.

## Why it matters

There are five ways to change a file: write it all again, replace a line range, replace an exact piece of text, apply a patch, or run a shell command. Four of them can change the wrong thing without telling you. What the room builds is one function that replaces exactly the text it was given, refuses when that text is missing, and refuses when it appears more than once. Hold on to that check, because the ticket defeats it without a single failed match. Versioning and rollback are the other half of write safety, and every undo tool covers what it saw change and nothing else, so a file changed by something outside the tool does not come back.
