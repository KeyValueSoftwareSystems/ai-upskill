# Memory step 1 · Switch it on, then read what it kept

Maya ran the Tidal launch a month ago. Along the way she typed: *the lakeside one*; *use our shoot photo, not an AI one*; *never call it unbreakable*; *make this one wide, it's for the web banner*; *yes, attach them and mark it ready*. Today she opens a new chat: "Breeze launches next month. Same as Tidal — concepts, then every size." The new chat has never heard of Tidal.

## What is already there

Nothing in this list is new to build. It is here so nothing changes without you knowing.

- **The store is not new.** Since Session 2, every run says who it is for (`user_id`) and which thread it belongs to (`session_id`). Agno files the turns in `data/sessions.db`, and that is how the last 5 turns ride along. Run `uv run launchkit store` to see the tables: `agno_sessions` and `agno_runs` have rows, and `agno_memories` has none. One Db object holds both, with different lifetimes: a session lasts one conversation, and a memory outlives it.
- **New in the harness, ready-made:**
  - A `# Memory` section in the prompt (`launchkit/agents/prompt.py`). LaunchKit writes its own system message, so Agno's `add_memories_to_context` never reaches the prompt here. The harness does what Agno's default does instead: every row this person may read, every turn (`memory_text` in `launchkit/memory/long_term.py`).
  - `MemoryDb`, the memory table's door. It marks every row with who said it and where it came from. The harness sets those two fields, never the agent.
  - `fake:memory`, a scripted model for these steps.
  - The commands `launchkit memories`, `store`, `forget`, `seed-memories` and `replay`.
  - Breeze in Harbor's `facts.md`.

## The slot

- `launchkit/agents/main_agent.py`, `build_main_agent`: one setting on the `Agent(...)` call.
- `launchkit/memory/layer_map.yaml`: where each kept row really belonged. You write this by hand, not your coding agent.

## Break it first

```
uv run launchkit forget harbor
uv run launchkit main harbor "Breeze launches next month. Same as Tidal — concepts, then every size." --model fake:memory --session breeze
```

```
  model     main phase · fake:memory · sent 563 tokens, got back 91
  draft     headline "Cold for 24 hours" (4 words) · subheadline 7 words · body 15 words
  tool      generate_image("A deep blue steel bottle on a misty lakeshore at dawn, nav…) → file data/outputs/poster-….png · 24 tokens back

main agent's view  0 tokens of tool results this turn · 0 tokens of history carried in · 0 tokens of memory in the prompt
```

A concept, every check green, and a paid AI picture. No photo was attached and nothing on file said otherwise, so `generate_image` was the right pick for what the agent knew. `uv run launchkit memories harbor` says: No memories for maya at harbor.

## Prompt card, for your coding agent

```
In launchkit/agents/main_agent.py, in build_main_agent, add update_memory_on_run=True to the
Agent(...) call, next to num_history_runs. Change nothing else.
```

Then send Maya's two Tidal messages in one conversation, and read what the store kept:

```
uv run launchkit main harbor "Tidal poster: the lakeside one. Use our shoot photo, not an AI one, and never call it unbreakable. Make this one wide, it's for the web banner." --model fake:memory --session tidal
uv run launchkit main harbor "Yes, attach them and mark it ready. Thanks!" --model fake:memory --session tidal
uv run launchkit memories harbor
```

After every run, a second model call (Agno's memory manager) read what was said and kept what looked worth keeping. Nobody asked it to keep anything. On the fake you get seven rows:

```
 1. Maya prefers wide formats.
 2. Never call the bottle unbreakable.
 3. Maya picked the lakeside concept.
 4. Harbor uses its own photography for launches, never AI-generated pictures.
 5. Maya says thanks at the end of a job.
 6. Maya approved attaching files to the Tidal card.
 7. The new sizes are on the Tidal card, marked ready.
```

**Now sort them, by hand.** For each row, write one entry in `launchkit/memory/layer_map.yaml`. Copy the row's words exactly, then say where it belonged and why. `belongs` is one of: `nowhere`, `the conversation`, `session state`, `the board`, `the brand files`, `the trace`, `memory`.

```
- kept: "Maya prefers wide formats."
  belongs: ...
  why: ...
```

## Prove it

```
uv run launchkit check mem1
```

- After Maya's two Tidal messages, the store holds rows for her, and the photo rule is one of them.
- `layer_map.yaml` places every row the store kept, each with where it belonged and why.
- Of everything it kept, only the photo rule belongs in memory.
- Breeze in a new chat, after the two launches: no AI picture; the agent asks for Harbor's photo.

## Run it again

On the chat page (`uv run launchkit ui`):
1. Sign in as Maya at Harbor, press **New conversation** and type `fake:memory` in **Model**.
2. Send the two Tidal messages.
3. Press **New conversation** again and send the Breeze message.

The reply now reads: "Harbor uses its own photography, so I have not made an AI picture. Attach the shoot photo and I will make the concepts and every size from it." The Context tab shows about 136 tokens of memory in the prompt: all seven rows, on every turn, whatever the message.

## Why it matters

It worked: Maya does not have to type the photo rule again. But only one of the seven rows was a memory. The rest were:
- politeness;
- one afternoon's yes;
- work already on the board;
- a rule already in the brand files;
- a one-off pick;
- a one-off format.

"Maya prefers wide formats" now argues with every square feed post. Nothing here is a bug. This is "remember what matters" with nobody deciding what matters.

## See it

The trainer runs the two Tidal messages on the real model (leave **Model** empty) and puts `uv run launchkit memories harbor` on screen, unedited. The real dump differs from the fake's seven, so read it as it is.

## Stuck?

The answer is on the branch `session-03-memory-step2`.
