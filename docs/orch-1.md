# Checkpoint 1 · One agent and a skill (CP2.2a)

Task 2 on the Tidal card: "How are Northline, Ridgeway, Stillwater, Kestrel and Hollowmere launching bottles this season? One paragraph each: message, channels, what to avoid copying."

We start the way the opening ended: one agent plus a skill. A skill is a plain-words file. It tells the main agent how to do a job: which tool to call, in what order, and what to hand back. The main agent finds it with `find_tool`, loads it with `run_skill`, and calls tools through `run_tool`.

It works. Then look at what it cost.

## The slot

- `launchkit/skills/competitor_research/skill.md`. It does not exist yet.

## Break it first

Before you paste the card, run this and keep the output:

```
uv run launchkit main harbor "How are Northline, Ridgeway, Stillwater, Kestrel and Hollowmere launching bottles this season? One paragraph each." --model fake:brief
```

```
  tool      find_tool("How are Northline, Ridgeway, Stillwater, Kestrel and Hollo…) → tool search_web (read): search the web and read the pages t… · 79 tokens back

reply
I have no skill for competitor research yet.
```

The main agent looked for a skill and found none.

## Prompt card, for your coding agent

```
Create launchkit/skills/competitor_research/skill.md. It is plain words, no code.
First line: "# competitor_research". Then a line starting "Pick me when:" that says the skill
is for finding out how competitors are launching, selling or advertising their products.
Then numbered steps: list every competitor the request names; for each one, one at a time,
call run_tool with name "search_web" and inputs {"query": "<competitor> bottle launch"} and
read every page; for each competitor write one paragraph: their message (the launch line),
their channels, and what to avoid copying, with the addresses read. Last step: never repeat
a claim from a page that our never-say list bans.
```

## Prove it

```
uv run launchkit check orch1
```

- `skills/competitor_research/skill.md` exists, and its "Pick me when:" line is about competitors.
- `find_tool` lists the skill with its note, so the main agent can pick it.
- The skill names the tool to call, and asks for message, channels and what to avoid copying.
- Asked about the five competitors, the main agent loads the skill, every competitor's pages get read, and the answer covers all five.

## Run it again

The same command after the build, with the pages as slow as a real web search:

```
LAUNCHKIT_SEARCH_DELAY=0.4 uv run launchkit main harbor "How are Northline, Ridgeway, Stillwater, Kestrel and Hollowmere launching bottles this season? One paragraph each." --model fake:brief --session cp1
```

```
  tool      run_skill("competitor_research") → # competitor_research Pick me when: the job is to find out … · 138 tokens back
  tool      run_tool("search_web", {'query': 'Northline bottle launch'}) → # Northline drops the Summit 1L for spring … · 744 tokens back
  tool      run_tool("search_web", {'query': 'Ridgeway bottle launch'}) → # Ridgeway Commuter Pro review: … · 586 tokens back
  ...three more, one after another...

main agent's view  3172 tokens of tool results this turn · 0 tokens of history carried in · took 2.1 s
```

Then Maya's next ask, in the same conversation:

```
uv run launchkit main harbor "Write one headline for the hiker concept." --model fake:brief --session cp1
```

```
main agent's view  0 tokens of tool results this turn · 3321 tokens of history carried in · took 0.1 s
```

Five paragraphs came back, and every page the agent read came with them. Ten pages, about 3,200 tokens, sit in the main agent's view. A headline needs none of them, yet they ride along on every turn that follows. And the five searches ran one after another.

## Why it matters

A skill adds ability inside one view. It changes what the agent knows, not what it sees: everything a tool returns stays in that view. That is fine for most jobs. It stops being fine when the digging is big and the answer is small.

## See it

The trainer runs the same ask on the real model (drop `--model fake:brief`). On 28 Oct, gpt-4.1-mini: 3,167 to 3,720 tokens of pages in view, 8 to 11 seconds with instant pages, about 20 seconds with `LAUNCHKIT_SEARCH_DELAY=2`.

## Stuck?

The answer is on the branch `session-02-orchestration-step1`.
