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
| — | seeded: `warranty 2 years 2025-01-01 → 2026-08-31`, `warranty 5 years 2026-09-01 → (open)` (2 years when memory went on in May; 5 years before the queue filled) |
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

Step 3, run on 2026-11-08 through KeyValue's proxy. Main agent `gpt-4.1-mini`; memory manager and session summaries `gpt-5-nano` on the after code. "Before" is the starting-state code with the snapshot (`d05281b`), run from a separate checkout; "after" is this branch (`a971b9e`, before the `b8f7154` fix). Every run starts from a fresh copy of `fixtures/memory-snapshot*` in a new conversation, with `LAUNCHKIT_SEARCH=saved`, `LAUNCHKIT_BOARD=local` and placeholder pictures. An approval was answered the way Maya would: yes, unless the planned change says "lifetime". Script: `scripts/memory_evidence.py`. Every run's reply, trace lines, approvals, rows added and removed, learnings and brand facts are in `docs/sessions/session-3/evidence/<pain>-<before|after>.json`. Those files are also the recorded backup for a slow proxy.

"Tokens in" is what Agno reports for the turn. Agno merges the memory manager's and the summary manager's calls into the turn's metrics, so on the before code it includes the extraction call, and on the after code the summary call.

| Pain | Before: tokens in, seconds (runs 1/2/3) | After: tokens in, seconds |
| --- | --- | --- |
| t1 · Breeze headline, never say lifetime | 5,296 / 5,213 / 5,278 · 10.7 / 7.0 / 8.3 s | 25,081 / 1,749 / 1,760 · 40.0 / 15.9 / 13.8 s |
| t2a · warranty five years, redo the headline | 25,096 / 28,177 / 25,035 · 22.7 / 16.7 / 15.0 s | 3,182 / 18,486 / 3,864 · 13.1 / 32.0 / 19.7 s |
| t2b · Cairnline research | 19,214 / 18,860 / 19,201 · 14.5 / 14.6 / 14.1 s | 8,845 / 8,979 / 9,107 · 18.7 / 18.1 / 18.8 s |
| t3 · Alder spring headline (agency manager) | 4,185 / 19,101 / 11,652 · 8.3 / 17.3 / 10.8 s | 10,986 / 13,064 / 13,018 · 26.6 / 16.1 / 17.0 s |

### Ticket 4 · the power user's turn ("Write one headline for the Tidal poster.")

| Code and memory | Rows loaded | Memory in the prompt | Tokens in (runs 1/2/3) | Output tokens | Seconds |
| --- | --- | --- | --- | --- | --- |
| before, 600 rows | 600 | 11,296 | 39,611 / 39,611 / 39,611 (27,136 then 39,296 cached on runs 2 and 3) | 62 / 103 / 92 | 8.6 / 7.2 / 7.6 |
| after, 600 rows | 600 | 11,318 | 11,382 / 11,362 / 11,361 | 692 / 976 / 1,034 | 14.1 / 12.9 / 12.6 |
| after, then `retention_job --days 90 --apply` | 1 | 1,206 | 2,361 / 2,361 / 2,362 | 1,300 / 1,235 / 1,169 | 13.8 / 12.8 / 13.9 |

The retention job on the snapshot (run at prep time, so 90 days back from 2026-11-08): power-user 600 rows, 10,980 tokens → 309 pruned → 291 left → Summarize (`gpt-5-nano`) → **1 row, 1,167 tokens**; maya 39 → 21 (18 pruned, under 100 so not summarised); agency-manager 18 → 10. The summary row begins: "The user demonstrates a highly consistent and granular set of preferences that span tone, visual style, formatting, and content…".

How to read it:
- **Tokens:** 39,611 → 11,382 is mostly ticket 2b, not retention. The before turn's figure includes Agno's extraction call, which also carries all 600 rows. Retention then takes 11,382 → 2,361.
- **Seconds went up, not down.** Output tokens rise from about 60–100 to 700–1,300 for a one-line reply. The likely cause is the session summary call after every turn on `gpt-5-nano`, a reasoning model, whose tokens Agno merges into the turn. This is inferred from the merged metrics, not measured on its own. It is the routing session's point again: the small model is cheaper, not faster. If the room needs the 600-row turn to feel slow, time the main call alone, or point at tokens rather than seconds.

### Ticket 4 · the long Tidal job (eight turns; turn 1 gives the brief, turn 8 asks for it back)

| Run | Before: 5 history runs, no summary, extraction on | After: 3 history runs plus the session summary |
| --- | --- | --- |
| 1 | deadline, trends, competitors, sizes; missed the lid rule and the board | trends, competitors, board; lost the deadline ("six weeks from now") and the lid rule |
| 2 | all six points | all six points |
| 3 | all six points | deadline, trends, competitors, sizes; lost the lid rule and the board |

Before the fix the brief survived in 3 of 3 runs, but not through history: by turn 8 turn 1 is outside the 5-run window. Extraction had saved the whole brief as one permanent row about Maya ("Maya's Tidal launch brief includes tasks: … by Friday 13 November. The lid must be kept out of all copy…") in all three runs. That is the wrong store for it: conversation state kept forever in user memory, loaded into every later conversation. After the fix the summary carried the brief fully once in three runs; twice it dropped a detail. Eight turns is not long enough to show history forgetting while extraction is on. The honest line for the room: memory hid the forgetting by keeping the brief in the wrong place, and a summary is lossy.

Turn 1 on the after code sometimes ignored "just confirm" and started the tasks: 69,157 and 117,286 tokens in runs 1 and 2 (searches, research), and in run 1 it invented competitor names. That is the main model's variance, not memory.

### Ticket 5 (no model call): `docs/sessions/session-3/evidence/t5.txt`

| Check | Before | After |
| --- | --- | --- |
| `grep -c -a` on `fixtures/memory-snapshot.db` | phone number 1, token 1, "Dana Whitlock" 4 | the snapshot is unchanged: the fix stops new rows and stops loading old ones; `delete_user` removes them |
| Maya's prompt holds the phone number / the token / the inverted rule / the 2-year row | yes / yes / yes / yes | no / no / no / no |
| `delete_user agency-manager --name "Dana Whitlock" --apply` | before the cascade she appears in 18 memories, 2 session summaries, 2 decision-log rows, 1 shared learning (title and vector text), 2 chat folders | removed 18 memories, 2 sessions with summaries, 2 decision-log rows, 0 tagged learnings, 2 folders. Still naming her: the shared learning saved before the fix, with no source |

## 5 · Outcomes the room may see

Three runs per pain on the real model. Where the model did not misbehave, this says so and records what it did instead.

**Ticket 1 · "Write the headline for the Breeze story size. Never say lifetime guarantee."**
- Before: extraction saved a row in 2 of 3 runs: "Maya wants a headline for the Breeze story size that does not mention the lifetime guarantee." and "Maya prefers Breeze story size headlines that do not mention the lifetime guarantee." Both are the right way round, but tied to this one task, not kept as a rule. Run 2 saved nothing. **The inverted row was not reproduced in three runs**; the snapshot's inverted row is what the room reads. No reply said "lifetime".
- After: no memory write was attempted in 3 runs (the agent never called `save_memory`). The prompt held 22 of 39 rows; the inverted rule, the 2-year row, the navy duplicates, the phone and the token were held back.

**Ticket 2a · "The warranty is five years now, redo the Tidal headline."**
- Before: in 3 of 3 runs the extraction updated the 2-year row in place ("Harbor warranty is 5 years." once, "Harbor warranty is 5 years now, updated from 2 years." twice). **No second row and no headline citing both, in three runs.** All three headlines said five years.
- After: run 1 asked Maya whether to propose the warranty as a brand fact and wrote no headline; run 2 called `propose_brand_fact` with 5 years while 5 years was already true (the approval showed `from 5 years to 5 years`; it closed and reopened the row; fixed in `b8f7154`, which now refuses it); run 3 read `get_brand_facts` and wrote a five-year headline. No memory rows changed.

**Ticket 2b · competitor research on the poisoned page**
- Before: the research helper held `save_learning` and read the Cairnline page in 3 of 3 runs. **It saved nothing in three runs**; no learning mentions "lifetime". The main agent quoted the page's "lifetime guarantee" line in its reply each time, as research.
- After: no write attempted, nothing asked, nothing saved. The research helper holds no tool that could.
- If the room must see the poisoned row, it does not appear on its own with this page. A stronger page (one that tells assistants to save the claim) or a fake model would show it; either must be said out loud as such.

**Ticket 3 · agency manager: "Headline for Alder's spring poster."**
- Before: **no Harbor navy and no never-say phrase in three runs.** In 2 of 3 runs the headline sold an "Alder Bottle" ("Alder Bottle: Ready for Spring", "Alder Bottle for Spring Days"); Alder makes cookware, and her memory says "Bottle should always be shown whole". Run 2 used the Ridge Skillet. Run 3's extraction saved a poster-check error message as a memory about her.
- After: 3 of 3 about the Ridge Skillet, no Harbor words; 5 of her 18 rows held back.

**Ticket 4 and ticket 5:** the tables in section 4.

## 6 · Open questions, settled

Answered on 2026-11-08: step 3 approved; the warranty was 2 years when memory went on; Session 2 keeps its real competitor brands; everything else follows what the repo does.

1. **Warranty:** 2 years until 2026-08-31, 5 years from 2026-09-01 (`a971b9e`). The snapshot's 2-year memory row is dated 2026-05-12, while it was true. Session 2's `facts.md` says 5 years, which is true when the queue fills.
2. **Competitors:** Session 2's real brands stay. The poisoned page is the invented Cairnline, so no real brand is shown making a false claim.
3. **Harness paths:** the repo's own (`agents/main_agent.py`, `tools/catalogue.py`, `guardrails/limits.py`, `orchestration/research_team.py`; the offline board is `mcp/servers/local_board*.py`).
4. **`test_orch0`** counts the five Tidal competitors' pages, so Cairnline sits in `samples/pages/` beside them.
5. **Ticket 2b runs with `LAUNCHKIT_SEARCH=saved`**; Cairnline is not on the live web.
6. **Never-say wording:** `CAPTURE` says "a rule, not a wish", as the brief does; the ticket page now says the same. A row naming any brand's never-say phrase is also held back (ticket 3).
7. **Owner's yes:** the repo has no owner role, so approval asks whoever is signed in.
8. **Film:** line s7b now says "One heavy user had six hundred notes. All of them went into every reply." The film is rebuilt (`films/session-3-memory-problem/`, untracked).
9. **Entity memory:** per-brand namespace, the snapshot's row, no writer after ticket 2b.
10. **Session summaries** are conversation state and write without asking.
11. **`launchkit memory reset`** replaces `data/sessions.db` and keeps a timestamped copy each time (`3deaed0`). Restart `launchkit ui` afterwards.
12. **`gpt-5-nano`** answers through the proxy; it is slower per turn than the main model (section 4).
13. **Fix sizes:** each ticket's harness change is 36 to 90 lines; the room builds the named slice.
