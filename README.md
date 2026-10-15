# LaunchKit

A marketing assistant built as a harness on [Agno](https://docs.agno.com), one step at a time.
A marketer asks for a poster. LaunchKit answers with the poster's words (the copy) and its picture,
following that brand's rules. Brands are workspaces: a folder of plain files, no code.

## Setup

Needs Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```
git clone <this repo> && cd ai-upskill
uv sync
cp .env.example .env        # add your OPENAI_API_KEY
uv run launchkit check 0    # prints PASS
uv run launchkit ui         # opens the chat page on http://localhost:8000
```

Without a key everything still runs: live runs use a fake model and a fake picture, and say so in the trace.

## Commands

| Command | What it does |
| --- | --- |
| `uv run launchkit run harbor "Poster for the Tidal launch"` | One request in the terminal: trace, spec, picture path |
| `uv run launchkit ui` | The chat page: sign in as a person, chat, live trace, context view, poster |
| `uv run launchkit explain` | What the model saw on the last run, in what order, at what cost |
| `uv run launchkit check 1` | Prove step 1 with fake models. `check all` is the CP1.1 gate |
| `uv run launchkit run harbor "..." --model fake:echo` | Force a fake model for one run |
| `uv run launchkit run harbor "..." --facts workspaces/harbor/brand-book.md` | Load a file into the facts section |
| `uv run launchkit onboard moss samples/harbor-brand-pack.pdf` | Draft a new workspace's files from a brand pack PDF. See `docs/onboarding.md` |

## The build, in four steps

Each step fills one TODO slot in `launchkit/harness/`. Each step has a check. The answer to each step is on its own branch, and each branch contains the previous one's answer.

| Step | Slot | Check | Branch with the answer |
| --- | --- | --- | --- |
| 1 · The agent reads its rules from files | `workspace.py` `load_workspace`, `agent.py` rules section | `check 1` | `session-01-harness-step1` |
| 2 · Check the form, fix it once, then stop | `spec.py` `validate_spec`, `run.py` repair | `check 2` | `session-01-harness-step2` |
| 3 · A tool and a leash | `tools.py`, `limits.py`, `agent.py` picture agent | `check 3` | `session-01-harness-step3` |
| 4 · The request says who you are | `request.py` `resolve_workspace_id` | `check 4` | `session-01-harness-step4` |

Prompt cards for each step are in `docs/`.

## Layout

```
launchkit/
  cli.py            run · ui · explain · check
  settings.py       env, paths, limits, section budgets
  harness/          request → workspace → context → copy agent → validate → picture agent → result
  adapters/         model resolver, fake models, image adapters, prices
  ui/               FastAPI app and one HTML page
workspaces/         one folder per brand: SOUL.md, AGENTS.md, rules.yaml, facts.md, users.yaml, assets/
samples/            a brand pack PDF to try onboarding with
checks/             one pytest file per step; `launchkit check` wraps them
docs/               setup, glossary, one page per step
```
