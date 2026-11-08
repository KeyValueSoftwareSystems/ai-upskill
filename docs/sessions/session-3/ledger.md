# Session 3 · Memory: the prep ledger

Branch `session-3-memory`, cut from `session-02-orchestration-step2`. Agno is pinned to **3.1.3** (`pyproject.toml`: `agno[openai,sqlite]==3.1.3`; installed: `importlib.metadata.version("agno") == "3.1.3"`). Every name below was read from the installed package under `.venv/lib/python3.12/site-packages/agno/`, not from docs.agno.com.

## 1 · Pinned parameter names on 3.1.3

| What | Exact name and signature on 3.1.3 | Where |
| --- | --- | --- |
| Memory after every run | `Agent(update_memory_on_run: bool = False)` | `agent/agent.py:137` |
| Agent-driven memory | `Agent(enable_agentic_memory: bool = False)`; registers a tool named `update_user_memory` | `agent/agent.py:135` |
| Memories into the prompt | `Agent(add_memories_to_context: Optional[bool] = None)` | `agent/agent.py:139` |
| The manager | `Agent(memory_manager: Optional[MemoryManager] = None)` | `agent/agent.py:130` |
| MemoryManager, instruction argument | `MemoryManager(memory_capture_instructions: Optional[str] = None)`; also `system_message: Optional[str]` (full override) and `additional_instructions: Optional[str]` (appended) | `memory/manager.py:78-92` |
| MemoryManager, model argument | `MemoryManager(model: Optional[Union[Model, str]] = None)`; a string goes through `get_model()` | `memory/manager.py:79` |
| MemoryManager, delete and clear flags | `MemoryManager(delete_memories: bool = False, update_memories: bool = True, add_memories: bool = True, clear_memories: bool = False)` | `memory/manager.py:84-87` |
| Summarize entry point | `MemoryManager.optimize_memories(user_id: Optional[str] = None, strategy: Union[MemoryOptimizationStrategyType, MemoryOptimizationStrategy] = MemoryOptimizationStrategyType.SUMMARIZE, apply: bool = True) -> List[UserMemory]`; async twin `aoptimize_memories` | `memory/manager.py:797` |
| The strategy | `agno.memory.strategies.types.MemoryOptimizationStrategyType.SUMMARIZE` (the only member) → `agno.memory.strategies.summarize.SummarizeStrategy` | `memory/strategies/` |
| History runs | `Agent(num_history_runs: Optional[int] = None)`; with neither it nor `num_history_messages` set, Agno uses 3 | `agent/agent.py:163`, `:590` |
| Session summaries | `Agent(enable_session_summaries: bool = False, add_session_summary_to_context: Optional[bool] = None, session_summary_manager: Optional[SessionSummaryManager] = None)`; passing a manager turns summaries on | `agent/agent.py:114-118`, `:561` |
| Learning on an agent | `Agent(learning: Optional[Union[bool, LearningMachine]] = None, add_learnings_to_context: bool = True)` | `agent/agent.py:289-291` |
| Namespace, entity memory | `EntityMemoryConfig(namespace: str = "global")`; `"user"`, `"global"` or any custom string | `learn/config.py:364` |
| Namespace, learned knowledge | `LearnedKnowledgeConfig(namespace: str = "global")` | `learn/config.py:294` |
| Namespace, default for both | `LearningMachine(namespace: str = "global")` | `learn/machine.py` |
| Learning modes | `agno.learn.LearningMode`: `ALWAYS`, `AGENTIC`, `PROPOSE` (learned knowledge only), `HITL` (reserved, unsupported) | `learn/config.py:36` |
| Learned knowledge tools | `save_learning(title, learning, context=None, tags=None)`, `search_learnings(...)`; flags `LearnedKnowledgeConfig(enable_agent_tools=True, agent_can_save=True, agent_can_search=True)` | `learn/stores/learned_knowledge.py:569` |
| Entity memory tools | `remember_about`, `link_entities`, `search_entities`, `forget` (AGENTIC only) | `learn/stores/entity_memory.py:983` |
| Decision log tools | `log_decision`, `record_outcome`, `search_decisions` | `learn/stores/decision_log.py:378` |
| Read for a debug view | `MemoryManager.get_user_memories(user_id)`, `SqliteDb.get_user_memories(user_id=...)` | `memory/manager.py:174` |

### Renamed on 3.1.3, or not what the brief assumed

- **No `source` column on learned knowledge.** A learning holds `title, learning, context, tags, user_id, namespace, agent_id, team_id, created_at, updated_at` (`learn/schemas.py:447`). Worse, `save()` keeps `user_id` only when `namespace == "user"`; a global learning is stored with `user_id = None` (`learn/stores/learned_knowledge.py:926`). So "the learnings that user seeded" can't be found by `user_id`. The fixes record the writer as a tag, `source:<user_id>`, which Agno does keep in the row's metadata.
- **Learned knowledge is not a database table.** It needs a `Knowledge` with a vector store. Its text lives in the vector store (here LanceDB under `data/learnings/`); SQLite's `agno_knowledge` holds only the title and the metadata (namespace, tags). The snapshot is therefore two pieces: `fixtures/memory-snapshot.db` and `fixtures/memory-snapshot-learnings/`.
- **Delete and clear flags default differently on the class and in `__init__`.** The class attributes say `delete_memories = True`, `clear_memories = True`; the constructor defaults are `False`. A manager built with `MemoryManager(...)` cannot delete or clear unless you pass the flags.
- **Summarize is one strategy, and it makes one row.** `SummarizeStrategy` folds every memory of a user into a single summary row and "preserves all factual information" (`memory/strategies/summarize.py`). It removes duplicates; it does not drop a wrong row, a phone number or a token.
- **Entity memory events.** `add_event(content, date=None)` exists on the `EntityMemory` schema (`learn/schemas.py:677`), but the agent's tools are `remember_about`, `link_entities`, `search_entities`, `forget`. A fact carries `created_at`/`updated_at` and a supersession judgement (`supersession_threshold: float = 0.8`); it has no valid-from or valid-to.
- **Propose mode is a prompt, not a gate.** `LearningMode.PROPOSE` adds text to the system message asking the agent to propose a learning at the end of its reply (`learn/stores/learned_knowledge.py:326`). Nothing in code stops a save.
- **The prune-by-age loop and the 500-row alert** are not in the package. `scripts/retention_job.py` writes the loop.
- **Postgres in the problem statement.** LaunchKit's project database is SQLite (`data/sessions.db`, `memory/chat_history.py`). `problem.md` says "the project database".

## 2 · Limits of Agno we hit that a better prompt cannot fix

1. **A custom `system_message` turns off every read path.** When an agent sets `system_message`, Agno returns it as is: no memories, no session summary, no learnings (`agent/_messages.py:942-964`; the memory block is at `:1095`, the summary at `:1136`, learnings at `:1150`, all after that early return). LaunchKit's main agent writes its own system message (`agents/prompt.py`). So "memory on in one line" would have saved rows that were never read back. LaunchKit reads them itself and adds a `# Memory` section (`memory/long_term.py`).
2. **Extraction reads only the user's message.** `make_memories` passes `run_messages.user_message` to the manager (`agent/_managers.py:29-50`), not the reply or the tool results. A competitor page can reach shared knowledge only through a tool such as `save_learning`, never through `update_memory_on_run`.
3. **Learning tools bypass LaunchKit's one door.** A `LearningMachine` on an agent adds its tools to the agent at run time, beside `find_tool`, `run_skill` and `run_tool`, not in `agent.tools`. Session 2's check "the research agent holds only search_web" reads `agent.tools`, so a check written that way misses `save_learning`. It went red at the starting state only because Agno also needs `agent.db` set before it will attach a LearningMachine.
4. **No validity window on any memory row.** User memories have `updated_at`; entity facts have `created_at`/`updated_at` and supersession. None has valid-from or valid-to, so "true today" is LaunchKit's table (ticket 2a).
5. **A global learning forgets who wrote it** (see "No source column" above).
6. **Summarize keeps whatever it is given**, wrong rows and personal data included.
7. **The manager's own prompt keeps old preferences.** `memory_capture_instructions` replaces only the criteria block. The fixed text around it still says "when a user's preferences change, … also capture what the user's preferences used to be" and "append the existing memory with new information rather than completely overwriting it" (`memory/manager.py:1000-1002`). That pulls against "update, do not keep both". Only `system_message=` replaces it, and then the add/update/delete instructions must be rewritten too.
8. **No dry run for extraction.** `create_user_memories` writes through its tools as it goes, so "show the planned rows, then ask" is not possible with Agno's manager. Ticket 2b asks before the note reaches the manager and shows the rows it changed afterwards (Trace).

## 3 · What each fix changed

Every commit on `session-3-memory`, oldest first. "Old" is the code the morning the queue filled (`a52ffb1`). Line counts are lines added; the room builds the slice named in the last column, and the rest comes ready-made.

### Starting state · `a52ffb1` (memory on in one line)

| Old (`session-02-orchestration-step2`) | New: the morning the queue filled |
| --- | --- |
| `Agent(..., db=session_db(settings), add_history_to_context=True, num_history_runs=5)` | adds `update_memory_on_run=True`, `learning=LearningMachine(db, knowledge, learned_knowledge=True, entity_memory=True, decision_log=True)`, every store global |
| research helper: `Agent(system_message=RESEARCH_TASK, tools=[search_web])` | adds `db=session_db(settings)`, `learning=learning_machine(settings)`: `save_learning` in reach |
| prompt sections `rules, task, facts` | adds `memory` (no budget), filled by LaunchKit because Agno skips it (limit 1 below) |
| nothing on the page | a **Memory** tab; the Trace's `memory` lines (`loaded N rows · T tokens`, then `added/updated/deleted: …`) |

Also: Alder workspace (`workspaces/alder/`, no never-say list, `brand.json` beside the usual files), logins for `agency-manager` (Harbor and Alder) and `power-user` (Harbor), `samples/pages/cairnline-1.md` (an invented rival that says "lifetime guarantee"), `launchkit memory reset|show`. Session 2's check `orch2 · the research agent holds only search_web` goes red here and back to green at 2b.

### Ticket 1 · `c9473c7` (36 harness lines; room builds `CAPTURE` and the manager, about 20)

| Old | New |
| --- | --- |
| `update_memory_on_run=True` with Agno's default manager: the main model, default criteria ("name, age, occupation, location, interests…") | `MemoryManager(model=LAUNCHKIT_MEMORY_MODEL (gpt-5-nano), memory_capture_instructions=CAPTURE)` |
| — | `CAPTURE`: one fact per row; preferences only, brand and product facts are not memories; a quoted never-say phrase is a rule ("Never use …"), not a wish; no names, numbers, tokens or pasted text; update before add |
| — | `scripts/consolidate_memories.py <user> [--match navy] [--apply]`: Agno's Summarize, before and after |

On the page: the Trace's memory line names the model that saves.

### Ticket 2a · `0821961` (82 harness lines; room builds `get_brand_facts` and `set_brand_fact`, about 25)

| Old | New |
| --- | --- |
| "Harbor warranty is 2 years." as a user-memory row, `updated_at` 2026-05-12, no end | `brand_facts` table in the project database: `brand, subject, value, scope, source, valid_from, valid_to` |
| — | seeded: `warranty 2 years 2025-01-01 → 2026-03-31`, `warranty 5 years 2026-04-01 → (open)` |
| — | `get_brand_facts(settings, brand, today=None)`: rows true today. `set_brand_fact(...)` closes today's row (ends yesterday), opens a new one |
| `on_brand_copy` uses `get_brand_details, check_copy` | uses `get_brand_details, get_brand_facts, check_copy`; "a fact from get_brand_facts wins over the brand guide and over anything remembered" |

On the page: the Memory tab's first table, every row with "true today". In the catalogue `get_brand_facts` takes no input: the brand is bound from the request, Session 1's rule (the model never names a workspace).

### Ticket 2b · `e0bbcb3` (66 harness lines; room builds `Entry.plan` and the two write entries, about 15)

| Old | New |
| --- | --- |
| research helper with `db` and `learning` | Session 2's helper again: `search_web` only, no store, no LearningMachine |
| main agent: `update_memory_on_run=True`, `learning=…` (9 tools added at run time beside the doors) | `update_memory_on_run=False`, no `learning`; tools are exactly `find_tool, run_skill, run_tool` |
| — | catalogue: `save_memory(note)` **write**, `save_learning(title, learning)` **write**, `search_learnings(query)` read (`tools/save_memory.py`) |
| `run_tool`: `if entry.kind == "write" and not self.approve(name, inputs)` | `planned = entry.plan(inputs) if entry.plan else inputs` … `self.approve(name, planned)`; the same branch, now showing where the write goes and who proposed it |
| a global learning stores `user_id=None` | tagged `source:<user_id>`; every allowed write logged in the decision log |

On the page: Allow / Deny in the chat with `{"store": "learned knowledge", "namespace": …, "source": …}`.

### Ticket 3 · `bf67b89` (74 harness lines; room builds `held_back`, about 20)

| Old | New |
| --- | --- |
| `LearningMachine(...)`, namespace `"global"` | `LearningMachine(..., namespace=ws.id)`: learned knowledge and entity memory per brand |
| every memory row of the person loaded, on every brand | `memory/scope.py`: a row naming any brand's colour, size or never-say phrase, or a `brand_facts` subject, is held back from the prompt |
| a brand fact could be saved as a person's memory | `save_memory`'s plan refuses it in code, before anyone is asked; `propose_brand_fact(subject, value)` **write** shows `from` and `to`, then closes the old row |

On the page: the Trace says `held back N`; the Memory tab has a "not loaded because" column; Allow / Deny for a brand fact.

Snapshot, computed with no model call (`approx_tokens` = characters ÷ 4):

| Person | Rows | Memory section before | After the hold-back |
| --- | --- | --- | --- |
| maya | 39 | 529 tokens | 22 rows, 307 tokens (held: 13 navy or sea glass or sand rows, the inverted rule, the 2-year warranty, the phone row, the token row) |
| agency-manager | 18 | 282 tokens | 13 rows, 204 tokens (held: Harbor colours, sizes, never-say list, and "moss green", an Alder colour) |
| power-user | 600 | 11,318 tokens | 600 rows, 11,318 tokens (nothing brand-shaped) |

Still loaded for the agency manager on Alder, because no rule word is in them: "Headlines up to six words, subheadlines up to twelve.", "Bottle should always be shown whole…", "Audience is weekend hikers and weekday commuters." Code catches the words a brand file lists; it can't catch a Harbor habit phrased in plain words.

### Ticket 4 · `1bdb46a` (62 harness lines; room builds `retain`, about 25)

| Old | New |
| --- | --- |
| `num_history_runs=5`, no summary | `num_history_runs=3`, `session_summary_manager=SessionSummaryManager(model=gpt-5-nano)`; LaunchKit adds the summary to the memory section (Agno skips it, limit 1) |
| — | `scripts/retention_job.py --days N [--summarise-over 100] [--apply]`: prune each person's rows older than N days, Summarize whoever still has more than 100. Dry run by default; cron, never per run |

On the page: the Context tab's third row, "memory and conversation summary in the prompt". Fake runs keep no summary (the fakes are scripted for the conversation only).

Retention dry run on the snapshot, `--days 90`, at the snapshot's morning (no model call):

| Person | Rows | Tokens | Pruned | Left | Tokens left |
| --- | --- | --- | --- | --- | --- |
| power-user | 600 | 10,980 | 285 | 315 | 5,768 (then Summarize: one row; needs the model, step 3) |
| maya | 39 | 472 | 16 | 23 | 282 |
| agency-manager | 18 | 236 | 8 | 10 | 116 |

### Ticket 5 · `3a3c770` (90 harness lines; room builds `delete_user`'s cascade, about 35)

| Old | New |
| --- | --- |
| the phone number and the token sat in Maya's rows and were loaded every turn | `CAPTURE` says never keep them (ticket 1); `scope.py` also holds back a row with a phone number (10+ digits), an email address or a token, and `save_memory` refuses such a note before asking |
| deleting a user's memories left summaries, the decision log and a shared learning | `scripts/delete_user.py <id> [--name …] [--apply]`: memories, sessions and their summaries, decision log and entity rows by `user_id`; shared learnings by `source:<id>`; chat page folders; brand facts kept with the source removed. Prints what it removed and what still names the person |

Offline, on a copy of the snapshot, `agency-manager --name "Dana Whitlock" --apply` removed 18 memories, 2 sessions with summaries, 2 decision-log rows, 0 tagged learnings, 0 folders. Still naming her afterwards: `agno_knowledge: Dana Whitlock's tip: lead every poster with navy` and the same learning's text in LanceDB. It was saved before the fix, with no source, so no key reaches it. That is the room's live answer to "show where she still appears".

## 4 · Measured numbers

Only the offline numbers above so far. Step 3 (three real-model runs per pain, before and after) is not run yet: it spends credits and waits for approval.

## 5 · Outcomes the room may see

Not recorded yet: step 3.

## 6 · Open questions

1. **The warranty timeline contradicts Session 2.** Session 2 (nine months before the queue, in the story) showed "5-year warranty" from `facts.md`, and `on_brand_copy`'s moment depends on it. The problem says it was two years when memory went on, six months ago; the brief says the 2-year row closed in March. Seeded as asked (2 years until 2026-03-31; the memory row dated 2026-05-12). Which dates do you want?
2. **Real competitors in Session 2.** The brief says Session 2 used invented competitors; its guide, card and `samples/pages/` use Hydro Flask, Stanley, Yeti, Owala and Klean Kanteen. Everything new here is invented (Cairnline, Fieldnote Agency, Dana Whitlock, Callum Ferris, Alder). Leave Session 2 as it is?
3. **Harness paths.** The brief names `launchkit/harness/agent.py, run.py, tools.py, limits.py, research.py` and a fake Notion MCP server. On this branch they are `agents/main_agent.py`, `tools/catalogue.py`, `guardrails/limits.py`, `orchestration/research_team.py`, and the offline board `mcp/servers/local_board*.py`. I used the real paths.
4. **`test_orch0` was edited.** It asserted exactly 10 files in `samples/pages/`; the Cairnline page makes 11. The assertion now counts the five Tidal competitors' pages. Or move Cairnline to its own folder?
5. **The 2b live pain needs `LAUNCHKIT_SEARCH=saved`.** Cairnline is invented, so the live web never returns its page.
6. **Never-say rule, two wordings.** The ticket page says "never store a quoted never-say phrase"; the brief says "a quoted never-say phrase is a rule, not a wish". `CAPTURE` follows the brief. From ticket 3 a row naming a phrase from any brand's never-say list is held back anyway.
7. **"The brand owner's yes."** Approval asks whoever is signed in; `users.yaml` has no owner role. Add one (Maya as owner, Sam as intern)?
8. **The film says "all six hundred of Maya's notes"** (`films/session-3-memory-problem/VO_LINES.txt`, s7b). The brief gives Maya about 40 and the power user 600. Change the line or the seed?
9. **Entity memory has no writer after 2b.** Its namespace is per brand, the snapshot's Harbor entity row is still there, but no tool writes it now. Add a gated `remember_about`, or drop entity memory from the session?
10. **Session summaries write without asking.** I treated them as conversation state, not memory. Agree?
11. **`launchkit memory reset` replaces `data/sessions.db`**, which also holds Session 2's chat history (kept as `sessions.db.bak`). Restart `launchkit ui` after a reset.
12. **Is `gpt-5-nano` on the proxy?** It is the memory and summary model by default (`LAUNCHKIT_MEMORY_MODEL`). First thing step 3 checks.
13. **Fix sizes.** Every ticket's harness change is 36 to 90 lines, over your 30; the room-built slices named above are 15 to 35.
