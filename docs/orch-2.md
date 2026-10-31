# Checkpoint 2 · Hand the digging to subagents (CP2.2b)

Same task, same pages. This time the main agent does not read them. A subagent does.

A subagent is an agent another agent calls like a tool. It works in its own view and hands back only the answer. Ours is a research agent: it gets one brief, searches, reads, and replies with a short report. It holds `search_web` and nothing else: no board, no `run_tool`, and none of Maya's chat.

The five competitors do not depend on each other, so five research agents can run at the same time. Whoever splits the work, writes the briefs, sends them out and gathers the answers is the orchestrator. Here it is the main agent, following the skill.

## The slot

- `launchkit/harness/agent.py` · `build_research_agent`. Today it returns None.
- `launchkit/harness/research.py` · `make_research_entries`. Today it returns no tools.
- `launchkit/skills/competitor_research/skill.md`. Today it tells the main agent to search itself.

## Break it first

Run checkpoint 1's command and keep the last line:

```
LAUNCHKIT_SEARCH_DELAY=0.4 uv run launchkit main harbor "How are Hydro Flask, Stanley, Yeti, Owala and Klean Kanteen launching bottles this season? One paragraph each." --model fake:brief --session cp2
```

```
main agent's view  9858 tokens of tool results this turn · 0 tokens of history carried in · took 2.1 s
```

## Prompt card, for your coding agent

Two parts, one after the other: the subagent first, then side by side. Run the check after both.

```
Part 1, the subagent. In launchkit/harness/agent.py, build_research_agent(model, settings, trace)
returns an Agno Agent with system_message=RESEARCH_TASK (already written), tools=[make_search_web(settings)]
from launchkit/harness/web.py, the same leash hook as build_picture_agent, and telemetry=False.
No db and no history: it sees only its brief.

In launchkit/harness/research.py, make_research_entries(model, settings, trace) returns one Entry:
"research", kind "read", note "hand one research question to a research agent; get back a short
report, not the pages". Its function research(brief: str) -> str builds the research agent, runs it
on the brief, calls raise_if_failed(run), records trace.model("research", model_name(model), run.metrics)
and returns the report text.
```

```
Part 2, side by side. In the same file add research_many(briefs: list[str]) -> list[str]: run
research on every brief at the same time with a ThreadPoolExecutor and return the reports in the
order of the briefs. Add it as a second Entry, kind "read", note "hand several independent research
questions to research agents that run at the same time; get back one short report each, in order".

In launchkit/skills/competitor_research/skill.md, change step 2: call run_tool once with name
"research_many" and inputs {"briefs": [...]}, one brief per competitor. Each brief stands alone,
because the research agent sees nothing else: ask for the message, the channels and what to avoid
copying, and list our never-say claims in it.
```

## Prove it

```
uv run launchkit check orch2
```

- The research agent holds `search_web` and nothing else, with no session store and no chat history.
- `research` and `research_many` go into the catalogue as ordinary read tools.
- The research agent sees its brief and its pages, never Maya's chat.
- The pages stay in the research agents' views. The main agent gets five short reports, and the next turn carries no pages.
- Five research agents run at once: with a search that takes 0.4 s, the whole job takes about one search, not five.
- `research_many` hands back one report per brief, in the order the briefs were given.

Then the gate for the whole part: `uv run launchkit check orch`.

## Run it again

On the chat page, started with `LAUNCHKIT_SEARCH_DELAY=0.4` as in checkpoint 1: press **New conversation**, keep `fake:brief` in **Model** and send the same ask. The Trace tab shows:

```
  tool      run_skill("competitor_research") → # competitor_research Pick me when: the job is to find out … · 223 tokens back
  tool      search_web("How is Hydro Flask launching bottles this season? Message,…) → # Role Model and Hydro Flask Launch Limited Edition Drinkwa… · 1977 tokens back
  model     research phase · fake:brief · sent 2179 tokens, got back 23
  ...four more research agents, at the same time...
  tool      research_many(['How is Hydro Flask launching bottles this season? Message…) → ['Hydro Flask: launch line, channels and what to avoid copy… · 121 tokens back
```

The Context tab: 514 tokens of tool results, 0 of history carried in, 0.4 s.

And Maya's next ask in the same conversation, "Write one headline for the hiker concept.": 0 tokens of tool results, 660 tokens of history carried in.

| | Checkpoint 1 | Checkpoint 2 |
| --- | --- | --- |
| Pages in the main agent's view | about 9,900 tokens | none; five reports |
| Carried into the next turn | 10,005 tokens | 660 tokens |
| Five searches | one after another, 2.1 s | at the same time, 0.5 s |

## Why it matters

A subagent changes what the main agent sees. The noisy digging happens somewhere else and only the answer comes back. Independent pieces run side by side. And the agent that reads the web holds no tool that writes.

It is not free. Count the model calls in the trace: six instead of one. Each research agent sees only its brief, so anything the brief leaves out (the never-say list, Maya's chat) it does not know.

## See it

The trainer runs the same ask on the real model: leave **Model** empty. On 30 Oct, gpt-4.1-mini with live web search, 2 runs: the main agent's view held 1,163 to 1,333 tokens instead of about 10,300, and the next turn carried 1,522 tokens of history. 17 to 22 seconds: the parallel run is only as fast as its slowest research agent.

## Stuck?

The answer is on the branch `session-02-orchestration-step2`.
