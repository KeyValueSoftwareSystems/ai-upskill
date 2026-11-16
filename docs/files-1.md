# Files stage 1 · Where the work lives, and the file tools

> Maya, Harbor: "You researched five competitors for me an hour ago. I asked what you found about Stanley, and you either said you did not know or started the research again."

Four months after the memory work, LaunchKit serves forty brands. File handling was written when it served one. Every poster, every resized version and every voice-over goes into one folder under `data/`, named by the millisecond it was made. Uploads go into another shared folder, keyed by the name of the attached file. There are no general file tools at all. Every artifact is written by a tool that already knows its own output path, and the agent cannot go back and look at anything it made.

## Before you start

The room starts on `session-04-filesystem-prd`. Put `data/` back the way Breeze week left it, then start the page:

```
uv run launchkit setup
uv run launchkit ui
```

`setup` replaces only the folders the seed owns: the shared folders, and three conversations with fixed ids. Maya's Breeze conversation is `k7c1`, Sam's is `s5b2`, and Jonas's at Ember is `t3a9`. The ids are fixed so that stage 5's attack can name Harbor's workspace with a path everyone can type. Work in Maya's Breeze conversation, `k7c1`, for the whole session: each stage builds on what the stage before left in its folder.

## The slot

- `launchkit/files/workspace.py` · `Workspace`, `for_request`. Today both raise.
- `launchkit/tools/read_file.py`, `list_files.py`, `write_file.py`. Today each raises, and none is registered with the agent.
- `launchkit/tools/generate_image.py`, `resize_poster.py`, `text_to_speech.py`, `launchkit/memory/attached_pictures.py`. Today each writes into a folder every brand shares.

## Break it first

On the chat page, sign in as **Maya at Harbor** and open her Breeze conversation (its first message is "Concepts for the Breeze launch, please"). Leave **Model** empty. First send the research ask:

> Find out how Hydro Flask, Klean Kanteen, Owala, Stanley and Yeti are launching their bottles this season, so we know what to avoid copying for Breeze.

The agent researches and answers in the chat. Then send three short questions, one at a time, so the research falls out of what the agent can still see. It keeps only its last few turns:

> Give me three headline ideas for Breeze.

> Which sizes does Harbor make posters in?

> What is Harbor's warranty?

Now ask about the research:

> Look in our saved briefs: what did the research say about Stanley's launch angle?

The agent has nothing to look with. It says it does not know, researches Stanley again (the Trace shows `competitor_research` and `search_web`), or answers from Harbor's own brand guide, which has nothing about Stanley (the Trace shows `get_brand_details`). It never reads a file. Nothing was written down, so there is nothing to find.

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
   Each joins its path onto workspace.root. read_file and list_files return a short message, such as "No file at
   <path>.", when the path does not exist, and do not raise. write_file builds a Record(workspace.root) from launchkit/files/record.py
   when the tool is built, and calls its add(path relative to the root, "write_file", message) after every write. Add
   trace lines for file_read, file_written and file_listed in Trace.line in launchkit/trace.py, each showing the path
   and the number of characters.

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
     marketer to send something again, look in the workspace with list_files and read_file. A brief,
     plan, draft or document is a file there, not a card on the board.
   And word the tools' Entry notes the way a person asks for things:
     write_file  "pick me to save, write or create a file, brief, document, draft or plan in this conversation's
                  workspace: finished work in outputs/, drafts in work/"
     read_file   "pick me to open, read or show a saved file, brief, document or draft from this conversation's
                  workspace, or a range of its lines; the brand's own files are brand/<name>"
     list_files  "pick me to list, see or find what files, briefs, drafts and documents this conversation has
                  already saved"

5. The picture, size and voice-over tools already save into the conversation's outputs/ drawer, and record what they
   write, when they are given files and message (generate_image, PictureDesk and text_to_speech in launchkit/tools,
   and make_images(settings, out_dir)). Pass files and message to them in build_catalogue and make_picture. Pictures
   in launchkit/memory/attached_pictures.py keeps its signature, builds its workspace with for_request, keeps an
   attached photo in uploads/ and its list in pictures.json at the workspace root, and gets attach_bytes(name, data)
   for a picture that arrives over the page; the /attach route in launchkit/web/app.py uses it instead of a temp file
   in data/uploads, and returns the photo's /workspace/<brand>/<conversation>/uploads/<name> address, because the old
   /files address stops working once for_request is built. In checks/test_tools0.py the attach test's address now
   ends /<conversation>/uploads/<name>.

6. Remove the @todo mark from for_request in launchkit/files/workspace.py. From then on the chat page lists a turn's
   files from the record and serves them through /workspace/<brand>/<conversation>/<path>, and the old /files and
   /outputs routes stop.

Do NOT: change any line that is already in Trace.line, or its spacing; resolve, normalise or validate paths (stage 5 does that); make the record safe for several writers;
add a search or an edit tool; change what the chat page lists or serves.

Done when `uv run pytest checks/test_files.py -m stage1` passes and the rest of `uv run pytest checks -q
--ignore=checks/test_files.py` still passes.
```

It stops where it does because a model asked for file tools will often add a path check unasked. The last paragraph keeps stage 5's failure real.

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
- The chat page lists a turn's files from the record: finished work only, never drafts, nothing another brand made, and each file served through its own conversation's route.
- Everything the earlier sessions built still passes.
- A research subagent saves its brief as `competitors/<name>.md` in this conversation's workspace.

## Run it again

In the same conversation, send the research ask again, then the three short questions, then the question about the research:

> Look in our saved briefs: what did the research say about Stanley's launch angle?

This time the researchers saved their briefs: the Trace shows five `wrote competitors/<name>.md` lines during the research. Look at the **Files** panel after that first step: it lists fewer briefs than the Trace says were written. Leave it. That is stage 2.

For the question, the Trace shows `list_files`, then a `read` of a brief that is about Stanley, and the reply comes from that file. The agent may make one wrong guess at a tool or an argument name first, and recovers. Now ask for a poster. The Trace's `generate_image` line ends in `data/files/harbor/k7c1/outputs/`, the **Files** panel lists it under this conversation, and a second conversation at Harbor starts with none of it.

## Why it matters

The decision this stage settles is who names the workspace. The brand and the conversation come from the request, which the server trusts, never from an argument the model fills in. Everything later rests on that: stage 3's fence compares against a root the model never chose, and stage 5's record is keyed by it. One feature already had this shape, since `Pictures` kept one folder per conversation, and nobody had generalised it. The media tools move for the same reason the brief does, because a poster is an artifact like any other, and Breeze is under embargo. The record behind the **Files** panel was already built. It had nothing to read until a conversation had a workspace, which is why this stage switches it on.
