# What is already built

This branch starts with less than it looks like. The agent has no file tools at all, because LaunchKit never had any: every artifact was written by a tool that already knew its own output path. The room builds them in stages, and each stage's file below is a stub that says which stage fills it and what it must do.

Everything else, the chat page, the Files panel, the seeded state, the checks and the research team, is already there. This table says what each piece is, which stage it serves, and where the idea is explained in the reference. Nothing in it is inherited from Session 3; the prep script wrote the file layer for this branch.

| File | What it is | Stage | Reference page |
| --- | --- | --- | --- |
| `launchkit/files/workspace.py` | A stub. `Workspace` and `for_request` raise until stage 1 builds the folder one conversation owns, and its drawers. | 1 | 3 Where the work lives |
| `launchkit/tools/read_file.py`, `list_files.py`, `write_file.py` | Stubs, not registered with the agent. Stage 1 builds all three and registers them in `build_catalogue`. | 1 | 6 File tools |
| `launchkit/tools/search_files.py` | A stub. Stage 2 builds the search, capped from the start. | 2 | 4 Finding a file, 5 What an index costs |
| `launchkit/files/paths.py` | A stub. `resolve_in_workspace` is the one door every path passes, built in stage 3. `OutsideWorkspace` and `refuse` are already here, so a refusal lands on the trace in the same words everywhere. | 3 | 9 Who may touch which file |
| `launchkit/tools/edit_file.py` | A stub. Stage 4 builds the exact-text edit. | 4 | 7 Changing a file, 8 What an edit tool can and cannot check |
| `launchkit/files/record.py` | A stub. Stage 5 builds the artifact record, written as each file is written, and the chat page reads it. | 5 | 11 Recording what the agent produced |
| `launchkit/tools/generate_image.py`, `resize_poster.py`, `text_to_speech.py`, `launchkit/memory/attached_pictures.py` | The tools that already write files, each into a folder every brand shares and each knowing its own path. Stage 1 points them at the conversation's workspace; stage 5 makes each record what it wrote. | 1, 5 | 3 Where the work lives, 11 Recording what the agent produced |
| `launchkit/orchestration/research_team.py` | Session 2's research team. `research_many` fans five subagents out in parallel. The ticket happens here. | ticket | 12 Two writers, one file |
| `launchkit/web/app.py`, `launchkit/web/index.html` | The chat page and the **Files** panel. `new_files` finds artifacts by scanning `data/` by modification time, which is stage 5's four defects. | 5 | 11 |
| `launchkit/trace.py` | The trace, as Session 3 left it. File events (`file_read`, `file_written`, `file_refused`, `search`) are added to it as the tools are built. | 3, 5 | 11 |
| `launchkit/settings.py` | `data_dir` reads `LAUNCHKIT_DATA_DIR`, so two workers can run with two data directories for the closing demo. | closing block | 13 Running on many machines |
| `workspaces/harbor/`, `workspaces/ember/` | The brands. Harbor's `brand-book.md` and `rules.yaml` are the shared files stage 6 reasons about. | 3, 6 | 9 |
| `checks/test_files.py` | The twelve acceptance criteria as code, grouped by stage. `-m stage1` runs one stage. Every group is red here and green on the solutions branch. | all | |
| `launchkit/files/seed.py` | The starting state the room inherits, and the code that builds it. `uv run launchkit setup` runs it. | all | |
| `launchkit/cli.py` | `setup` puts the seeded state in place. `ui --reload` runs the chat page. | | |

## The Files panel

<a id="files-panel"></a>

Press **Files** on the chat page. It shows what this conversation produced and what the agent reached this turn. Every acceptance criterion is read from this panel or from the Trace tab, never from a terminal.

Today it is wrong in four ways at once, which is stage 5: it lists anything under `data/` modified since the run started, filtered to picture and sound types, with no filter for the brand and no record of who wrote what. After the build it reads the artifact record instead.

## The seeded state

`uv run launchkit setup` puts `data/` back the way Breeze week left it:

- Posters from Harbor and Ember in one `outputs/` folder, named by the millisecond.
- Their resized versions in `sizes/`, a voice-over in `audio/`, uploads keyed by the attached file's name.
- Chat history for Maya, Sam and Jonas, including Monday's Breeze conversation and the reviewer's notes.
- Five Breeze competitor briefs, with the lifetime-guarantee claim in two of them.
- `data/files/ember/t3a9-old/`, a conversation whose name starts the same way as Jonas's `t3a9`, which is the prefix case in stage 3.

It is never generated in the room. If you want it back, run setup again.

## Real models

Every flow runs on the real model through the proxy. The path attack is seeded in the data rather than scripted, so it fails the same way every time without a fake model. Fake models exist only inside this branch's own tests.
