# Session 2: Tools, Agents & Orchestration — trainer walkthrough

This file is the trainer's hands-on walkthrough for Session 2: the branches, what to run, and what the room should see at each step. It follows the session from setup to the close.

The story (Maya, the wall she hits at each step, the discussion points, the Scribble cases) is in the session guide, "Session 2: how to run it", kept next to this file as `session-2-how-to-run-it.pdf`. This file does not repeat it. Each block below opens with what the step teaches and what to show, then gives the exact asks, commands and expected output.

## Contents

1. [Before the session](#1-before-the-session)
2. [Running order](#2-running-order)
3. [How every hands-on step runs](#3-how-every-hands-on-step-runs)
4. [Tools, skills and MCP: steps 1 to 5](#4-tools-skills-and-mcp-steps-1-to-5)
5. [Agents and orchestration: steps 1 and 2](#5-agents-and-orchestration-steps-1-and-2)
6. [Ready-made skills to show when there is time](#6-ready-made-skills-to-show-when-there-is-time)
7. [Troubleshooting](#7-troubleshooting)

## Words used in this file

| Word | Meaning |
| --- | --- |
| Main agent | The one agent Maya talks to. It decides what runs. In Session 1 it was the copy agent. |
| Tool | A function the model may ask for. The model sees only its name, its inputs and its description. |
| Skill | A plain-words how-to file (`launchkit/skills/<name>/skill.md`). It says which tools to use, in what order, and how to judge the result. The agent loads it only when it needs it. |
| The three doors | From step 3 the main agent holds only `find_tool` (find a skill or tool), `run_skill` (load a skill) and `run_tool` (run any tool by name), not every tool. |
| MCP | Model Context Protocol: a common plug between an agent and an outside service. The service's MCP server lists its own tools. |
| Read / write | Every tool says if it only looks (read) or changes something outside LaunchKit (write). From step 5 a write asks Maya first. |
| Subagent | An agent another agent calls like a tool. It works in its own view and hands back only a short answer. |
| Orchestrator | The agent that splits a job, writes the briefs, sends them out and gathers the answers. Here: the main agent. |
| Fake model | A scripted stand-in for the model, typed in the chat page's **Model** box. `fake:tools` for steps 1 to 5, `fake:brief` for orchestration steps 1 and 2. It makes the same mistake every time and needs no key. |
| Check | `uv run launchkit check <step>`: the repo's own pytest checks for a step, with fake models, offline. |
| LiteLLM proxy | KeyValue's server that passes our model calls on (`llm.keyvalue.systems`). Reached only over the VPN. |

## 1. Before the session

### What every participant needs

The full list is in the README, "Session 2: before you start". In short:

- The Session 1 setup: Python 3.12+, uv, git, the repo, a coding agent, and a `.env` with `LITELLM_API_KEY`.
- The VPN on for the whole session. The proxy and the picture GPU are reached only over it.
- Their own free Tavily key in `.env` as `TAVILY_API_KEY` (https://app.tavily.com, no card). Needed from step 3, for live web search.
- A Notion account (a free personal one is enough). Needed for steps 4 and 5.

### Setup steps

Same repo as Session 1. Do not clone again.

```bash
git checkout session-02-tools
uv sync
uv run python -m launchkit.check_setup
```

- **`.env` from Session 1:** copy in the Session 2 lines from `.env.example`: `LAUNCHKIT_BOARD`, `LAUNCHKIT_SEARCH`, `TAVILY_API_KEY` and `LAUNCHKIT_TIMEOUT=90`.
- **The setup check** must end with **Setup complete. Next: open docs/tools-1.md, the first step card.** Under anything marked FAIL it prints a fix.
- **On a fresh clone only**, run `uv run launchkit index` once. It puts the brand books in the vector database that `get_brand_details` searches. The first run downloads the embedding model.
- **Session 1 extras:** anyone who installed langgraph in Session 1 needs nothing special. `uv sync` removes what this branch does not use. Only `uv add` changes git files; undo it with `git checkout -- pyproject.toml uv.lock`.

### Notion, before step 4

Each person does this once, by hand, as Maya would:

1. In their own Notion, make a new page named **Tidal launch: campaign brief**.
2. Paste in the text of `samples/board/tidal-card-to-paste.txt` as plain text (Cmd+Shift+V).
3. On the chat page, sign in as Maya and press **Connect Notion**. Notion's login opens in a new tab.

Connecting only logs in. It writes nothing. To run a step again, edit the card back by hand.

### Trainer checklist

- The setup check passes on your machine, with the VPN on.
- Your Tidal launch brief is in your Notion, and **Connect Notion** shows **Notion connected**.
- You have run each step's **Run it again** on the real model on the chat page, on its answer branch.
- For orchestration, start the page with `LAUNCHKIT_SEARCH_DELAY=0.4` (see [section 5](#5-agents-and-orchestration-steps-1-and-2)).
- Have the two pictures ready to attach: `samples/approved/tidal-poster.jpg` (Maya's approved poster) and `samples/shoot/tidal-shoot.jpg` (her shoot photo).

## 2. Running order

| Guide step | Segment | Branch | What happens | Done when |
| --- | --- | --- | --- | --- |
| Before | Setup | `session-02-tools` | `uv sync`, `.env`, the setup check, Notion card. See [section 1](#1-before-the-session). | **Setup complete** |
| 0 | Where we left Maya | none | Talk from the guide: the needs board, one agent decides, "every size" fails live. | n/a |
| 1 | Tools | `session-02-tools` | Build `centre_crop`, then four more tools. | `check tools1`: 7 passed |
| 2 | Skills | `session-02-tools-step1` | Write the `resize_image` skill and the fit rule. | `check tools2`: 6 passed |
| 3 | Lookup | `session-02-tools-step2` | Build `run_tool`: the agent holds three doors, not every tool. | `check tools3`: 11 passed |
| 4 | MCP | `session-02-tools-step3` | Build `connect`: Maya's Notion board joins the catalogue. | `check tools4`: 10 passed |
| 5 | Permissions | `session-02-tools-step4` | A write asks Maya first. | `check tools5`: 4 passed |
| 6 | What is left on the brief | none | Talk only. | n/a |
| 7 | One agent and a skill | `session-02-orchestration` | Write the `competitor_research` skill. | `check orch1`: 4 passed |
| 8 | When a subagent earns its place | none | Talk only. | n/a |
| 9 | Subagents | `session-02-orchestration-step1` | Build the research subagent and run five at once. | `check orch2`: 6 passed; `check orch`: 39 passed |
| 10–11 | The bill, the close | none | Talk only. | n/a |

**Catching up.** Each step's answer is on its own branch, and each branch holds the previous step's answer. Anyone who falls behind runs `git stash`, checks out the answer branch, and carries on.

**The two parts.** `session-02-orchestration` starts from the tools part's answer (`session-02-tools-step5`), so the main agent, the doors and the permission rule are all there.

`main` holds only the trainer notes.

## 3. How every hands-on step runs

Every step has a card in `docs/` (`tools-1.md` to `tools-5.md`, `orch-1.md`, `orch-2.md`) and runs in the same four beats.

1. **Break it first.** On the chat page, before anyone builds, send the card's ask and watch it fail. Which model to break it on is in the guide's hands-on map. Say it out loud when you use the fake.
2. **Build.** Each person hands the card's prompt to their coding agent.
3. **Prove it.** `uv run launchkit check <step>`. All checks pass.
4. **Run it again** on the chat page, usually on the real model.

**The chat page.** `uv run launchkit ui`, then open http://localhost:8000.

- Sign in as **Maya (marketer)** at **Harbor**, then press **New conversation** for each new ask.
- **Model** box: empty means the real model, through the proxy. `fake:tools` or `fake:brief` means the fake.
- 📎 next to the message box attaches a picture. The picture tools work on the newest picture in the conversation.
- **Trace** tab: every tool call and model call. **Context** tab: how many tokens the main agent holds this turn. **Files** tab: what the run made.
- A write shows **Allow** / **Deny** in the chat (from step 5).
- A slow model call shows on the Working line: "the model did not answer in 90 s, trying again: 2 of 4".

**After every `git checkout`, restart `launchkit ui`.** It does not reload code.

**The real model does not answer the same way every time.** If a run takes a wrong turn (it answers without loading the skill, or without searching), press **New conversation** and send the same ask again.

## 4. Tools, skills and MCP: steps 1 to 5

### Step 1 · Tools: one tool, then a toolbox

**What it teaches.** A tool is a function the model may ask for. The model sees only the name, inputs and description; one tool use costs two model calls. A tool does exactly what it is told, and one way to work fails when the shape changes a lot.

**What to show.** Every size comes back from `centre_crop`, and the web banner (1200×628) cuts off the bottle's base. Then four tools, and the model drives them a different way on each run.

- **Start:** `session-02-tools`. Card: `docs/tools-1.md`.
- **The ask:** attach `samples/approved/tidal-poster.jpg`, then send "Love the poster. Now all the sizes, please."
- **Break it first (real model):** the agent says it cannot resize: it holds only `get_brand_details` and `generate_image`.
- **Build:** prompt card 1 (`PictureDesk.centre_crop`), run it, look at the banner. Then prompt card 2 (`detect_focal_point`, `crop`, `expand_canvas`, `scale`).
- **Prove it:** `uv run launchkit check tools1`, 7 passed.
- **Run it again (real model):** five sizes come back. Point at the budget: Session 1's image budget is 3, yet five come back, because a size cuts the existing poster in plain code and makes no paid picture. Then watch the Trace: the model picks `scale` and squashes the bottle, crops before it finds the bottle, or adds bars where a crop was fine.
- **Answer:** `session-02-tools-step1`.

### Step 2 · Skills: write the know-how down

**What it teaches.** The tools know how to act, but not which one, in what order, or when to stop. A skill is that know-how in a plain-words file the agent reads only when it needs it.

**What to show.** The same ask, now every size with the bottle whole, and the brand's sizes only.

- **Start:** `session-02-tools-step1`. Card: `docs/tools-2.md`.
- **Break it first (real model):** the same ask. Results change from run to run. On `fake:tools` it picks `scale` every time and squashes the bottle.
- **Build:** the `resize_image` skill (plain words) and `window_around`, the fit rule (plain code, the same answer every time).
- **Prove it:** `uv run launchkit check tools2`, 6 passed.
- **Run it again (real model):** new conversation, attach the poster, same ask. Every size is a crop around the bottle. The bars are the safety net for a shape the bottle cannot fit.
- **Ready-made, with its moment:** `check_copy` and the `on_brand_copy` skill. Make a poster first in the same conversation ("A poster for the Tidal bottle on a misty lakeshore at dawn."), then "Shorter headline, please." The Trace shows `check_copy` catching long words before the answer goes back.
- **Answer:** `session-02-tools-step2`.

### Step 3 · Lookup: find the right skill

**What it teaches.** Every tool's description and every skill's line ride along on every turn, used or not. Three doors (`find_tool`, `run_skill`, `run_tool`) replace the whole list. A skill's "Hides" line keeps its raw tools out of `find_tool`'s answer, so the agent cannot skip the skill.

**What to show.** The tokens a greeting sends, before and after.

- **Start:** `session-02-tools-step2`. Card: `docs/tools-3.md`.
- **Break it first (real model):** new conversation, send "Morning!". The model line in the Trace sends about 1,500 tokens for a greeting that needs no tool.
- **Build:** `run_tool` in `launchkit/tools/catalogue.py` (about 20 lines).
- **Prove it:** `uv run launchkit check tools3`, 11 passed.
- **Run it again (real model):**
  - "Morning!" again in a new conversation: about 880 tokens.
  - The photo ask: new conversation, attach `samples/shoot/tidal-shoot.jpg`, send "Use our shoot photo for the story size." Expect `find_tool`, then `run_skill("ingest_image")`, then `describe_image`, `detect_focal_point` and `crop` through `run_tool`. No paid picture.
- **Ready-made skills that arrive here:** `market_research` (live web search), `ingest_image` and `voice_over`. See [section 6](#6-ready-made-skills-to-show-when-there-is-time).
- **Answer:** `session-02-tools-step3`.

### Step 4 · MCP: plug in Maya's Notion board

**What it teaches.** An MCP server describes its own tools: name, description, schema, and whether each only reads. `connect` turns them into catalogue entries in a few lines, with nothing written by hand. New power brings new risk: Notion also offers `notion-delete-pages`.

**What to show.** The agent reads Maya's real brief from her Notion, then puts the sizes on the card and moves it to Ready for review. Then open the card in Notion and check it.

- **Start:** `session-02-tools-step3`. Card: `docs/tools-4.md`. Everyone has made the Notion card and pressed **Connect Notion** (see [section 1](#notion-before-step-4)).
- **Break it first (real model):** "Take the Tidal launch brief from our Notion." The agent finds no skill or tool for it.
- **Build:** `connect(server)` in `launchkit/mcp/client.py`.
- **Prove it:** `uv run launchkit check tools4`, 10 passed.
- **Run it again (real model, your Notion), in one conversation:**
  1. "Take the Tidal launch brief from our Notion." `find_tool` lists `post_to_board` first; the agent reads the card.
  2. Attach the poster, then "Love the poster. Now all the sizes, please."
  3. "Put the new sizes on the Tidal launch brief in Notion, and move it to Ready for review."
- **Then open the card in Notion.** The Files line lists the new file names, and Status says Ready for review. Notion's MCP tools here cannot upload images, so the card lists file names; a real team would attach the images. Point out that an agent can say "done" when Notion took the call but changed nothing: always check.
- **Offline backup:** `LAUNCHKIT_BOARD=local` in `.env` uses the small board server in the repo (`read_card`, `attach_files`, `update_status`, `remove_files`). The fakes and the checks always use it.
- **Answer:** `session-02-tools-step4`.

### Step 5 · Permissions: read freely, ask before you write

**What it teaches.** The rule lives in code, at the one door every tool goes through (`run_tool`), so it covers every tool, including tools an outside MCP server adds. A read runs. A write stops and asks Maya, with exactly what it is about to change. This is Session 1's leash, grown up: the leash caps spending, this caps change.

**What to show.** The agent removes last week's approved files to "keep the card clean". After the build, the chat asks before each write, and Maya denies the delete.

- **Start:** `session-02-tools-step4`. Card: `docs/tools-5.md`.
- **Break it first (fake, `fake:tools`):** "Put the new sizes on the Tidal launch brief in Notion." The Trace shows `remove_files` taking out last week's approved files. The real model usually keeps them, so break it on the fake and say so.
- **Build:** four lines in `run_tool`: a write asks `self.approve` first; a no is recorded and the tool never runs.
- **Prove it:** `uv run launchkit check tools5`, 4 passed.
- **Run it again:**
  - On `fake:tools`: the chat asks before each write. Allow `attach_files` and `update_status`, deny `remove_files`. The card ends with both weeks' files, ready for review.
  - On the real model and your Notion: make the sizes first in the conversation, then "Put the new sizes on the Tidal launch brief in Notion, and move it to Ready for review." The chat asks before `notion-update-page` and `notion-create-comment`. Read what each one will change before pressing **Allow**.
- **Answer:** `session-02-tools-step5`.

## 5. Agents and orchestration: steps 1 and 2

Start the chat page for this part with a pretend wait of 0.4 s per saved-page search, so the fake model shows the speed gain:

```bash
LAUNCHKIT_SEARCH_DELAY=0.4 uv run launchkit ui
```

The ask for both steps:

```text
How are Hydro Flask, Stanley, Yeti, Owala and Klean Kanteen launching bottles this season? One paragraph each.
```

On the fake model the reply only names the sites it read; the real model writes the paragraphs.

### Orchestration step 1 · One agent and a skill (guide step 7)

**What it teaches.** A skill adds ability inside one view. Everything a tool returns stays in that view and rides along on every later turn.

**What to show.** It works. Then the Context tab: about 9,900 tokens of pages in the main agent's view, still there when Maya asks for a headline.

- **Start:** `session-02-orchestration`. Card: `docs/orch-1.md`.
- **Break it first (fake, `fake:brief`):** the agent looks for a skill, finds only `market_research`, and replies "I have no skill for competitor research yet." The real model often borrows `market_research` and answers anyway, so break it on the fake and say so.
- **Build:** the `competitor_research` skill (plain words).
- **Prove it:** `uv run launchkit check orch1`, 4 passed.
- **Run it again (fake, `fake:brief`), new conversation:**
  - The Trace: `run_skill("competitor_research")`, then five `search_web` calls, one after another.
  - The Context tab: 9,915 tokens of tool results, 0 of history, 2.1 s.
  - Then, in the same conversation, "Write one headline for the Tidal poster." The Context tab: 0 tokens of tool results, 10,008 tokens of history carried in.
- **On the real model (trainer):** leave **Model** empty. Expect about 10,300 tokens of pages in view and 13 to 21 seconds.
- **Answer:** `session-02-orchestration-step1`.

### Orchestration step 2 · Hand the digging to subagents (guide step 9)

**What it teaches.** A subagent changes what the main agent sees: the noisy digging happens in its own view and only a short report comes back. Independent pieces run side by side. The agent that reads the web holds no tool that writes. It is not free: six model calls instead of one, and each research agent knows only its brief.

**What to show.** The same ask: five research agents at once, five short reports, and a small main view. Then the headline turn carries almost nothing.

- **Start:** `session-02-orchestration-step1`. Card: `docs/orch-2.md`.
- **Break it first (real model):** nothing fails. The problem is the 10,300 tokens of pages from step 1. Run step 1's command and keep its last line.
- **Build, two parts:** the research agent (`build_research_agent`, `search_web` only, no session store, no chat history), then `research` and `research_many` as read tools, and the skill changed to call `research_many` once with one brief per competitor. Each brief names this month and year (the research agent has no clock) and carries the never-say claims.
- **Prove it:** `uv run launchkit check orch2`, 6 passed. Then the gate for the part: `uv run launchkit check orch`, 39 passed.
- **Run it again (fake, `fake:brief`), new conversation:**
  - The Trace: `run_skill`, five research agents searching at the same time, one `research_many` line with five short reports.
  - The Context tab: 540 tokens of tool results, 0.4 s.
  - The headline turn: 0 tokens of tool results, 632 tokens of history.
- **On the real model (trainer):** expect the main view at about 1,100 to 1,300 tokens instead of about 10,300, and 17 to 22 seconds. The searches say this month and year, for example "Stanley bottle launch November 2026". Not faster than one agent: each research agent runs its own model calls, and the run is only as fast as the slowest.
- **The headline turn on the real model** gets a plain one-line reply, no picture. The main agent answers with a full poster only when asked for a whole poster.
- **Answer:** `session-02-orchestration-step2`.

| | Step 1 | Step 2 |
| --- | --- | --- |
| Pages in the main agent's view (fake) | 9,915 tokens | none; five reports, 540 tokens |
| Carried into the next turn (fake) | 10,008 tokens | 632 tokens |
| Five searches (fake, 0.4 s each) | one after another, 2.1 s | at the same time, about 0.4 s |
| Main view on the real model | about 10,300 tokens | about 1,100 to 1,300 tokens |

## 6. Ready-made skills to show when there is time

These arrive ready-made in step 3. Each is a short live moment on the real model, in a new conversation, on `session-02-tools-step3` or later.

| Skill + tool | Maya asks | What to point at |
| --- | --- | --- |
| `market_research` + `search_web` | "What are hikers talking about this season?" | Live web results, with the address each trend came from. The search says this year, because the main agent's prompt carries today's date. |
| `ingest_image` + `describe_image` | Attach `samples/shoot/tidal-shoot.jpg`: "Use our shoot photo for the story size." | It checks the photo has no words and no other brand, finds the bottle, crops. No paid picture. |
| `voice_over` + `text_to_speech` | "A 10-second voice-over for the story ad." | A new kind of output: an audio player in the chat, and a file with its own name (`voice-over-xxxx.mp3`). The agent may first ask what the voice-over should say. The clip runs short of 10 seconds, about 6: the skill aims at about 25 words, and the voice reads fast. |

## 7. Troubleshooting

| What you see | Why | Fix |
| --- | --- | --- |
| Setup check: chat model times out, everything else passes | The VPN does not route `llm.keyvalue.systems` (a split-tunnel profile). The LiteLLM page in the browser fails too. | Run `route -n get llm.keyvalue.systems \| grep interface`. If it shows `en0`, not the VPN's interface, IT must add the host to the VPN profile. |
| Red "Cannot reach KeyValue's model proxy (llm.keyvalue.systems). Is the VPN on?" | The VPN is off, or the proxy blinked. | Check the VPN, then send the ask again. |
| Working line: "the model did not answer in 90 s, trying again: 2 of 4" | The proxy did not answer in time. The agent retries up to 3 times by itself. | Wait. If all tries fail, reload the page and send the ask again in a new conversation. |
| Red "Maya's Notion login has ended. To use the Notion board, press Connect Notion, then send the ask again." | Notion refused the saved login. | Press **Connect Notion**, log in, send the ask again. |
| The agent says the card is updated, but Notion shows no change | Notion took the call but changed nothing, or the card text was edited away from the pasted text. | Open the card in Notion. Paste `samples/board/tidal-card-to-paste.txt` again if needed, and send the ask again. |
| Search errors, or no `TAVILY_API_KEY` | The key is missing or used up. | Add the key, or set `LAUNCHKIT_SEARCH=saved` in `.env` to use the saved pages (offline). |
| No Notion account on the day | — | Set `LAUNCHKIT_BOARD=local` in `.env` to use the board server in the repo. |
| Pictures fail with a clear error | The picture GPU is down. | Set `LAUNCHKIT_IMAGE_PROVIDER=litellm` in `.env` (30 to 60 s a picture, paid), restart the page. Set it back to `gpu` when the GPU is up. |
| A change does not show on the chat page | `launchkit ui` does not reload code. | Restart `launchkit ui` after every checkout. |
| `get_brand_details` finds nothing on a fresh clone | The vector database is empty. | `uv run launchkit index` once. |
| "Missing: langgraph" or other Session 1 leftovers | An old checkout or a package added by hand. | `git checkout session-02-tools`, `git pull`, `uv sync`, then the setup check again. |
| The real model answers without loading the skill or searching | The real model does not answer the same way every time. | **New conversation**, send the same ask again. |
| Someone falls behind | — | `git stash`, check out the step's answer branch, restart `launchkit ui`. |
