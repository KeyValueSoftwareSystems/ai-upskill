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

## 3 · What each fix changed

_Filled in as each commit lands._

## 4 · Measured numbers

_Step 3. Not run yet: it spends real model credits and waits for approval._

## 5 · Outcomes the room may see

_Step 3._

## 6 · Open questions

_Collected at the end of step 2._
