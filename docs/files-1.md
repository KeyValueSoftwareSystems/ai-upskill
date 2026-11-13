# Files stage 1 · Where the work lives, and the file tools

> Maya, Harbor: "Give me Monday's approved Breeze brief." The agent says it cannot find one and asks her for the details.

Four months after the memory work, LaunchKit serves forty brands. File handling was written when it served one. Every poster, every resized version and every voice-over goes into one folder under `data/`, named by the millisecond it was made. Uploads go into another shared folder, keyed by the name of the attached file. There are no general file tools at all. Every artifact is written by a tool that already knows its own output path, and the agent cannot go back and look at anything it made.

## Before you start

The room starts on `session-04-filesystem-prd`. Put `data/` back the way Breeze week left it, then start the page:

```
uv run launchkit setup
uv run launchkit ui
```

`setup` replaces only the folders the seed owns: the shared folders, and three conversations with fixed ids. Maya's Breeze conversation is `k7c1`, Sam's is `s5b2`, and Jonas's at Ember is `t3a9`. The ids are fixed so that stage 3's attack can name Harbor's workspace with a path everyone can type.

## The slot

- `launchkit/files/workspace.py` · `Workspace`, `for_request`. Today both raise.
- `launchkit/tools/read_file.py`, `list_files.py`, `write_file.py`. Today each raises, and none is registered with the agent.
- `launchkit/tools/generate_image.py`, `resize_poster.py`, `text_to_speech.py`, `launchkit/memory/attached_pictures.py`. Today each writes into a folder every brand shares.

## Break it first

On the chat page, sign in as **Maya at Harbor** and open her Breeze conversation from launch week (its first message is "Concepts for the Breeze launch, please"). Leave **Model** empty and send:

> Give me Monday's approved Breeze brief.

The agent has nothing to look with. In prep it said it could not find the brief and asked for the details, 3 runs of 3; the Trace shows `find_tool` and a look at the board or at the brand facts, never a file. Last week's brief is on disk, in `data/campaign-brief.md`, and nothing on disk says it is Harbor's or Maya's.

Then ask for something that writes a file:

> A poster for Breeze: the bottle on a misty lakeshore at dawn.

The **Files** panel shows the poster, and the Trace's `generate_image` line shows where it went: `data/outputs/`, next to Ember's autumn posters, named by the millisecond.

## Prompt card, for your coding agent

```
LaunchKit's agent has no file tools. Build stage 1 of Session 4: let the agent write, list and read back what it
made, in a folder that belongs to one brand and one conversation, and put the files it already makes in the same
place. Read TICKETS.md (Stage 1) and the stubs in launchkit/files/ and launchkit/tools/.

1. launchkit/files/workspace.py: fill in Workspace.drawer and for_request. The root is
   settings.data_dir / "files" / brand / conversation, and the brand's own files are settings.workspaces_dir / brand.
   The brand comes from resolve_workspace_id and the conversation from request.session_id, which must match
   ^[A-Za-z0-9_-]{1,32}$. Neither may come from anything a tool is given.

2. Three tools, each a factory returning an Entry from launchkit/tools/catalogue.py with kind "read":
   - launchkit/tools/read_file.py   make_read_file(workspace, trace)             read_file(path)
   - launchkit/tools/list_files.py  make_list_files(workspace, trace)            list_files(folder=".")
   - launchkit/tools/write_file.py  make_write_file(workspace, trace, message="") write_file(path, text)
   Each joins its path onto workspace.root. Add trace lines for file_read, file_written and file_listed in
   Trace.line in launchkit/trace.py.

3. Register them in build_catalogue in launchkit/agents/main_agent.py: add `files=None` and `message=""` parameters,
   build the three tools when files is given, and add them to the entries. In run_main pass
   files=for_request(req, settings) and message=trace.message. Pass make_research_entries
   write=lambda: make_write_file(files, trace, message).fn, a factory, so that every research subagent builds its
   own write tool when it starts and saves its own brief with it.

4. Tell the agent it has these tools, because on the real model it does not find them otherwise and reaches for the
   board's cards instead. In MAIN_TASK in launchkit/agents/main_agent.py, add this paragraph before the line that
   begins "Never say something is made":
     This conversation has a workspace of files, and everything you have made for the marketer is kept there. Save
     finished work with write_file in outputs/ and drafts in work/. Before you answer from memory or ask the
     marketer to send something again, look in the workspace with list_files, search_files and read_file. A brief,
     plan, draft or document is a file there, not a card on the board.
   And word the tools' Entry notes the way a person asks for things:
     write_file  "pick me to save, write or create a file, brief, document, draft or plan in this conversation's
                  workspace: finished work in outputs/, drafts in work/"
     read_file   "pick me to open, read or show a saved file, brief, document or draft from this conversation's
                  workspace, or a range of its lines; the brand's own files are brand/<name>"
     list_files  "pick me to list, see or find what files, briefs, drafts and documents this conversation has
                  already saved"

5. Point the tools that already write files at the same workspace. make_images(settings, out_dir=None) in
   launchkit/adapters/image_providers.py takes the folder to save into. PictureDesk in
   launchkit/tools/resize_poster.py and make_text_to_speech / text_to_speech_entry in launchkit/tools/text_to_speech.py
   take files=None and save into files.drawer("outputs") when it is given. Pictures in
   launchkit/memory/attached_pictures.py keeps its signature, builds its workspace with for_request, keeps an attached
   photo in uploads/ and its list in pictures.json at the workspace root, and gets attach_bytes(name, data) for a
   picture that arrives over the page; the /attach route in launchkit/web/app.py uses it instead of a temp file in
   data/uploads. build_catalogue passes files to all of them, and make_picture takes files too, for the rework path.
   With no workspace each keeps its old folder, so Session 1's poster flow still runs. In checks/test_tools0.py the
   attach test's address now ends /<conversation>/uploads/<name>.

Do NOT: resolve, normalise or validate paths (stage 3 does that); record anything about what was written (stage 5);
add a search or an edit tool; change what the chat page lists or serves.

Done when `uv run pytest checks/test_files.py -m stage1` passes and the rest of `uv run pytest checks -q
--ignore=checks/test_files.py` still passes.
```

It stops where it does because a model asked for file tools will often add a path check unasked. The last paragraph keeps stage 3's failure real.

## Prove it

```
uv run pytest checks/test_files.py -m stage1
uv run pytest checks -q --ignore=checks/test_files.py
```

- Two conversations at one brand, and two brands, never share a folder, and the workspace sits under `data/`.
- The workspace comes from the request, never from anything the model supplies.
- Finished work and drafts are kept apart, and every drawer is made on first use.
- A brief written in a conversation is found again in that conversation, and a second conversation at the same brand starts with none of it.
- A poster, a size and a voice-over land in the conversation's `outputs/`, and an attached photo in its `uploads/`.
- Everything the earlier sessions built still passes.
- A research subagent saves its brief as `competitors/<name>.md` in this conversation's workspace.

## Run it again

As Maya, in the same conversation, send the research ask and then ask for the brief:

> Find out how Hydro Flask, Klean Kanteen, Owala, Stanley and Yeti are launching their bottles this season, so we know what to avoid copying for Breeze.

> Write our Breeze campaign brief from that research and save it as campaign-brief.md. Give it a positioning line, a tone and the placements.

The Trace shows five `wrote competitors/<name>.md` lines from the researchers, then `wrote outputs/campaign-brief.md`. Now ask for it back:

> Give me the Breeze brief you just made.

The Trace shows `read outputs/campaign-brief.md`, and the reply is that file, not a new one. Ask for a poster, and the Trace's `generate_image` line now ends in `data/files/harbor/k7c1/outputs/`; a second conversation at Harbor starts with none of it. The brief itself does not appear in the **Files** panel yet. That is stage 5's failure, and it stays until the room gets there.

## Why it matters

The decision this stage settles is who names the workspace. The brand and the conversation come from the request, which the server trusts, never from an argument the model fills in. Everything later rests on that: stage 3's fence compares against a root the model never chose, and stage 5's record is keyed by it. One feature already had this shape, since `Pictures` kept one folder per conversation, and nobody had generalised it. The media tools move for the same reason the brief does, because a poster is an artifact like any other, and Breeze is under embargo.
