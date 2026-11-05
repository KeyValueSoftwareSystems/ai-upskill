# LaunchKit

A marketing assistant built in steps across the session. A marketer asks for a poster. LaunchKit answers with the poster's words (the copy) and its picture, following that brand's rules. Brands are workspaces: a folder of plain files, no code.

| Branch | What it holds |
| --- | --- |
| `session-01-00-setup` | shared code and the setup check |
| `session-01-llm-call` | one LLM call, `approach_llm/app.py`; hands-on sheet in the trainer notes |
| `session-01-langgraph` | a LangGraph pipeline, `approach_graph/graph.py` |
| `session-01-harness` | the agent harness on Agno, built in four steps; the opener's code stays in the repo |
| `session-01-harness-step1` … `step4` | each step's answer |
| `session-01-rag-step1` … `step4` | retrieval (CP1.2): one `get_brand_details` tool, rebuilt four times |
| `session-02-tools` | tools, skills, lookup, MCP and permissions (Session 2, part 1): the main agent and Maya's "every size" |
| `session-02-tools-step1` … `step5` | each step's answer |
| `session-02-orchestration` | agents and orchestration (Session 2, part 2): the main agent, the Tidal launch brief, saved competitor pages |
| `session-02-orchestration-step1`, `step2` | each step's answer |
| **`session-03-memory-step1`** (you are here) | agent memory (Session 3): Session 2's answer plus the memory setup; hands-on 1 (what goes in) starts here |
| `session-03-memory-step2` | hands-on 2 (what comes back, and for how long: the index, then compaction), with hands-on 1 answered |

Each branch contains the previous branch's solution. Fall behind, check out the next one.

## Setup

Needs Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```
git clone <this repo> && cd ai-upskill
uv sync
cp .env.example .env        # add your LITELLM_API_KEY (KeyValue's proxy)
uv run launchkit run harbor "Poster for the Tidal bottle on a misty lakeshore at dawn."   # prints a trace and a spec
uv run launchkit ui         # the harness chat page on http://localhost:8000
```

Keys go through KeyValue's LiteLLM proxy: `LITELLM_API_KEY` and `LITELLM_BASE_URL`. Everyone runs the real model and real pictures. `LAUNCHKIT_IMAGE_PROVIDER` picks who makes the pictures: `gpu` (our GPU, a few seconds each, the default), `litellm` (the image model through the proxy, 30 to 60 seconds each; only when the trainer says the GPU is down) or `placeholder` (a stand-in picture drawn by code).

The opener's code is on this branch too (`approach_llm/`, `approach_graph/`, `launchkit/opener/ui.py`, `launchkit/opener/scoreboard.py`), but its LangGraph parts need the opener branches' dependencies; run them from `session-01-langgraph`.

## Commands

| Command | What it does |
| --- | --- |
| `uv run launchkit run harbor "Poster for the Tidal bottle on a misty lakeshore at dawn."` | One request in the terminal: trace, spec, picture path |
| `uv run launchkit ui` | The chat page, restarting by itself when the code changes: sign in as a person, chat with the main agent, live trace, context view, the files it made, Allow and Deny before a write |
| `uv run launchkit main harbor "How are Hydro Flask, Stanley, Yeti, Owala and Klean Kanteen launching bottles this season?"` | Talk to the main agent: trace, reply, how much its view holds, how long it took |
| `uv run launchkit check orch1` | Prove a step with fake models. `check orch` is the gate for both steps |
| `uv run launchkit explain` | What the model saw on the last Session 1 poster run, in what order, at what cost |
| `uv run launchkit check 1` | Prove step 1 with fake models. `check all` is the CP1.1 gate |
| `uv run launchkit run harbor "..." --model fake:echo` | Force a fake model for one run |
| `uv run launchkit run harbor "..." --facts workspaces/harbor/brand-book.md` | Load a file into the facts section |
| `uv run launchkit onboard samples/moss-and-fern-brand-pack.pdf` | Draft a new brand's workspace from its brand pack PDF. See `docs/onboarding.md` |

## Session 1 · The harness, in four steps

Each step fills one TODO slot. That code now sits in the folders under `launchkit/`: see Layout. Each step has a check. The answer to each step is on its own branch, and each branch contains the previous one's answer.

| Step | Slot | Check | Branch with the answer |
| --- | --- | --- | --- |
| 1 · The agent reads its rules from files | `brands/workspace.py` `load_workspace`, `agents/copy_and_picture_agents.py` rules section | `check 1` | `session-01-harness-step1` |
| 2 · Check the form, fix it once, then stop | `guardrails/poster_check.py` `validate_spec`, `agents/poster_flow.py` repair | `check 2` | `session-01-harness-step2` |
| 3 · A tool and a leash | `tools/generate_image.py`, `guardrails/limits.py`, `agents/copy_and_picture_agents.py` picture agent | `check 3` | `session-01-harness-step3` |
| 4 · The request says who you are | `brands/request.py` `resolve_workspace_id` | `check 4` | `session-01-harness-step4` |

Prompt cards for each step are in `docs/`.

## Session 1 · Hand-over to retrieval (CP1.2)

Branch from `session-01-harness-step4`. It is the full CP1.1 harness: `uv run launchkit check all` passes every check.

Where retrieval plugs in:

- `launchkit/agents/copy_and_picture_agents.py` · `build_copy_agent`: add your `get_brand_details` tool to `tools=[...]` on the copy agent. The copy agent already carries the leash hook, so every tool call goes through the trace with its result size in tokens and counts against the step cap.
- `launchkit/agents/prompt.py` · `ContextBuilder`: `ctx.set("facts", text)` fills the facts section. Budgets live in `launchkit/settings.py` (`budgets`). A trimmed section says so inside the prompt.
- `uv run launchkit explain` prints what the model saw on the last Session 1 poster run, section by section, with tool results as a row. Session 2 runs show their trace on the chat page and in the terminal instead.
- `workspaces/harbor/brand-book.md` and `facts.md` hold Harbor's text with clear headings; Ember's are in `workspaces/ember/`.
- `launchkit/brands/request.py`: the workspace id is already resolved from the trusted request. Your tool takes no workspace argument.

## Session 1 · Retrieval (CP1.2), in four steps

One tool, `get_brand_details`, rebuilt each time it fails. Each step has a check and a page in `docs/`.

| Step | Version | Check | Branch with the answer |
| --- | --- | --- | --- |
| 1 · A tool to fetch brand details | `get_brand_details()`: the whole brand file | `check rag1` | `session-01-rag-step1` |
| 2 · Return only what matches | `get_brand_details(query)`: top 5 chunks by keywords (BM25) | `check rag2` | `session-01-rag-step2` |
| 3 · Match what the words mean | `get_brand_details(query)`: top 5 by meaning, local `bge-small-en-v1.5`, LanceDB vector database | `check rag3` | `session-01-rag-step3` |
| 4 · Keep each brand to its own chunks | `get_brand_details(query)`: the same search, filtered to the request's workspace inside the query | `check rag4` | `session-01-rag-step4` |

From step 3 on, brand documents live in a vector database under `data/brand-store/`. Uploading a brand file indexes it; for the brands in this repo run `uv run launchkit index` once. `uv run launchkit check rag` runs every retrieval check on the branch.

## Session 2: before you start

Session 2 starts on the branch `session-02-tools`. Do this before the day; it takes about fifteen minutes.

| You need | Why | How |
| --- | --- | --- |
| KeyValue's proxy key | the model and the pictures | the trainer gives you one; `LITELLM_API_KEY` in `.env` |
| KeyValue's VPN | the proxy and our picture GPU are reached through it | connect before you start |
| Your own Tavily key | from step 3, `search_web` reads the live web | free at https://app.tavily.com: 1,000 searches a month, no card; `TAVILY_API_KEY` in `.env` |
| A Notion account | steps 4 and 5 read and write a card in your own Notion | a free personal account is enough; you connect it from the chat page in step 4 |

```
git checkout session-02-tools
uv sync
cp .env.example .env        # already have a .env? copy in the Session 2 lines: LAUNCHKIT_BOARD, LAUNCHKIT_SEARCH, TAVILY_API_KEY
uv run launchkit index      # once on a fresh clone: puts the brand books in the vector database get_brand_details searches
uv run launchkit ui         # the chat page on http://localhost:8000
```

How each step runs:

1. Start on the step's branch (the step tables below). Restart `uv run launchkit ui` after each checkout.
2. Break it first: on the chat page, sign in as Maya at Harbor, press **New conversation** and send the ask on the step's card in `docs/`. Leave **Model** empty for the real model. `fake:tools` (steps 1 to 5) or `fake:brief` (orchestration steps 1 and 2) is a scripted model built into LaunchKit: it makes the same mistake every time.
3. Build: hand the card's prompt to your coding agent, then prove it with the card's check, for example `uv run launchkit check tools1`.
4. Run it again on the chat page. The **Trace** tab shows every tool call, the **Context** tab shows how many tokens the main agent holds, and a write asks **Allow** or **Deny** in the chat.
5. Behind? Check out the step's answer branch and carry on.

The pictures come from the conversation, never from a hidden file. Maya's approved poster is in the repo at `samples/approved/tidal-poster.jpg`, and her shoot photo (step 3) at `samples/shoot/tidal-shoot.jpg`: attach them with 📎 next to the message box, or with `--attach` in the terminal. Or ask for a new poster first, in the same conversation. The picture tools work on the newest picture in the conversation.

Before step 4, make Maya's Tidal launch brief in your own Notion by hand: a new page named "Tidal launch: campaign brief", with the text of `samples/board/tidal-card-to-paste.txt` pasted in (Cmd+Shift+V pastes it as plain text). Then press **Connect Notion** on the chat page and log in. Connecting only logs in; the agent reads and writes the card only when an ask needs it. To run a step again, edit the card back by hand.

Offline, or without a key: `LAUNCHKIT_SEARCH=saved` uses the saved pages, `LAUNCHKIT_BOARD=local` uses the board server in this repo, and the fake models need no key. The checks always run offline.

## Session 2 · Tools, skills and MCP, five steps

Run each step on the chat page, as in "Session 2: before you start". In the terminal, `uv run launchkit main harbor "Love the poster. Now all the sizes, please."` does the same. Each step fills one slot, has a check, a card in `docs/` and a branch with the answer.

| Step | Slot | Check | Branch with the answer |
| --- | --- | --- | --- |
| 1 · Tools: one tool, then a toolbox | `tools/resize_poster.py` `PictureDesk` | `check tools1` | `session-02-tools-step1` |
| 2 · Skills: write the know-how down | `launchkit/skills/resize_image/skill.md`, `tools/resize_poster.py` `window_around` | `check tools2` | `session-02-tools-step2` |
| 3 · Lookup: find the right skill | `tools/catalogue.py` `make_run_tool` | `check tools3` | `session-02-tools-step3` |
| 4 · MCP: plug in Maya's board | `mcp/client.py` `connect` | `check tools4` | `session-02-tools-step4` |
| 5 · Permissions: read freely, ask before you write | `tools/catalogue.py` `run_tool` | `check tools5` | `session-02-tools-step5` |

Cards: `docs/tools-1.md` … `docs/tools-5.md`.

## Session 2 · Agents and orchestration, two steps

| Step | Slot | Check | Branch with the answer |
| --- | --- | --- | --- |
| 1 · One agent and a skill | `launchkit/skills/competitor_research/skill.md` | `check orch1` | `session-02-orchestration-step1` |
| 2 · Hand the digging to subagents | `orchestration/research_team.py` `build_research_agent`, `orchestration/research_team.py`, the skill | `check orch2` | `session-02-orchestration-step2` |

Cards: `docs/orch-1.md`, `docs/orch-2.md`.

## Session 3: before you start

Session 3 starts on the branch `session-03-memory-step1`. Nothing new to sign up for: the same `.env` as Session 2.

```
git checkout session-03-memory-step1
uv sync
uv run launchkit check mem0     # the setup: Breeze at Harbor, Sam signed in, the store, the seeded month, the Tidal launch
uv run launchkit ui
```

Then recreate Maya's Tidal launch, the conversation this session starts from: on the chat page, or with `uv run launchkit replay harbor samples/sessions/tidal_launch.txt`. `docs/memory-1.md` walks through it.

Every branch here is the **start** of a hands-on. The one before it is already answered, so if you fall behind, check out the next branch. Your own edits and new files would block the checkout, so set them aside first:

```
git stash -u                                   # your changes and new files, kept aside
git checkout session-03-memory-step2
```

How each step runs:

1. Start on the step's branch and keep `uv run launchkit ui` running. It restarts by itself when a `.py` file under `launchkit/` changes, including after a checkout: the terminal says `Reloading...`, and you reload the browser tab. `uv run launchkit ui --no-reload` turns that off.
2. Everything Maya types goes on the chat page: sign in as Maya (or Sam) at Harbor, press **New conversation**, leave **Model** empty for the real model, and send the message on the card. An ask to keep a memory comes up in the chat with three buttons: **Just me**, **Everyone at the brand** and **Don't keep**.
3. The terminal is for what Maya would not do on the page: `uv run launchkit forget harbor` to start a step again from an empty store (conversations stay), `uv run launchkit seed-memories harbor` for hands-on 2's month of rows, `uv run launchkit replay` to send a file of Maya's messages as one conversation, `uv run launchkit store …` and `uv run launchkit memories …` to read the store, and `uv run launchkit check mem1` or `mem2` to prove a hands-on.
4. `fake:memory` is the fallback: a scripted model that gives the same answer every time. Type it in **Model** when you are offline, without a key, or want the card's exact output. The checks always run on it.

### See what the agent stored

Everything Agno keeps for LaunchKit is one SQLite file, `data/sessions.db`. It appears after the first run; `data/` is not in git. Three tables matter in this session:

| Table | One row per | Columns to watch |
| --- | --- | --- |
| `agno_memories` | thing the agent kept | `memory`, `user_id` (`maya`, `sam`, or `harbor:everyone` for everyone at Harbor), `topics` (the kind, `author:`, `source:`), `created_at` |
| `agno_sessions` | conversation | `session_id`, `user_id`, `summary` (from hands-on 2, part B) |
| `agno_runs` | turn in a conversation | `session_id`, `run_index`, `status`, `run_data` |

In the terminal:

```
uv run launchkit store                             # every table and how many rows it holds
uv run launchkit store agno_memories               # the memory rows, column by column, as Agno stored them
uv run launchkit store agno_memories --user maya   # only Maya's own rows; --user harbor:everyone for Harbor's
uv run launchkit store agno_sessions               # one row per conversation; the summary column is hands-on 2's
uv run launchkit store agno_runs                   # one row per turn
uv run launchkit store agno_memories --schema      # a table's columns and their types
uv run launchkit memories harbor --user maya       # what one person may read: their rows and Harbor's, as get_user_memories returns them
```

Long values are cut at 100 characters; add `--full` to see them whole, and `--limit N` for more than 20 rows.

In your editor: install the **SQLite Viewer** extension (`qwtel.sqlite-viewer`; it works in VS Code and Cursor) and open `data/sessions.db` from the file explorer. Each table opens as a grid with its real columns. Close and reopen the tab after a run to see new rows. Use it to look, not to edit: to start again, `uv run launchkit forget harbor` empties Harbor's memory rows.

## Session 3 · Agent memory, two hands-on steps

| Hands-on (start on) | Parts and slots | Check | Card |
| --- | --- | --- | --- |
| 1 · What goes in (`session-03-memory-step1`) | 1, switch it on: `agents/main_agent.py` `build_main_agent`, then sort on `docs/memory-sort.html`; 2, what earns a write: `agents/main_agent.py` `build_main_agent`, `memory/write_rules.md`; 3, whose it is: `memory/write_gate.py` `ask_before_keeping` | `check mem1` | `docs/memory-1.md` |
| 2 · What comes back, and for how long (`session-03-memory-step2`) | A, read it back cheaply: `memory/index.py` `memory_index`, `recall`; B, one long conversation: `agents/main_agent.py` `build_main_agent`, `memory/compaction.py` `must_keep` | `check mem2` | `docs/memory-2.md` |

`uv run launchkit check mem` runs every memory check on the branch.

## Layout

```
launchkit/
  agents/                                who thinks: the agent Maya talks to, and what it sees
    copy_and_picture_agents.py           Session 1's copy and picture agents
    main_agent.py                        the agent Maya talks to; build_catalogue lists its tools
    poster_flow.py                       Session 1's fixed order: copy, then picture
    prompt.py                            what the model sees: rules, task, facts
  tools/                                 what the agent can do: one file per tool, named after the tool
    catalogue.py                         the catalogue and the three doors: find_tool, run_skill, run_tool
    check_copy.py                        checks a poster's words against the brand's limits
    describe_image.py                    looks at a photo the marketer gave
    generate_image.py                    draws a new picture with the paid image model
    get_brand_details.py                 looks up the brand's guide and product facts
    resize_poster.py                     cuts the poster you already have: detect_focal_point, crop, expand_canvas, scale
    search_web.py                        searches the web (Tavily), or the saved pages offline
    text_to_speech.py                    turns a script into a voice-over
  skills/                                how-tos: one folder per skill, with skill.md
    competitor_research, ingest_image, market_research, on_brand_copy, post_to_board, resize_image, voice_over
  mcp/                                   outside services over MCP: one common client, one file per server
    client.py                            the common MCP adapter: connects a server, turns its tools into catalogue entries
    servers/                             add a file here to connect a new MCP server
      local_board.py                     the offline board, the same every run
      local_board_server.py              the offline board's own MCP server
      notion.py                          Maya's real board: Notion's MCP server
  guardrails/                            what the harness stops or checks
    limits.py                            step cap and image budget
    poster_check.py                      checks the poster and asks the model to repair it
  memory/                                what one conversation keeps, and what outlives it
    attached_pictures.py                 pictures attached or made in this conversation
    chat_history.py                      past turns of this conversation
    long_term.py                         the memory table, its door (MemoryDb) and who may read which row
    write_gate.py                        Maya says yes, and whose it is, before a row is kept (hands-on 1, part 3)
  knowledge/                             brand facts the agent looks up (RAG)
    brand_index.py                       puts the brand books in the vector database (launchkit index)
    brand_library.py                     reads a brand's files
    brand_search.py                      finds the brand lines that match a question
  brands/                                a brand's workspace: rules, users, onboarding
    onboard.py                           makes a workspace from a brand pack
    request.py                           works out which brand a request is for
    users.py                             who can sign in
    workspace.py                         loads a brand's SOUL, AGENTS and rules
  orchestration/                         helper agents the main agent hands work to
    research_team.py                     the research helper agent, and research / research_many that run it
  adapters/                              plumbing: models, fakes, image providers, prices
    fakes.py                             scripted models for the checks and offline runs
    gpu_images.py                        our GPU picture service
    image_providers.py                   picks who makes the pictures
    llm.py                               one plain model call, used for vision
    models.py                            which model a run uses
    pricing.py                           token prices
  web/                                   the chat page
    app.py                               the chat page's server
    index.html                           the chat page
  opener/                                the opener's demo: one LLM call vs LangGraph
    ask.py
    images.py
    poster.py
    scoreboard.py
    ui.py
  check_setup.py                         checks your machine before the session
  cli.py                                 the launchkit command
  settings.py                            .env, paths, limits
  trace.py                               what the Trace tab shows
approach_llm/, approach_graph/   the opener's two approaches
workspaces/   one folder per brand: SOUL.md, AGENTS.md, rules.yaml, facts.md, users.yaml, assets/
samples/      pictures, photos and brand packs to try
checks/       one pytest file per step; `launchkit check` wraps them
docs/         setup, glossary, one card per step
```

### Where a change goes

| The ask | Where |
| --- | --- |
| The agent needs a new ability | a new file in `tools/`, named after the tool, and one `Entry` line in `build_catalogue` (`agents/main_agent.py`) |
| A how-to for a kind of job | a new folder in `skills/` with a `skill.md` |
| A new outside service over MCP | a new file in `mcp/servers/` with `on()` and `entries()` |
| Stop, cap or check something | `guardrails/` |
| Change what the model sees | `agents/prompt.py`, and the task text in `agents/main_agent.py` |
| Hand work to a helper agent | `orchestration/` |
| Keep something past the conversation, or change what is kept | `memory/`: the store and its door (`long_term.py`); each memory hands-on adds its own files there |
| A new brand | `uv run launchkit onboard` writes `workspaces/<brand>/` (`brands/onboard.py`) |
| New brand facts to look up | `workspaces/<brand>/facts.md`, then `uv run launchkit index` (`knowledge/`) |
