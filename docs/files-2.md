# Files stage 2 · Five writers at once

> Maya, Harbor: "I asked it to research five competitors. The chat shows one brief. Did it do the other four?"

It did. All five briefs are on disk. Four of them are missing from the record, so the chat cannot show them. `research_many` runs five subagents in a thread pool. Each builds its own write tool when it starts, which loads the record, then writes its own `competitors/<name>.md`, which never collides, and then writes the record back from what it loaded, with its one line added. All five loaded the same record, all five wrote it back, and the last one wins. Nobody wrote a criterion for this. Every one of the twelve is met, and the bug is real.

## Before you start

The page is running on the working copy where stage 1's checks went green. Maya's Breeze conversation is the one from stage 1.

## The slot

- `launchkit/files/record.py` · `Record`, `record`, `entries`. It is ready-made, and it is where the bug is.

## Break it first

As **Maya at Harbor**, in the Breeze conversation:

> Find out how Hydro Flask, Klean Kanteen, Owala, Stanley and Yeti are launching their bottles this season, so we know what to avoid copying for Breeze.

The Trace shows five `wrote competitors/<name>.md` lines. The **Files** panel shows one brief. Five are on disk and one is in the record. A run takes about thirty seconds.

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

Done when `uv run pytest checks/test_files.py -m "stage1 or stage2"` passes.
```

## Prove it

```
uv run pytest checks/test_files.py -m "stage1 or stage2"
```

- Five subagents write at once and no entry is lost.
- Five write tools built together, each finishing in turn, keep every entry: the same bug as it happens live, with no threads and nothing to time.
- A tool call that times out and runs again does not put the same entry in twice.

## Run it again

The same research ask. Five briefs in the **Files** panel. Run it again, and there are still five. Two more criteria then go in `DECISIONS.md`, so this bug cannot come back unnoticed.

## Why it matters

Appending is safe on a server's own disk. On a bucket mount a write is a whole new object and there is no real append, so the same code loses entries again the day the files move to a bucket. The log also costs you a clean-up now and then, to squeeze out old and repeated lines, and a reader that copes with a half-written last line. The directory as the index costs you a listing on every read, and a filename convention that has to carry what the line used to say. Both ship in production.

The edit tool in stage 4 does not help here, and working out why is part of that stage. Its check asks whether the old text is still there exactly once. Each of five writers adds a different line, so every one finds what it expects. The edit check looks at content. This bug is about the order of the writes.
