# Files stage 5 · What gets recorded when the agent produces something

> Maya, Harbor: "I asked for five competitor briefs. The chat shows one Ember poster and nothing else."

`new_files` in `launchkit/web/app.py` finds a turn's artifacts by scanning all of `data/` for pictures and sounds modified since the run started. Two lines, four defects: no workspace filter, so a poster Ember generated during Maya's turn appears in Maya's chat; no `.md` in the list, so a brief can never appear; selection by modification time rather than by who wrote the file; and a list assembled after the run, so a turn that crashes halfway loses every artifact it made on the way. Harbor asked for this one by name: "I can see what it made for me, next to the message where I asked."

## Before you start

The page is running on the working copy where stage 4's checks went green. Open two browser tabs: Maya's Breeze conversation in one, and Jonas's autumn conversation at Ember in the other.

## The slot

- `launchkit/files/record.py` · `Entry` is ready-made; `record` and `entries` raise.
- `launchkit/web/app.py` · `new_files`, and the two routes that hand out any media under `data/`.
- `launchkit/web/index.html` · `mediaHtml`, which only knows how to show a picture or a sound.
- `checks/test_tools0.py` · the old test that pins the scan.

## Break it first

As **Maya at Harbor**, send the research ask:

> Find out how Hydro Flask, Klean Kanteen, Owala, Stanley and Yeti are launching their bottles this season, so we know what to avoid copying for Breeze.

While it runs, in the other tab as **Jonas at Ember**:

> Autumn poster for the Night Shift roast, dark and warm.

When Maya's turn ends, her **Files** panel shows Jonas's poster and none of the five briefs the Trace says were written. In prep, with the scan, the page listed exactly one file for Maya's turn, Ember's poster, 3 runs of 3.

## Prompt card, for your coding agent

```
Build stage 5 of Session 4: record what the agent produces as it produces it, and have the chat page list that
instead of scanning the disk.

1. launchkit/files/record.py: entries(root), a class Record, and record(root, path, by, message). The record is
   root / "artifacts.json", a plain JSON list of the Entry fields; entries() returns [] if it is missing or
   unreadable. Record(root) loads that list once when it is built and keeps it in self.items. Record.add(path, by,
   message) appends an Entry to self.items and writes the whole list back. record() is Record(root).add(...).
   Entry.path is relative to the workspace. Keep it that simple: no locking, no temp file, no append mode, and
   add() never re-reads the file.

2. Every tool that writes a file records it, under its own name, the moment it has written. write_file builds a
   Record(workspace.root) when the tool is built and calls add(path relative to the root, "write_file", message)
   after every write. generate_image in launchkit/tools/generate_image.py, PictureDesk.save in
   launchkit/tools/resize_poster.py (under the tool's name: crop, expand_canvas, scale or centre_crop) and
   text_to_speech in launchkit/tools/text_to_speech.py take message="" and call record(files.root, the path relative
   to it, their name, message) when they have a workspace. build_catalogue and make_picture pass message through.

3. In launchkit/web/app.py replace new_files with listed_files(current, req, message, kept=()). It returns page
   addresses, /workspace/<brand>/<conversation>/<path>, for the record's entries for this message whose path is not
   under work/ (drafts exist and are not shown), and for a kept poster when it lies inside the workspace. Remove
   duplicates. Use it in _worker, and add _made_before_failing(current, req, message), which calls listed_files and
   returns [] on any error, so a turn that dies partway still shows what it made. The worker sets trace.message
   before run_main. Remove the /files/{name} and /outputs/{name} routes and the MEDIA set: every address now goes
   through the download route. /attach returns the attached photo's /workspace address.

4. launchkit/web/index.html: mediaHtml renders non-picture files as an "open" link instead of a broken image, and the
   error turn shows its files.

5. The old test in checks/test_tools0.py asserts the scan and the /files door. Change it to assert the new
   behaviour: a stray picture in a shared folder is neither listed for a conversation that did not make it nor
   served by any route.

Do NOT: make the record safe for several writers at once; re-read the file inside add(); touch the research team.

Done when `uv run pytest checks/test_files.py -m "stage1 or stage2 or stage3 or stage4 or stage5 or stage6"` and
`uv run pytest checks/test_tools0.py` pass, and the checks marked `ticket` still fail. That is the point of the
next beat.
```

## Prove it

```
uv run pytest checks/test_files.py -m "stage1 or stage2 or stage3 or stage4 or stage5 or stage6"
uv run pytest checks/test_tools0.py
uv run pytest checks/test_files.py -m ticket
```

The first two are green. The third is red, and stays red until the ticket.

- Every artifact is recorded against the session and the message, by the code that wrote it, and nothing is collected afterwards.
- A poster, a size and a voice-over go in the record the moment they are written, under the tool that wrote each.
- The record survives a turn that fails partway, and so does the page's view of it.
- A research brief is a `.md` file and appears; drafts in `work/` exist and are not shown.
- No file made for one brand is listed for another, even when both were written during the same turn.
- What a turn made is listed and served through the conversation's own route, and the old door that served any media under `data/` is closed.

## Run it again

The same two asks in the same two tabs. Maya's **Files** panel shows her five briefs as "open" links and none of Jonas's work; Jonas's panel shows his poster only. Every address begins `/workspace/harbor/k7c1/` or `/workspace/ember/t3a9/`. Ask Maya's agent for a poster: it appears next to that message, served from her workspace. A turn that fails partway keeps its files in the panel too; that case is covered by the checks rather than shown live.

## Why it matters

An agent that writes files you cannot enumerate afterwards is an agent nobody can debug, bill or answer questions about. The record is written by whoever produces an artifact, at the moment it is written, carrying the message, the tool and the writer, and the page reads it instead of scanning the disk. It is written as it goes rather than at the end, because a record assembled after a successful run is exactly the record you do not have when you most want it. A poster goes in the same record as a brief, by the same rule, so the page has one source and the fence from stage 3 covers everything it shows.
