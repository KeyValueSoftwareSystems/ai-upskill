# What Session 3 builds

By the end of the session LaunchKit has 17 tools of its own (Session 2's 12 and five new), 7 skills, 1 MCP server (Notion's), two agents, two model helpers and seven stores. Session 2's catalogue is unchanged; the new rows are marked **new**. This is the trainer's answer key.

## Tools

One action each. A read runs; a paid tool spends from the leash budget; an outside write or a memory write asks first, through `run_tool`.

| Tool | Kind | Read / write | Comes in |
| --- | --- | --- | --- |
| get_brand_details | Plain code (search) | Read | Session 1 |
| generate_image | Model, paid | Paid: budget leash | Session 1 |
| detect_focal_point | Model (vision), once per poster | Read | Session 2, step 1 |
| crop | Plain code | Read | Session 2, step 1 |
| expand_canvas | Plain code | Read | Session 2, step 1 |
| scale | Plain code (hidden by resize_image) | Read | Session 2, step 1 |
| check_copy | Plain code | Read | Session 2, step 2 |
| search_web | Connector | Read | Session 2, step 3 |
| describe_image | Model (vision) | Read | Session 2, step 3 |
| text_to_speech | Model (audio), paid | Paid: budget leash | Session 2, step 3 |
| research(brief) | Runs one research subagent | Read | Session 2, step 9 |
| research_many(briefs) | Runs one research subagent per brief, at once | Read | Session 2, step 9 |
| **get_brand_facts** | Plain code (a table): this brand's facts true today | Read | Ticket 2a |
| **save_memory(note)** | Model helper (memory manager, cheaper model) | **Write: asks first** | Ticket 2b |
| **save_learning(title, learning)** | Plain code into learned knowledge, brand namespace, tagged with its source | **Write: asks first** | Ticket 2b |
| **search_learnings(query)** | Plain code (vector search), brand namespace | Read | Ticket 2b |
| **propose_brand_fact(subject, value)** | Plain code: closes today's row, opens a new one | **Write: asks first** | Ticket 3 |

## Skills

How-to files in `launchkit/skills/<name>/skill.md`.

| Skill | Uses | Comes in | Hides (prefer_over) |
| --- | --- | --- | --- |
| resize_image | detect_focal_point, crop, expand_canvas | Session 2, step 2 | the raw picture tools, scale too |
| on_brand_copy | get_brand_details, **get_brand_facts** (ticket 2a), check_copy | Session 2, step 2 | — |
| market_research | search_web | Session 2, step 3 | search_web |
| ingest_image | describe_image, detect_focal_point, crop, expand_canvas | Session 2, step 3 | — |
| voice_over | text_to_speech, check_copy | Session 2, step 3 | text_to_speech |
| post_to_board | Notion MCP tools | Session 2, step 4 | — |
| competitor_research | research_many | Session 2, step 7 | — |

## MCP server

Notion's hosted server, with each person's own login: notion-search, notion-fetch and notion-get-comments (read), notion-update-page, notion-create-comment and notion-delete-pages (write). Offline and on the fake model, a local board stands in: read_card (read), attach_files, update_status and remove_files (write). Unchanged.

## The agents and the model helpers

| Agent | In this session | Why |
| --- | --- | --- |
| Main agent | Same doors, checks and sessions. Its prompt gains a `# Memory` section that LaunchKit fills: the person's rows minus the held-back ones, and the conversation summary. It keeps 3 turns word for word (was 5). It writes no memory on its own: no `update_memory_on_run`, no learning tools beside the doors | Agno skips memory when an agent writes its own system message; every write goes through one door |
| Research subagent ×5 | Back to Session 2's: search_web only, no store, no learnings | The agent that reads the web holds no tool that writes |
| Onboarding agent | Unchanged | Runs once per brand, outside Maya's chat |
| **Memory manager** (model helper, not an agent) | Agno's `MemoryManager` with `CAPTURE` and `LAUNCHKIT_MEMORY_MODEL` (gpt-5-nano). Runs only inside an allowed `save_memory` | It only sorts one note into rows |
| **Session summary manager** (model helper) | Agno's `SessionSummaryManager` on the same cheaper model, after each turn | Keeps the brief when old turns leave the view |

## Stores

All in the project database, `data/sessions.db`, except the two vector folders. No second memory system.

| Store | Holds | Scope | Written by | Comes in |
| --- | --- | --- | --- | --- |
| Sessions (`agno_sessions`) | each conversation's runs, **and its summary** | one conversation | Agno, every turn | Session 1 (summary: ticket 4) |
| User memories (`agno_memories`) | facts about one person, one per row | user_id, across brands | save_memory, after a yes | Session 3 start |
| Learned knowledge (`data/learnings/` + `agno_knowledge`) | learnings for a team, tagged `source:<user_id>` | the brand's namespace | save_learning, after a yes | Session 3 start (namespace: ticket 3) |
| Entity memory (`agno_learnings`) | facts about companies, products | the brand's namespace | nothing after ticket 2b (snapshot rows only) | Session 3 start |
| Decision log (`agno_learnings`) | every allowed memory write: who allowed what | user_id | the memory tools | Session 3 start (audit: ticket 2b) |
| **Brand facts** (`brand_facts`) | dated brand facts: subject, value, scope, source, valid_from, valid_to | brand | propose_brand_fact, after a yes | Ticket 2a |
| Brand store (`data/brand-store/`) | brand book chunks for get_brand_details | brand | `launchkit index` | Session 1 |

## Scripts (prep and operations, never run by the agent)

| Script | What it does | Ticket |
| --- | --- | --- |
| `scripts/seed_memory_snapshot.py` | builds `fixtures/memory-snapshot.db` and `fixtures/memory-snapshot-learnings/` | prep |
| `uv run launchkit memory reset` / `show --user <id>` | puts the snapshot in place / prints what is stored | prep, all |
| `scripts/consolidate_memories.py <user> [--match] [--apply]` | Agno's Summarize on one person's rows, before and after | 1 |
| `scripts/retention_job.py --days N [--apply]` | prune by age, Summarize the rest; scheduled | 4 |
| `scripts/delete_user.py <id> [--name] [--apply]` | the cascade, and what still names them | 5 |
| `scripts/memory_evidence.py <pain> --label …` | prep: runs a live pain three times from the snapshot and saves every outcome to `docs/sessions/session-3/evidence/` | prep |

## The code at the end

New since `session-02-orchestration-step2`:

```
launchkit/
  knowledge/brand_facts.py      ticket 2a: the dated brand facts table and get_brand_facts
  memory/long_term.py           memory on: the learnings store, the capture rules, the cheaper model, the summary
  memory/memory_view.py         the Memory tab, and the snapshot reset
  memory/scope.py               tickets 3 and 5: what is never a memory about a person
  memory/retention.py           ticket 4: prune by age, then Summarize
  memory/forget.py              ticket 5: the delete cascade and what still names them
  tools/save_memory.py          ticket 2b: save_memory, save_learning, search_learnings, propose_brand_fact
workspaces/alder/               the agency's second brand: no never-say list
fixtures/                       the snapshot the room starts from
samples/pages/cairnline-1.md    an invented rival that says "lifetime guarantee"
checks/test_mem1.py … test_mem5.py   `uv run launchkit check mem`
```
