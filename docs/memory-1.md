# Memory step 1 · Switch it on, then read what it kept

Maya ran the Tidal launch a month ago. Along the way she typed: *the lakeside one*; *use our shoot photo, not an AI one*; *never call it unbreakable*; *make this one wide, it's for the web banner*; *yes, attach them and mark it ready*. Today she opens a new chat: "Breeze launches next month. Same as Tidal — concepts, then every size." The new chat has never heard of Tidal.

## What is already there

Nothing in this list is new to build. It is here so nothing changes without you knowing.

- **The store is not new.**
  - Since Session 2, every run says who it is for (`user_id`) and which thread it belongs to (`session_id`). Agno files the turns in `data/sessions.db`, and that is how the last 5 turns ride along.
  - One Db object holds sessions and memories, each in its own table, with different lifetimes: a session lasts one conversation, and a memory outlives it.
- **New in the harness, ready-made:**
  - A `# Memory` section in the prompt (`launchkit/agents/prompt.py`). LaunchKit writes its own system message, so Agno's `add_memories_to_context` never reaches the prompt here. The harness does what Agno's default does instead: every row this person may read, every turn (`memory_text` in `launchkit/memory/long_term.py`).
  - `MemoryDb`, the memory table's door. It marks every row with who said it and where it came from. The harness sets those two fields, never the agent.
  - The chat page's Context tab now shows the tokens of memory in the prompt.
  - Breeze in Harbor's `facts.md`, and its shoot photo in `samples/shoot/breeze-shoot.jpg`.

## The slot

- `launchkit/agents/main_agent.py`, `build_main_agent`: one setting on the `Agent(...)` call.
- `launchkit/memory/layer_map.yaml`: where each kept row really belonged. You write this by hand, not your coding agent.

## Break it first

In the terminal, start from an empty store and open the chat page:

```
uv run launchkit forget harbor
uv run launchkit ui
```

On the chat page:
1. Sign in as Maya at Harbor and press **New conversation**. Leave **Model** empty for the real model.
2. Send: "Breeze launches next month. Same as Tidal — concepts, then every size."

**What to look for:**
- **The Trace tab:** the agent writes a concept, every check passes, and `generate_image` makes a new AI picture. No photo was attached and nothing on file said otherwise, so that was the right pick for what the agent knew.
- **The Context tab:** 0 tokens of memory in the prompt.
- **The real model may ask for a photo on its own** instead of making a picture. If it does, note it: it is one of the outcomes the room may see.

Then look at the store, in the terminal (`uv run launchkit store`) or in SQLite Viewer (see the README). `agno_sessions` and `agno_runs` have a row for this conversation, and `agno_memories` has none.

## Prompt card, for your coding agent

```
In launchkit/agents/main_agent.py, in build_main_agent, add update_memory_on_run=True to the
Agent(...) call, next to num_history_runs. Change nothing else.
```

Restart `uv run launchkit ui`, then on the chat page:
1. Signed in as Maya, press **New conversation**.
2. Send Maya's two Tidal messages, one after the other:
   - "Tidal poster: the lakeside one. Use our shoot photo, not an AI one, and never call it unbreakable. Make this one wide, it's for the web banner."
   - "Yes, attach them and mark it ready. Thanks!"

After every run, a second model call (Agno's memory manager) read what was said and kept what looked worth keeping. Nobody asked it to keep anything. Read what it kept, in the terminal:

```
uv run launchkit memories harbor                   # numbered, as get_user_memories returns them
uv run launchkit store agno_memories               # the same rows, every column, as the table holds them
```

Or open `agno_memories` in SQLite Viewer. Expect several rows: the photo rule, plus things that were never memories. Read the list as it came back. The exact rows depend on the model.

**Now sort them, by hand.** For each row, write one entry in `launchkit/memory/layer_map.yaml`. Copy the row's words, then say where it belonged and why. `belongs` is one of: `nowhere`, `the conversation`, `session state`, `the board`, `the brand files`, `the trace`, `memory`.

```
- kept: "<the row, as the store has it>"
  belongs: ...
  why: ...
```

## Prove it

```
uv run launchkit check mem1
```

The checks run offline on `fake:memory`, a scripted model that keeps the same seven rows every time.

- After Maya's two Tidal messages, the store holds rows for her, and the photo rule is one of them.
- `layer_map.yaml` sorts the dump: at least five rows, each in one of the seven places, each with why.
- Of everything it kept, only the photo rule belongs in memory.
- Breeze in a new chat, after the two launches: no AI picture; the agent asks for Harbor's photo.

## Run it again

On the chat page, still signed in as Maya, press **New conversation** and send the Breeze message again.

**What to look for:**
- **The reply:** no AI picture this time. The agent asks for Harbor's shoot photo.
- **The Context tab:** memory in the prompt is no longer 0. It is every row the store kept, on every turn, whatever the message.

Attach `samples/shoot/breeze-shoot.jpg` with 📎 and send "Here it is." The poster uses Harbor's photo.

## Why it matters

It worked: Maya does not have to type the photo rule again. But only one row was a memory. The rest were:
- politeness;
- one afternoon's yes;
- work already on the board;
- a rule already in the brand files;
- a one-off pick;
- a one-off format.

"Maya prefers wide formats", or whatever your store kept about *wide*, now argues with every square feed post. Nothing here is a bug. This is "remember what matters" with nobody deciding what matters.

## If the real model is not available

Offline, without a key, or to see the same result every time: type `fake:memory` in **Model**. The fake keeps exactly these seven rows:

```
Maya prefers wide formats.
Never call the bottle unbreakable.
Maya picked the lakeside concept.
Harbor uses its own photography for launches, never AI-generated pictures.
Maya says thanks at the end of a job.
Maya approved attaching files to the Tidal card.
The new sizes are on the Tidal card, marked ready.
```

## Stuck?

The answer is on the branch `session-03-memory-step2`.
