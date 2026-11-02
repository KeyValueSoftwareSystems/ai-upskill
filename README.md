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
| **`session-02-tools`** (you are here) | tools, skills, lookup, MCP and permissions (Session 2, part 1): the main agent and Maya's "every size" |
| `session-02-tools-step1` … `step5` | each step's answer |

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

The opener's code is on this branch too (`approach_llm/`, `approach_graph/`, `launchkit/ui.py`, `launchkit/scoreboard.py`), but its LangGraph parts need the opener branches' dependencies; run them from `session-01-langgraph`.

## Commands

| Command | What it does |
| --- | --- |
| `uv run launchkit run harbor "Poster for the Tidal bottle on a misty lakeshore at dawn."` | One request in the terminal: trace, spec, picture path |
| `uv run launchkit ui` | The chat page: sign in as a person, chat with the main agent, live trace, context view, the files it made, Allow and Deny before a write |
| `uv run launchkit explain` | What the model saw on the last run, in what order, at what cost |
| `uv run launchkit check 1` | Prove step 1 with fake models. `check all` is the CP1.1 gate |
| `uv run launchkit run harbor "..." --model fake:echo` | Force a fake model for one run |
| `uv run launchkit run harbor "..." --facts workspaces/harbor/brand-book.md` | Load a file into the facts section |
| `uv run launchkit onboard samples/moss-and-fern-brand-pack.pdf` | Draft a new brand's workspace from its brand pack PDF. See `docs/onboarding.md` |

## Session 1 · The harness, in four steps

Each step fills one TODO slot in `launchkit/harness/`. Each step has a check. The answer to each step is on its own branch, and each branch contains the previous one's answer.

| Step | Slot | Check | Branch with the answer |
| --- | --- | --- | --- |
| 1 · The agent reads its rules from files | `workspace.py` `load_workspace`, `agent.py` rules section | `check 1` | `session-01-harness-step1` |
| 2 · Check the form, fix it once, then stop | `spec.py` `validate_spec`, `run.py` repair | `check 2` | `session-01-harness-step2` |
| 3 · A tool and a leash | `tools.py`, `limits.py`, `agent.py` picture agent | `check 3` | `session-01-harness-step3` |
| 4 · The request says who you are | `request.py` `resolve_workspace_id` | `check 4` | `session-01-harness-step4` |

Prompt cards for each step are in `docs/`.

## Session 1 · Hand-over to retrieval (CP1.2)

Branch from `session-01-harness-step4`. It is the full CP1.1 harness: `uv run launchkit check all` passes every check.

Where retrieval plugs in:

- `launchkit/harness/agent.py` · `build_copy_agent`: add your `get_brand_details` tool to `tools=[...]` on the copy agent. The copy agent already carries the leash hook, so every tool call goes through the trace with its result size in tokens and counts against the step cap.
- `launchkit/harness/context.py` · `ContextBuilder`: `ctx.set("facts", text)` fills the facts section. Budgets live in `launchkit/settings.py` (`budgets`). A trimmed section says so inside the prompt.
- `uv run launchkit explain` prints what the model saw on the last run, section by section, with tool results as a row.
- `workspaces/harbor/brand-book.md` and `facts.md` hold Harbor's text with clear headings; Ember's are in `workspaces/ember/`.
- `launchkit/harness/request.py`: the workspace id is already resolved from the trusted request. Your tool takes no workspace argument.

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

In step 4, press **Connect Notion** on the chat page and log in to Notion. The page puts a private Tidal card in your Notion; press it again to set the card back.

Offline, or without a key: `LAUNCHKIT_SEARCH=saved` uses the saved pages, `LAUNCHKIT_BOARD=local` uses the board server in this repo, and the fake models need no key. The checks always run offline.

## Session 2 · Tools, skills and MCP, five steps

Run each step on the chat page, as in "Session 2: before you start". In the terminal, `uv run launchkit main harbor "Love the poster. Now all the sizes, please."` does the same. Each step fills one slot, has a check, a card in `docs/` and a branch with the answer.

| Step | Slot | Check | Branch with the answer |
| --- | --- | --- | --- |
| 1 · Tools: one tool, then a toolbox | `picture_tools.py` `PictureDesk` | `check tools1` | `session-02-tools-step1` |
| 2 · Skills: write the know-how down | `launchkit/skills/resize_image/skill.md`, `picture_tools.py` `window_around` | `check tools2` | `session-02-tools-step2` |
| 3 · Lookup: find the right skill | `catalogue.py` `make_run_tool` | `check tools3` | `session-02-tools-step3` |
| 4 · MCP: plug in Maya's board | `mcp_link.py` `connect` | `check tools4` | `session-02-tools-step4` |
| 5 · Permissions: read freely, ask before you write | `catalogue.py` `run_tool` | `check tools5` | `session-02-tools-step5` |

Cards: `docs/tools-1.md` … `docs/tools-5.md`.

## Layout

```
launchkit/
  cli.py            run · ui · explain · check · onboard   (the harness)
  llm.py, images.py, poster.py, scoreboard.py, ui.py, check_setup.py, ask.py   (the opener's shared code)
approach_llm/, approach_graph/   the opener's two approaches
  settings.py       env, paths, limits, section budgets
  harness/          request → workspace → context → copy agent → validate → picture agent → result
  adapters/         model resolver, fake models, image adapters, prices
  web/              FastAPI app and one HTML page
workspaces/         one folder per brand: SOUL.md, AGENTS.md, rules.yaml, facts.md, users.yaml, assets/
samples/            a brand pack PDF to try onboarding with
checks/             one pytest file per step; `launchkit check` wraps them
docs/               setup, glossary, one page per step
```
