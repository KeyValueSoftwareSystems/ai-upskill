# What is already built

This branch starts with less than it looks like. The agent has no file tools at all, because LaunchKit never had any: every artifact was written by a tool that already knew its own output path. The room builds them in three stages. Each tool file below is a stub that says which stage fills it and what it must do. The record, the search code, the tools' notes and the paragraph that tells the agent about its files are not stubs: they are built, and nothing in them is for the room to write.

Everything else, the chat page, the Files panel, the seeded state, the checks and the research team, is already there. This table says what each piece is, which stage it serves, and where the idea is explained in the reference. Nothing in it is inherited from Session 3; the prep script wrote the file layer for this branch.

| File | What it is | Stage | Reference page |
| --- | --- | --- | --- |
| `launchkit/files/workspace.py` | A stub. `Workspace.drawer` and `for_request` raise until stage 1 builds the folder one conversation owns, and its drawers. | 1 | 3 Where the work lives |
| `launchkit/tools/read_file.py`, `list_files.py`, `write_file.py` | Stubs, each with its signature, its note and a comment that says what to do. The agent is not offered them until stage 1 fills them in and registers them in `build_catalogue`. `read_file` takes a line range. | 1 | 6 File tools |
| `launchkit/tools/edit_file.py` | A stub. Stage 2 builds the exact-text edit. | 2 | 7 Changing a file, 8 What an edit tool can and cannot check |
| `launchkit/files/paths.py` | A stub. `resolve_in_workspace` is the one door every path passes, built in stage 3. `OutsideWorkspace` and `refuse` are already here, so a refusal lands on the trace in the same words everywhere. | 3 | 9 Who may touch which file |
| `launchkit/files/record.py` | Ready-made. The artifact record is an append-only log, `artifacts.jsonl`, one line per entry. Each tool that writes a file adds an entry as it writes, five writers at once keep all five entries, a write that is retried counts once, and the chat page reads it. It switches on when stage 1 builds `for_request`. | ready | 11 Recording what the agent produced, 12 Two writers, one file |
| `launchkit/tools/search_files.py` | Ready-made. A capped search: a path, a line number and a snippet per match, ten matches at most, text files only, and a line that says when it stopped early. It is plain Python, not ripgrep. It has no path check yet: stage 3 adds it, like the other tools. It is not offered to the agent until stage 2 registers it in `build_catalogue`, together with the edit tool. | ready, 2 | 4 Finding a file, 5 What an index costs |
| `launchkit/tools/notes.py` | Ready-made. What each file tool says about itself to `find_tool`. They are worded the way a person asks ("saved briefs", "change one line"), and `checks/test_files.py` checks the ranking without any model. Do not rewrite them. | ready | 6 File tools |
| `launchkit/agents/main_agent.py` | `file_paragraph` and `main_task` are ready-made: the agent is told about its workspace, naming only the file tools that are built, so before stage 1 nothing is said. The prompt budget for the task section is 700 tokens so the paragraph is not cut. | ready | 6 |
| `launchkit/skills/edit_a_line/skill.md` | Ready-made. The steps for changing one line in a file: search, read around it, edit. A skill can say which tools it needs, and it is offered only when they are built, so it appears when stage 2 is done. | ready | 7 |
| `launchkit/tools/generate_image.py`, `resize_poster.py`, `text_to_speech.py`, `launchkit/memory/attached_pictures.py` | The tools that already write files, each into a folder every brand shares and each knowing its own path. They are ready to save into a conversation's workspace and record what they write; stage 1 gives them the workspace. | 1 | 3 Where the work lives, 11 Recording what the agent produced |
| `launchkit/orchestration/research_team.py` | Session 2's research team. `research_many` fans five subagents out in parallel; each saves its own brief once stage 1 passes it a write tool. | 1 | 12 Two writers, one file |
| `launchkit/web/app.py`, `launchkit/web/index.html` | The chat page and the **Files** panel. Until stage 1 is built, `new_files` finds artifacts by scanning `data/` by modification time. Once it is, the page reads the record and serves files through each conversation's own route; stage 3 puts the fence in that route. | 1, 3 | 11 |
| `launchkit/trace.py` | The trace. The lines for `file_read`, `file_written`, `search` and `file_listed` are ready-made. The `file_refused` line is added in stage 3. | ready, 3 | 11 |
| `launchkit/settings.py` | `data_dir` reads `LAUNCHKIT_DATA_DIR`, so two workers can run with two data directories for the closing demo. | closing block | 13 Running on many machines |
| `workspaces/harbor/`, `workspaces/ember/` | The brands. Harbor's `brand-book.md` and `rules.yaml` are the shared files stage 3 reasons about. | 3 | 9 |
| `checks/test_files.py` | The twelve acceptance criteria as code, grouped by stage, with the routing checks. `-m stage1` runs one stage. Every group is red here and green on the solutions branch. | all | |
| `launchkit/files/seed.py` | The starting state the room inherits, and the code that builds it. `uv run launchkit setup` runs it. | all | |
| `launchkit/cli.py` | `setup` puts the seeded state in place. `ui --reload` runs the chat page. | | |

## The Files panel

<a id="files-panel"></a>

Press **Files** on the chat page. It shows what this conversation produced and what the agent reached this turn. Every acceptance criterion is read from this panel or from the Trace tab, never from a terminal.

Until stage 1 is built it lists anything under `data/` modified since the run started, filtered to picture and sound types, with no filter for the brand and no record of who wrote what. Once stage 1 is built it reads the artifact record instead.

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
