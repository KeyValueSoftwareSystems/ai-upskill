# Session 2 pre-read: Tools, Agents & Orchestration

Designing Agentic Systems · Session 2 pre-read · Oct 30, 2026

## How to use this pre-read

This covers four topics the session builds on: tools, skills, MCP, and subagents. It also shows where the session sits in the upskill plan, and walks through the practice repo so the hands-on starts fast.

- **If you're newer to this:** read every *Start here* block in order, open one link per topic, then *Go deeper*.
- **If you already build with agents:** skim *Start here* for the terms we'll use, read every *Go deeper* block.

Before the session: do the setup in the repo section below. It takes ten minutes.

## Where this session sits

Session 2 is day 2 of the upskill. Day 1 built the harness: the code around the model. Day 2 gives that harness hands: tools, skills and outside services, and then a team of agents.

| Day | Topics | When |
| --- | --- | --- |
| Day 1 | Harness / scaffold engineering: LLM calls, LangGraph, the agent harness, RAG | Done, 27th Oct |
| **Day 2 (this one)** | Tool use, MCP & context · Multi-agent systems & orchestration | 3rd Nov |
| Day 3 | Frontier models, reasoning & model-agnostic architecture · Agent memory architecture | 10th Nov |

Later in the plan, order still to be set: generative media; agent runtime, sandboxing & secure tool execution; agent evaluation; observability & tracing; agent security & red teaming; self-improving agents; durable & long-running agents; productionizing agents (the capstone).

Day 2 continues in the same practice repo as day 1: the harness you built is where today starts.

## The practice repo in five minutes

The hands-on uses **LaunchKit**, a small marketing agent in Python on [Agno](https://docs.agno.com). It is the same repo as Session 1: [ai-upskill](https://github.com/KeyValueSoftwareSystems/ai-upskill).

**Setup.** Set up for Session 1 already? Do not clone again. Open a terminal in the folder you used then, and run:

```
git fetch origin && git checkout session-02-tools
uv sync
uv run launchkit check setup
```

New to the repo? Clone [the repo](https://github.com/KeyValueSoftwareSystems/ai-upskill), copy `.env.example` to `.env`, add your `LITELLM_API_KEY`, then run the same three lines in the new folder.

**Branches.** Part 1 starts on `session-02-tools`, part 2 on `session-02-orchestration`. Each step has an answer branch; if you fall behind, check out the next one.

**What is in the repo after Session 1.** Only the files today builds on.

| File | What it is |
| --- | --- |
| `workspaces/harbor/` | The brand: voice, rules, colours, ad sizes, brand book |
| `launchkit/harness/main.py` | The main agent. It has 2 tools now; every new tool joins here |
| `launchkit/harness/catalogue.py` | The tool list: each tool has a "pick me when" note and a read or write flag |
| `launchkit/harness/tools.py`, `brand.py` | Day 1's 2 tools: make the picture, search the brand book |
| `launchkit/harness/context.py` | Builds the prompt inside a token budget |
| `launchkit/harness/limits.py`, `trace.py` | The step and cost limits, and the record of every call |
| `launchkit/skills/` | Empty. Skills go here |
| `checks/`, `docs/` | One test file and one card per step |

Two commands you will use all day: `uv run launchkit main harbor "<ask>"` talks to the main agent and prints its trace; `uv run launchkit explain harbor` shows what the model saw on the last turn, and what it cost.

## 1. Tools: how a model calls your code

A tool is a function the model may ask for. The model never runs code itself: it replies with a request, and the harness runs it.

### Start here

- **The round trip.** The model replies with a call (a tool name and its inputs) instead of text. The harness runs the function and sends the result back as a message. Then the model is called again. So one tool use costs two model calls.
- **What the model sees.** Only three things: the tool's name, its inputs (a schema), and its description. Frameworks build them from the function's name, type hints and docstring. The description is the only thing the model has to choose by.
- **Results are context.** Everything a tool returns lands in the model's view, and is paid for again on every later turn of that conversation.
- **Errors are results too.** Wrong inputs or an unknown tool name should come back as a clear message, not a crash. The model reads it and tries again.
- **Read vs write.** Some tools only look (read a card, search the web). Some change the world (post, delete, pay). They need different rules.

### Go deeper

- **Small tools vs one big tool.** Splitting one tool into several small ones gives the model more ways to do the job, and more ways to do it wrong. Which tool, in what order, and when to stop is not in any tool.
- **Tool lookup.** Every tool definition rides along on every turn, used or not. With many tools, give the agent a search tool instead: each tool carries a short "pick me when" note, and only the best few come back. The cost is one extra call per job.
- **One door.** Route every tool call through one function. Input checks, budgets, the trace and permissions then live in one place, instead of in every tool.
- **Permissions in code.** A write that needs a person's yes is enforced by the harness, not asked for in the prompt. The model cannot skip a rule it does not control.
- **Parallel calls.** A model can ask for several tools in one reply; the harness runs them all and sends every result back together.
- **Tool output is data, not orders.** A web page or a card can contain text that reads like an instruction. The model may follow it. Keep the rules that matter in code.

**Question to hold:** if every tool works, why can the agent still do the job wrong?

### Read further

- [Anthropic: Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents). How to name, describe and size tools so a model picks them right.
- [Claude docs: Tool use overview](https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview). The round trip, step by step, with the request and response shapes.
- [OpenAI: Function calling](https://platform.openai.com/docs/guides/function-calling). The same idea from another provider, including parallel calls.
- [Anthropic: Advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use). Tool search for large catalogues, and why it saves tokens.
- [Agno: Tools](https://docs.agno.com/tools/introduction). How the framework in the repo turns a Python function into a tool.

## 2. Skills: know-how in a file

Tools know how to act. They do not know which one to use, in what order, or when the result is good enough. A skill is that know-how, written down in plain words, in a file the agent reads only when it needs it.

### Start here

- **What a skill is.** A folder with a `SKILL.md` (in the repo: `skill.md`) file: a short "pick me when" line, the tools it uses, and numbered steps. Plain words, no code. The brand team can read it and change it.
- **Loaded on demand.** The prompt lists each skill in one line. When a job fits, the agent loads the whole file for that job only. Everything else stays out of the prompt.
- **Skill vs tool.** A tool does one thing. A skill is a recipe that uses tools: which ones, in what order, what to do in each case, and how to check the result.
- **Skill vs prompt.** Rules for every job in one big prompt are paid for on every turn and crowd each other out. Moving a job's rules into its skill keeps the main prompt short.

### Go deeper

- **Progressive disclosure.** Three levels: the one-line note is always loaded, the file is loaded when the job fits, and any extra files the skill points to are loaded only if a step needs them.
- **A skill can hide raw tools.** If the agent can call the raw tools directly, it can skip the skill's rules. Hiding those tools from the lookup forces the job through the skill.
- **Not everything needs a skill.** One tool with light rules can live with a good tool description. A skill earns its place with several steps, a choice the brand owns, or rules that must not be skipped.
- **Shared skills vs per-workspace skills.** One shared set serves every customer and one fix reaches all of them. A customer's own routine may need its own skill. Many systems do both: built-in skills plus a workspace's own, merged.
- **The notes are the interface.** The agent picks a skill by its "pick me when" line. Two skills with notes that sound alike lead to wrong picks, and the fix is better notes.

**Question to hold:** which parts of your own system's prompt are really a recipe for one kind of job?

### Read further

- [Anthropic: Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills). Why skills exist, and how progressive disclosure keeps them cheap.
- [Anthropic: Introducing Agent Skills](https://www.anthropic.com/news/skills). The short announcement, with examples.
- [Agent Skills](https://agentskills.io). The open format for skill folders: what goes in SKILL.md, and how agents load it.

## 3. MCP: one plug for outside services

MCP (Model Context Protocol) is a common plug between an agent and an outside service. The service runs an MCP server that lists its own tools. Any agent that speaks MCP can use them, with no custom code for each pair.

### Start here

- **The problem it solves.** Five agents and five services means up to 25 custom connections. With MCP, each service writes one server and each agent one client.
- **A server lists its tools.** Each with a name, a description and an input schema: the same three things you would write by hand for a local tool. It can also add hints, such as "this tool only reads" or "this tool can delete".
- **A client plugs them in.** The agent connects, lists the server's tools, adds them to its own catalogue, and calls them like any other tool.
- **Transports.** How the client and the server talk: inside one program, as a local process (stdio), or over HTTP to a remote server.
- **More than tools.** A server can also offer resources (data to read) and prompts (ready-made templates). The session uses tools only.

### Go deeper

- **Write a tool, or plug in a server?** A server someone else maintains saves you the work, but its descriptions ride in your prompt, its changes reach you without a release, and you depend on its uptime.
- **Hints are claims, not guarantees.** The MCP spec says clients must treat tool annotations as untrusted unless the server is trusted. Your harness decides what needs a person's yes, not the server.
- **Many servers, many tools.** Plug in a few servers and the catalogue grows fast. This is where tool lookup, or letting the agent write code that calls tools, starts to pay.
- **Auth.** Remote servers usually sign in with OAuth, per user. Tokens expire and must be refreshed; that is where most real integration pain lives.
- **Results are untrusted input.** Whatever a server returns is data written by someone else.

**Question to hold:** when you plug in a server you did not write, who decides what it may change?

### Read further

- [MCP: Introduction](https://modelcontextprotocol.io/docs/getting-started/intro). What MCP is, the server and client roles, and the transports.
- [Anthropic: Introducing the Model Context Protocol](https://www.anthropic.com/news/model-context-protocol). Why it was created, in one page.
- [MCP spec: Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools). How a server lists tools, the hints it can add, and the trust rules.
- [Anthropic: Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp). What changes when an agent has hundreds of MCP tools.
- [Agno: MCP tools](https://docs.agno.com/tools/mcp/overview). How the framework in the repo connects to an MCP server.

## 4. Subagents and orchestration: when one agent is not enough

Skills and tools add ability inside one agent's view. Everything a tool returns stays in that view. A subagent is a second agent that does a job in its own view and hands back only the answer.

### Start here

- **Subagent.** An agent another agent calls like a tool. It is the same round trip as a tool call, except a whole agent runs instead of a function.
- **Orchestrator.** Whoever splits the work, writes the briefs, sends them out and gathers the answers. It can be a model, or plain code.
- **Three reasons a subagent earns its place.** A small view: it digs through the noise and returns a short report, so the main view stays small turn after turn. Safe tools: it gets only the tools its job needs. Side by side: independent jobs can run at the same time.
- **The practical test.** A task suits a subagent when it fits in a self-contained brief, its answer fits in a short report, and it is noisy, can run side by side, or needs different settings.
- **Start with one agent.** One agent plus skills and tools first. Add a subagent only when a separate view solves a real problem. A skill changes what an agent knows; a subagent changes what it sees.

### Go deeper

- **What it costs.** More tokens: every subagent sets up its own view and loop, and the orchestrator reads every report. The handoff loses whatever the brief left out. And helpers cannot see each other, so their reports come back in different shapes.
- **Code in charge, or the model?** When the steps are known in advance, a fixed loop in code is cheap, predictable and easy to trace. When the split depends on the ask, let the model decide.
- **The agent that reads the web should not hold the tools that write.** A page can carry instructions. A read-only research subagent cannot act on them, even if it reads them.
- **Same helpers, or specialists?** Several copies of one research agent, or different specialists with their own instructions, tools and even model. Specialists need clear scopes, or the handoffs become the bug.
- **The map.** Multi-agent is the umbrella. One orchestrator with subagents is the most common shape. Others: a handoff, where the user is passed to one specialist and the main agent steps aside; and peers that talk to each other.

**Question to hold:** in your own system, which job is noisy digging with a short answer?

### How frameworks name it

One line each; no verdicts here.

| Framework | What it calls the pattern | Docs |
| --- | --- | --- |
| Agno | Teams: a team leader routes to member agents | [Teams](https://docs.agno.com/teams/introduction) |
| Claude Agent SDK | Subagents with their own prompt, tools and context | [Subagents](https://docs.claude.com/en/docs/agent-sdk/subagents) |
| OpenAI Agents SDK | Handoffs, and agents used as tools | [Handoffs](https://openai.github.io/openai-agents-python/handoffs/) |
| LangGraph | Supervisor and network graphs of agents | [Multi-agent](https://langchain-ai.github.io/langgraph/concepts/multi_agent/) |
| Google ADK | Multi-agent systems with parent and sub-agents | [Multi-agents](https://google.github.io/adk-docs/agents/multi-agents/) |

### Read further

- [Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system). A lead agent with parallel subagents, what it gained and what it cost.
- [Cognition: Don't build multi-agents](https://cognition.ai/blog/dont-build-multi-agents). The case against, mostly about lost context between agents. Read it next to the one above.
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents). The orchestrator-workers and parallelization patterns, in plain terms.
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents). Why a small view matters, and where subagents fit.
