# Memory ticket 2b · Who may write

> "…and it says lifetime, which we never say."

The warranty ticket has a second cause. Memory writes happen in three places, and none of them asks anyone:
- the main agent's memory manager, after every turn (`update_memory_on_run=True`);
- the main agent's learning tools (`save_learning`, `remember_about`, `log_decision` and others), which Agno adds beside the three doors at run time, so they never pass through `run_tool`;
- the research helper, which reads competitor pages and was given the same learning tools.

A competitor's page says "lifetime guarantee". Learned knowledge is shared with everyone by design.

This is Session 2's question, "ask every time, or remember a yes?", coming back as a bill.

## The slot

- `launchkit/tools/catalogue.py` · `run_tool`: ask with the planned change, not the raw inputs.
- `launchkit/orchestration/research_team.py` · `build_research_agent`: no store, no learning.
- `launchkit/agents/main_agent.py`: no write after every run, no learning tools; the memory doors go in the catalogue; one line in the task.

Ready-made in `launchkit/tools/save_memory.py`: `memory_entries` returns `save_memory`, `save_learning` and `propose_brand_fact` (all kind write, each with a `plan`), `search_learnings` (read), and logs every allowed write in the decision log. `Entry` already has an optional `plan` field.

## Break it first

Cairnline is an invented rival, not on the live web, so start the page on the saved pages:

```
uv run launchkit memory reset
LAUNCHKIT_SEARCH=saved uv run launchkit ui
```

As **Maya at Harbor**, in a new conversation:

> How is Cairnline launching its Summit bottle this season? One paragraph: message, channels, what to avoid copying.

The Trace shows `competitor_research`, then `research_many`. The research helper reads the Cairnline page, "lifetime guarantee" and all. In prep it held `save_learning` in 3 runs and **never used it**; no learning mentioning lifetime was saved. The reply quoted the line each time, as research. The point is not that it wrote; it is that nothing would have stopped it, and nobody would have been asked.

Then, in the terminal:

```
uv run launchkit check orch2
```

Session 2's check is red: "the research agent holds only search_web" fails, because the helper now has a store. Its tool list still says `search_web`: Agno adds learning tools at run time, not to `agent.tools`.

## Prompt card, for your coding agent

```
Part 1, one door. In launchkit/tools/catalogue.py, run_tool: before the write check, work out
planned = entry.plan(inputs) if entry.plan else inputs. If planned is a str, it is a refusal: record
self.trace.refused(name, planned) and return it without asking. Then ask with planned instead of
inputs: if entry.kind == "write" and not self.approve(name, planned): ... as before.

Part 2, no other writer. In launchkit/orchestration/research_team.py, build_research_agent: remove
db= and learning=; the research agent is Session 2's again, search_web only. In
launchkit/agents/main_agent.py, build_main_agent: set update_memory_on_run=False and remove the
memory_manager= and learning= arguments. In build_catalogue, add
*memory_entries(settings, lambda: memory_manager(settings, trace, model), user, namespace=ws.id)
to the entries (memory_entries is in launchkit/tools/save_memory.py). In MAIN_TASK, before the last
line, add: When the marketer tells you how they like to work and it will matter in a later
conversation, call run_tool("save_memory", {"note": "..."}); a new value for a brand fact, such as the
warranty, goes to propose_brand_fact. Every memory write asks the marketer first.
```

## Prove it

```
uv run launchkit check mem2b
uv run launchkit check orch2
```

- The research helper holds no memory and no learning tools; Session 2's orch2 check is green again.
- The main agent writes nothing on its own: its tools are exactly `find_tool`, `run_skill`, `run_tool`.
- Memory writes are write tools: they ask.
- A learning asks first with the planned change, and a no saves nothing.
- An allowed learning carries its source (`source:maya`) and is logged.
- A brand fact is refused as a memory before anyone is asked.
- A proposed brand fact is shared only after a yes; proposing the value already true changes nothing.

## Run it again

Restart the page (still with `LAUNCHKIT_SEARCH=saved`). Same ask, new conversation: no write anywhere in the Trace. Then:

> Save that as a learning for the team.

When the agent calls `save_learning`, the chat asks, with exactly where it would go:

```
The agent wants to save_learning
{ "store": "learned knowledge", "namespace": "harbor", "source": "maya", "title": "...", "learning": "..." }
[ Allow ] [ Deny ]
```

Press **Deny**. Then:

> Remember: never say lifetime guarantee.

If the agent calls `save_memory`, the Trace shows `refused save_memory: Not saved: a brand fact ("lifetime guarantee")…` and nobody is asked: it is Harbor's rule, and Harbor's files already hold it. And:

> The warranty is seven years from today, update it.

When the agent calls `propose_brand_fact`, the chat asks with `"from": "5 years", "to": "7 years"`. After **Allow**, the Memory tab shows the 5-year row closed yesterday and a 7-year row from today. Reset afterwards.

## Why it matters

Every memory write now goes through the one door Session 2 built for outside writes. The rule is in code, so the model cannot talk its way past it, whatever a page tells it. Agno's propose mode is a prompt asking the agent to propose; it is not a gate. And the agent that reads the web holds no tool that writes.

The price is a question every time something is saved. "Remember a yes" would need its own rule, and its own place to be written down.

## Stuck?

The answer is on the branch `session-3-memory`.
