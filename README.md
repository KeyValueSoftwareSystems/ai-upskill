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
| **`session-02-orchestration`** (you are here) | agents and orchestration (CP2.2): the main agent, the Tidal card, saved competitor pages |
| `session-02-orchestration-step1`, `step2` | each checkpoint's answer |

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
| `uv run launchkit main harbor "How are Northline, Ridgeway, Stillwater, Kestrel and Alder Co. launching bottles this season?"` | Talk to the main agent: trace, reply, how much its view holds, how long it took |
| `uv run launchkit check orch1` | Prove a checkpoint with fake models. `check orch` is the CP2.2 gate |
| `uv run launchkit explain` | What the model saw on the last run, in what order, at what cost |
| `uv run launchkit check 1` | Prove step 1 with fake models. `check all` is the CP1.1 gate |
| `uv run launchkit run harbor "..." --model fake:echo` | Force a fake model for one run |
| `uv run launchkit run harbor "..." --facts workspaces/harbor/brand-book.md` | Load a file into the facts section |
| `uv run launchkit onboard samples/moss-and-fern-brand-pack.pdf` | Draft a new brand's workspace from its brand pack PDF. See `docs/onboarding.md` |

## The build, in four steps

Each step fills one TODO slot in `launchkit/harness/`. Each step has a check. The answer to each step is on its own branch, and each branch contains the previous one's answer.

| Step | Slot | Check | Branch with the answer |
| --- | --- | --- | --- |
| 1 · The agent reads its rules from files | `workspace.py` `load_workspace`, `agent.py` rules section | `check 1` | `session-01-harness-step1` |
| 2 · Check the form, fix it once, then stop | `spec.py` `validate_spec`, `run.py` repair | `check 2` | `session-01-harness-step2` |
| 3 · A tool and a leash | `tools.py`, `limits.py`, `agent.py` picture agent | `check 3` | `session-01-harness-step3` |
| 4 · The request says who you are | `request.py` `resolve_workspace_id` | `check 4` | `session-01-harness-step4` |

Prompt cards for each step are in `docs/`.

## Tools, skills and MCP, five steps

Talk to the main agent with `uv run launchkit main harbor "Love the poster. Now all the sizes, please."`. Each step fills one slot, has a check, a card in `docs/` and a branch with the answer.

| Step | Slot | Check | Branch with the answer |
| --- | --- | --- | --- |
| 1 · Tools: one tool, then a toolbox | `picture_tools.py` `PictureDesk` | `check tools1` | `session-02-tools-step1` |
| 2 · Skills: write the know-how down | `launchkit/skills/resize_image/skill.md`, `picture_tools.py` `window_around` | `check tools2` | `session-02-tools-step2` |
| 3 · Lookup: find the right skill | `catalogue.py` `make_run_tool`, the note on `generate_image` in `main.py` | `check tools3` | `session-02-tools-step3` |
| 4 · MCP: plug in Maya's board | `mcp_link.py` `connect` | `check tools4` | `session-02-tools-step4` |
| 5 · Permissions: read freely, ask before you write | `catalogue.py` `run_tool` | `check tools5` | `session-02-tools-step5` |

Cards: `docs/tools-1.md` … `docs/tools-5.md`.

## Agents and orchestration, two checkpoints

| Checkpoint | Slot | Check | Branch with the answer |
| --- | --- | --- | --- |
| CP2.2a · One agent and a skill | `launchkit/skills/competitor_research/skill.md` | `check orch1` | `session-02-orchestration-step1` |
| CP2.2b · Hand the digging to subagents | `agent.py` `build_research_agent`, `research.py`, the skill | `check orch2` | `session-02-orchestration-step2` |

Cards: `docs/orch-1.md`, `docs/orch-2.md`.

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

## Hand-over to retrieval (CP1.2)

Branch from `session-01-harness-step4`. It is the full CP1.1 harness: `uv run launchkit check all` passes every check.

Where retrieval plugs in:

- `launchkit/harness/agent.py` · `build_copy_agent`: add your `get_brand_details` tool to `tools=[...]` on the copy agent. The copy agent already carries the leash hook, so every tool call goes through the trace with its result size in tokens and counts against the step cap.
- `launchkit/harness/context.py` · `ContextBuilder`: `ctx.set("facts", text)` fills the facts section. Budgets live in `launchkit/settings.py` (`budgets`). A trimmed section says so inside the prompt.
- `uv run launchkit explain` prints what the model saw on the last run, section by section, with tool results as a row.
- `workspaces/harbor/brand-book.md` and `facts.md` hold Harbor's text with clear headings; Ember's are in `workspaces/ember/`.
- `launchkit/harness/request.py`: the workspace id is already resolved from the trusted request. Your tool takes no workspace argument.

## Retrieval (CP1.2), in four steps

One tool, `get_brand_details`, rebuilt each time it fails. Each step has a check and a page in `docs/`.

| Step | Version | Check | Branch with the answer |
| --- | --- | --- | --- |
| 1 · A tool to fetch brand details | `get_brand_details()`: the whole brand file | `check rag1` | `session-01-rag-step1` |
| 2 · Return only what matches | `get_brand_details(query)`: top 5 chunks by keywords (BM25) | `check rag2` | `session-01-rag-step2` |
| 3 · Match what the words mean | `get_brand_details(query)`: top 5 by meaning, local `bge-small-en-v1.5`, LanceDB vector database | `check rag3` | `session-01-rag-step3` |
| 4 · Keep each brand to its own chunks | `get_brand_details(query)`: the same search, filtered to the request's workspace inside the query | `check rag4` | `session-01-rag-step4` |

From step 3 on, brand documents live in a vector database under `data/brand-store/`. Uploading a brand file indexes it; for the brands in this repo run `uv run launchkit index` once. `uv run launchkit check rag` runs every retrieval check on the branch.
