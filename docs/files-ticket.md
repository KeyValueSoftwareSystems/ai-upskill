# Files ticket · Five writers, four entries lost

> Maya, Harbor: "I asked it to research five competitors. The chat shows one brief. Did it do the other four?"

It did. All five briefs are on disk. Four of them are missing from the record, so the chat cannot show them. `research_many` runs five subagents in a thread pool. Each builds its own write tool when it starts, which loads the record, then writes its own `competitors/<name>.md`, which never collides, and then writes the record back from what it loaded, with its one line added. All five loaded the same record, all five wrote it back, and the last one wins. Stage 4's edit tool would not have helped, and working out why is the point. Every one of the five edits matched exactly once, because each was appending a different line. Exact-text matching catches a collision that overwrote your lines and silently permits one that did not. All twelve criteria are met and the bug is real.

## Before you start

The page is running on the working copy where stage 5's checks went green.

## The slot

- `launchkit/files/record.py` · `Record`, `record`, `entries`.

## Break it first

As **Maya at Harbor**, in the Breeze conversation:

> Find out how Hydro Flask, Klean Kanteen, Owala, Stanley and Yeti are launching their bottles this season, so we know what to avoid copying for Breeze.

The Trace shows five `wrote competitors/<name>.md` lines. The **Files** panel shows one brief. In prep there were five on disk and one in the record, 3 runs of 3, at about thirty seconds a run.

## The three answers

One file per entry with the directory as the index, an append-only log, or a write that refuses when the file moved on. Two are layout changes and one is a lock. The room weighs them first. The prompt below is the log; if the room picks another, adapt it.

## Prompt card, for your coding agent

```
Fix the lost update in launchkit/files/record.py. Five research subagents call record() at the same time, each reads
the whole list and writes it back, and the last one wins.

Make the record an append-only log in root / "artifacts.jsonl": one JSON object per line. Record.add opens the
file for append and writes one line, and must never read the file or use anything Record loaded. Record no longer
needs to load anything. entries() reads the lines, skips a line
that does not parse (a crash can cut the last one short), and counts an entry once however many times it was
appended, identifying it by (message, by, path), because a tool call that times out and runs again appends the same
line twice.

Do NOT: add a lock, a queue or a temp-file-and-rename; change anything outside record.py.

Done when `uv run pytest checks/test_files.py` passes, all of it.
```

## Prove it

```
uv run pytest checks/test_files.py
```

- Five subagents write at once and no entry is lost.
- Five write tools built together, each finishing in turn, keep every entry: the ticket as it happens live, with no threads and nothing to time.
- A tool call that times out and runs again does not put the same entry in twice.

## Run it again

The same research ask. Five briefs in the **Files** panel. Run it again, and there are still five. Three more criteria then go in `DECISIONS.md`, as the regression test that stops this coming back.

## What it costs

The atomicity of an append holds on a pod's local disk. On a bucket mount a write is a whole new object and there is no real append, so the same code loses entries again the day the files move to a bucket. The log also costs you compaction, and a reader that tolerates a half-written last line. The directory as the index costs you a listing on every read, and a filename convention that has to carry what the line used to say. Both ship in production.
