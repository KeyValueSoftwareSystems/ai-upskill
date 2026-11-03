# Memory step 1 · Switch it on, then read what it kept

A month ago Maya ran the Tidal launch in LaunchKit. Along the way she typed: *the lakeside one*; *use our shoot photo, not an AI one*; *never call it unbreakable*; *make this one wide, it's for the web banner*. Today she opens a new chat: "Breeze launches next month. Same as Tidal — concepts, then every size." The new chat has never heard of Tidal.

## Before you start: recreate Maya's Tidal launch

This session starts a month after the Tidal launch, so everyone needs that conversation first. It does not matter whether you did Session 2 or kept its data: do this once, on this branch, before the step. LaunchKit has no memory yet, so the Tidal chat is kept as a conversation and nothing else.

In the terminal, start from an empty memory store and open the chat page:

```
uv run launchkit forget harbor
uv run launchkit ui
```

On the chat page, sign in as **Maya** at **Harbor**, press **New conversation**, and leave **Model** empty for the real model. Then send three messages, one at a time, waiting for each reply.

1. Press 📎 and attach `samples/shoot/tidal-shoot.jpg` from the repo. Then send: "Tidal poster from our shoot photo: the lakeside one. Use our shoot photo, not an AI one, and never call it unbreakable."
   - **Expect:** a poster with a headline, subheadline and body, on Maya's photo. The Trace tab shows no `generate_image`: the photo was given, so nothing is bought.
2. Send: "Make this one wide, it's for the web banner."
   - **Expect:** the resize skill cuts the photo to the web banner size, 1200x628.
3. Send: "Love it. Now all the sizes, please."
   - **Expect:** the five Harbor sizes, one file each.
4. **Optional, only if your Notion board is connected from Session 2:** send "Put the new sizes on the Tidal card and mark it ready." **Allow** attaching and marking it ready. **Deny** removing files.

**Or, in one command:** the terminal sends the same three messages as one conversation, with the photo attached. Your terminal asks you before any write.

```
uv run launchkit replay harbor samples/sessions/tidal_launch.txt
```

Reload the chat page. The Tidal conversation is in the conversation list, and you can open it and read it like one you typed.

**Check where you are:** run `uv run launchkit store`, or open `data/sessions.db` in SQLite Viewer (see the README).
- `agno_sessions` has the Tidal conversation, and `agno_runs` has one row per message.
- `agno_memories` is empty. Nothing outlived the conversation.

## What is already there

Nothing in this list is new to build. It is here so nothing changes without you knowing.

- **The store is not new.**
  - Since Session 2, every run says who it is for (`user_id`) and which thread it belongs to (`session_id`). Agno files the turns in `data/sessions.db`, and that is how the last 5 turns ride along.
  - One Db object holds sessions and memories, each in its own table, with different lifetimes: a session lasts one conversation, and a memory outlives it.
- **New in the harness, ready-made:**
  - A `# Memory` section in the prompt (`launchkit/agents/prompt.py`). LaunchKit writes its own system message, so Agno's `add_memories_to_context` never reaches the prompt here. The harness does what Agno's default does instead: every row this person may read, every turn (`memory_text` in `launchkit/memory/long_term.py`).
  - `MemoryDb`, the memory table's door. It marks every row with who said it and where it came from. The harness sets those two fields, never the agent.
  - The Context tab now shows the tokens of memory in the prompt.
  - Breeze in Harbor's `facts.md`, and its shoot photo in `samples/shoot/breeze-shoot.jpg`.

## The slot

- `launchkit/agents/main_agent.py`, `build_main_agent`: one setting on the `Agent(...)` call.
- `launchkit/memory/layer_map.yaml`: where each kept row really belonged. You write this by hand, not your coding agent.

## Break it first

On the chat page, still signed in as Maya, press **New conversation** and send: "Breeze launches next month. Same as Tidal — concepts, then every size."

**What to look for:**
- **The Trace tab:** a concept, every check passing, and `generate_image` making a new AI picture. No photo was attached and nothing on file said otherwise, so that was the right pick for what the agent knew. "Same as Tidal" meant nothing in a chat that had never heard of Tidal.
- **The Context tab:** 0 tokens of memory in the prompt.
- **The real model may ask for a photo on its own** instead of making a picture. If it does, note it: it is one of the outcomes the room may see.

## Prompt card, for your coding agent

```
In launchkit/agents/main_agent.py, in build_main_agent, add update_memory_on_run=True to the
Agent(...) call, next to num_history_runs. Change nothing else.
```

Restart `uv run launchkit ui`.

Memory starts now. It learns nothing from the Tidal chat, which ran before it was switched on. So on the chat page, signed in as Maya, press **New conversation** and run a short launch, two messages:
1. "Tidal poster: the lakeside one. Use our shoot photo, not an AI one, and never call it unbreakable. Make this one wide, it's for the web banner."
2. "Yes, attach them and mark it ready. Thanks!"

After every run, a second model call (Agno's memory manager) read what was said and kept what looked worth keeping. Nobody asked it to keep anything. Read what it kept, in the terminal or in SQLite Viewer (`agno_memories`):

```
uv run launchkit memories harbor                   # numbered, as get_user_memories returns them
uv run launchkit store agno_memories               # the same rows, every column, as the table holds them
```

Expect several rows: the photo rule, plus things that were never memories. The exact rows depend on the model, so read the list as it came back.

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

The check runs offline on a scripted model, so it gives everyone the same result.

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

Whatever your store kept about *wide* now argues with every square feed post. Nothing here is a bug. This is "remember what matters" with nobody deciding what matters.

## Stuck?

The answer is on the branch `session-03-memory-step2`.

No model access (offline, or no key)? Type `fake:memory` in **Model**. Every step on this card works, with scripted replies.
