# Checkpoint 1 · One agent and a skill (CP2.2a)

Task 2 on the Tidal card: "How are Hydro Flask, Stanley, Yeti, Owala and Klean Kanteen launching bottles this season? One paragraph each: message, channels, what to avoid copying."

We start the way the opening ended: one agent plus a skill. A skill is a plain-words file. It tells the main agent how to do a job: which tool to call, in what order, and what to hand back. The main agent finds it with `find_tool`, loads it with `run_skill`, and calls tools through `run_tool`.

It works. Then look at what it cost.

## The slot

- `launchkit/skills/competitor_research/skill.md`. It does not exist yet.

## Break it first

Before you paste the card, run this and keep the output:

```
uv run launchkit main harbor "How are Hydro Flask, Stanley, Yeti, Owala and Klean Kanteen launching bottles this season? One paragraph each." --model fake:brief
```

```
  tool      find_tool("How are Hydro Flask, Stanley, Yeti, Owala and Klean Kantee…) → skill market_research: finding out what people are talking … · 38 tokens back

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

The same ask after the build, on the chat page, with the pages as slow as a real web search. Start the page with `LAUNCHKIT_SEARCH_DELAY=0.4 uv run launchkit ui`, sign in as Maya at Harbor, press **New conversation**, type `fake:brief` in **Model** and send "How are Hydro Flask, Stanley, Yeti, Owala and Klean Kanteen launching bottles this season? One paragraph each." The Trace tab shows:

```
  tool      run_skill("competitor_research") → # competitor_research Pick me when: the job is to find out … · 152 tokens back
  tool      search_web("Hydro Flask bottle launch") → # Role Model and Hydro Flask Launch Limited Edition Drinkwa… · 1977 tokens back
  tool      search_web("Stanley bottle launch") → # Stanley Cup Marketing Strategy - Soar With Us Address: ht… · 2083 tokens back
  ...three more, one after another...
```

The Context tab: 9,858 tokens of tool results, 0 of history carried in, 2.1 s.

Then Maya's next ask, in the same conversation: "Write one headline for the hiker concept." The Context tab: 0 tokens of tool results, 10,005 tokens of history carried in.

In the terminal, `uv run launchkit main harbor "..." --model fake:brief --session cp1` does the same; `--session` keeps the conversation.

Five paragraphs came back, and every page the agent read came with them. Ten pages, about 9,900 tokens, sit in the main agent's view. A headline needs none of them, yet they ride along on every turn that follows. And the five searches ran one after another.

## Why it matters

A skill adds ability inside one view. It changes what the agent knows, not what it sees: everything a tool returns stays in that view. That is fine for most jobs. It stops being fine when the digging is big and the answer is small.

## See it

The trainer runs the same ask on the real model: leave **Model** empty. On 30 Oct, gpt-4.1-mini with live web search, 2 runs: about 10,300 tokens of pages in view, 13 to 21 seconds. The five searches run one after another.

## Stuck?

The answer is on the branch `session-02-orchestration-step1`.
