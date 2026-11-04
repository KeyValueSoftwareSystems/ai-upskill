# Memory hands-on 1 · What goes in

A month ago Maya ran the Tidal launch in LaunchKit. Along the way she typed: *the lakeside one*; *use our shoot photo, not an AI one*; *never call it unbreakable*; *make this one wide, it's for the web banner*. Today she opens a new chat: "Breeze launches next month. Same as Tidal — concepts, then every size." The new chat has never heard of Tidal.

This hands-on is about what goes into memory, in three parts, each one fixing what the part before it left:

- **Part 1, switch it on:** one setting, and the agent keeps things. Then you read what it kept, and sort it.
- **Part 2, what earns a write:** a decision you can see, and rules you wrote, in place of an extractor nobody sees.
- **Part 3, whose it is:** Maya says yes before a row is kept, and whether it is hers or for everyone at Harbor.

## Before you start: recreate Maya's Tidal launch

This session starts a month after the Tidal launch, so everyone needs that conversation first. It does not matter whether you did Session 2 or kept its data: do this once, on this branch, before Part 1. LaunchKit has no memory yet, so the Tidal chat is kept as a conversation and nothing else.

In the terminal, start from an empty memory store and open the chat page:

```
uv run launchkit forget harbor
uv run launchkit ui
```

Leave the page running for the whole hands-on. When you save a change to the code, it restarts by itself: the terminal says `Reloading...`. Then reload the browser tab.

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
- **A `# Memory` section in the prompt** (`launchkit/agents/prompt.py`). LaunchKit writes its own system message, so Agno's `add_memories_to_context` never reaches the prompt here. The harness does what Agno's default does instead: every row this person may read, every turn (`memory_text` in `launchkit/memory/long_term.py`).
- **`MemoryDb`** (`launchkit/memory/long_term.py`): the agent's database, `data/sessions.db`, passed to the agent as `db=`. It is Agno's `SqliteDb` with a door on one write: sessions and runs pass through unchanged, and every memory row goes through the door first.
    - The door marks each row with who said it (`author:`) and where it came from (`source:`). The harness sets those two fields, never the agent.
    - Once your gate is built (Part 3), it asks the gate before every write. A row kept for everyone goes under the `user_id` `harbor:everyone`: Agno scopes memory by user id only and has no workspace, so the shared tier is an id of its own.
    - Every read is the person's own rows plus the workspace's, and nobody else's.
    - The door has to be inside the database, because Agno's memory manager writes straight to whatever `db` it is given. A check anywhere else would be skipped.
- **`write_rules()`** in `long_term.py` reads `launchkit/memory/write_rules.md`, once you have written it (Part 2).
- **The instruction for the memory tool** (`MEMORY_TASK` and `MEMORY_SHARE`, same file).
    - Agno tells the model about `update_user_memory` inside the system message it builds itself, and LaunchKit writes its own. LaunchKit's task also says to call `find_tool` first and every tool only through `run_tool`.
    - So without this, the real model holds the tool but never calls it, and nothing reaches the memory manager.
    - Once you turn `enable_agentic_memory` on (Part 2), the harness opens the `# Task` section with Agno's instruction, worded for the three doors: before `find_tool`, call `update_user_memory` when the message states a rule, preference or correction meant to last. It has to come first: placed later in the prompt, "call find_tool first" wins, and the model rarely calls the memory tool.
    - The `# Memory` section adds one line for Part 3: call it again when something already kept should be kept for everyone.
- **The Context tab** shows the tokens of memory in the prompt.
- **Breeze** in Harbor's `facts.md`, and its shoot photo in `samples/shoot/breeze-shoot.jpg`.

## The slots

- **Part 1:** `launchkit/agents/main_agent.py`, `build_main_agent`: one setting on the `Agent(...)` call. Then a sort, by hand, on a ready-made page: `docs/memory-sort.html`.
- **Part 2:** the memory settings on the same `Agent(...)` call; and `launchkit/memory/write_rules.md`, which does not exist yet.
- **Part 3:** `launchkit/memory/write_gate.py`, `ask_before_keeping`.

## Part 1 · Switch it on, then read what it kept

The new chat has never heard of Tidal. In this part one setting makes the agent keep things after every run, and you read what it kept. You build the switch; at the end, Breeze in a new chat asks for Harbor's photo, and you sort everything the store kept.

### Break it first

On the chat page, still signed in as Maya, press **New conversation** and send: "Breeze launches next month. Same as Tidal — concepts, then every size."

**What to look for:**

- **The Trace tab:** a concept, every check passing, and `generate_image` making a new AI picture. No photo was attached and nothing on file said otherwise, so that was the right pick for what the agent knew. "Same as Tidal" meant nothing in a chat that had never heard of Tidal.
- **The Context tab:** 0 tokens of memory in the prompt.
- **The real model may ask for a photo on its own** instead of making a picture. If it does, note it: it is one of the outcomes the room may see.

### Prompt card, for your coding agent

```
1. In launchkit/agents/main_agent.py, in build_main_agent, add update_memory_on_run=True to the
   Agent(...) call, next to num_history_runs. Change nothing else.
```

### Run it again

Save the file. The page restarts by itself (the terminal says `Reloading...`); reload the browser tab.

Memory starts now. It learns nothing from the Tidal chat, which ran before it was switched on. So on the chat page, signed in as Maya, press **New conversation** and run a short launch, two messages:

1. "Tidal poster: the lakeside one. Use our shoot photo, not an AI one, and never call it unbreakable. Make this one wide, it's for the web banner."
2. "Yes, attach them and mark it ready. Thanks!"

After every run, a second model call (Agno's memory manager) read what was said and kept what looked worth keeping. Nobody asked it to keep anything. Read what it kept, in the terminal or in SQLite Viewer (`agno_memories`):

```
uv run launchkit memories harbor                   # numbered, as get_user_memories returns them
uv run launchkit store agno_memories               # the same rows, every column, as the table holds them
```

Expect several rows: the photo rule, plus things that were never memories. The exact rows depend on the model, so read the list as it came back.

Then press **New conversation** and send the Breeze message again.

**What to look for:**

- **The reply:** no AI picture this time. The agent asks for Harbor's shoot photo.
- **The Context tab:** memory in the prompt is no longer 0. It is every row the store kept, on every turn, whatever the message.

Attach `samples/shoot/breeze-shoot.jpg` with 📎 and send "Here it is." The poster uses Harbor's photo.

### Now sort them

Open `docs/memory-sort.html` in your browser: double-click it in your file manager, or run `xdg-open docs/memory-sort.html` (`open` on a Mac).

- It holds nine sentences like the ones your store kept, one for each place a sentence can belong:
    - nowhere;
    - the conversation;
    - session state;
    - the board;
    - the brand files;
    - a skill;
    - the trace;
    - the memory store.
- Pick a place for every sentence, then press **Reveal answers** at the end. Each sentence shows the right place, the kind of memory it is (short-term, working, episodic, semantic, procedural, or not memory at all), and why, with your score.

Then go back to your own dump: each of your rows is one of those nine kinds. How many of yours belonged in the memory store?

It worked: Maya does not have to type the photo rule again. But only one row was a memory. Whatever your store kept about *wide* now argues with every square feed post, and nobody can point at the moment a decision was made to keep any of it.

## Part 2 · What earns a write

Part 1's extractor kept whatever looked worth keeping, after every run, with nobody deciding. In this part the agent decides instead: it calls a memory tool you can see in the trace. The memory manager behind that tool keeps only what your rules allow. You build the switch and the rules; at the end, one clean row is kept.

### Break it first

Carry on from Part 1: do not empty the store. Memory belongs to the person, not the conversation, so the rows Maya's Tidal messages left in Part 1 are still hers, whichever chat she opens. Read them again:

```
uv run launchkit memories harbor                   # Maya's rows from Part 1
```

**If it says No memories** (you emptied the store), send the two Tidal messages from Part 1 once on the chat page as Maya, with **Model** empty. Any conversation will do.

**What to look for:**

- **Rows nobody chose:** a one-off squashed into a preference ("wide, for the web banner" sitting inside the photo rule), a plan, perhaps a row that is pure noise. A message that said only "use this" can leave: "User wants to use 'this' but the context … was not provided".
- **No trace line for any of them.** The extractor wrote after the run, on its own call, so there is no moment in the trace where a decision was made.

### What changes, and why

- **Before:** after every run, a second model call read the exchange and wrote whatever it liked (`update_memory_on_run`).
- **After:** the agent holds a tool, `update_user_memory`, and decides when to call it (`enable_agentic_memory`), so every write is a line in the Trace tab. Agno puts this tool **beside** `find_tool`, `run_skill` and `run_tool`, not behind them: it is a fourth door, and Session 2's leash hook sees it like any other tool.
- When the agent calls it, Agno's `MemoryManager` makes its own model call to decide what to add. `memory_capture_instructions` is where your rules go. Without them, Agno's default asks for "personal information about the user", which is why Part 1 kept what it kept.
- If both flags are on, the agentic one wins: Agno skips the extractor whenever `enable_agentic_memory` is set.

### Prompt card, for your coding agent

```
2. In launchkit/agents/main_agent.py, build_main_agent: remove update_memory_on_run=True from the
   Agent(...) call. Add enable_agentic_memory=True and
   memory_manager=MemoryManager(memory_capture_instructions=write_rules(), delete_memories=False).
   Import MemoryManager from agno.memory, and write_rules from launchkit.memory.long_term.
   Leave db as it is: the memory manager writes through it.

3. Create launchkit/memory/write_rules.md, plain words. Say: keep only what changes how the agent
   works next time and is true beyond this conversation. Keep it only if it is one of four kinds,
   and put the kind first in its topics: preference, domain fact, workflow, correction, each with
   one example. Then a "Never keep" list: thanks and small talk; a yes or no to one action (that
   permission is for one run); the work itself (it lives on the board); a rule already in the brand
   files; one choice on one afternoon. Last line: when unsure, do not keep it.
```

### Run it again

In the terminal, run `uv run launchkit forget harbor`. The store is emptied on purpose: Part 1's rows went in with no rules, and you want to see only what your rules let through. Conversations stay.

Saving `main_agent.py` restarted the page by itself; reload the browser tab. `write_rules.md` is read on every run, so editing it needs no restart.

On the chat page, sign in as Maya at Harbor and send the two Tidal messages from Part 1 again. Your conversation from Part 1 is fine, or press **New conversation**.

**What to look for:**

- **The Trace tab:** one `update_user_memory(…)` line for each thing the agent offered to keep, followed by `note  memory kept · maya · …` for each row that got through.
    - How many it offers depends on the model.
    - Your rules decide how many get through: the photo rule should, and thanks, the yes to attaching, and the one-off "wide" should not.
- **The store** (`uv run launchkit store agno_memories`, or SQLite Viewer):
    - one clean row, the photo rule;
    - `user_id` `maya`;
    - `topics` carrying its kind (`preference`), `author:maya` and `source:conversation`.
- **Sometimes one more row gets through**, such as "keep the lakeside concept". Read it against your rules: it is one choice on one afternoon, and your "Never keep" list names it. Tighten `write_rules.md` and run it again.

The row is right. It is Maya's, and Maya is not the only person at Harbor.

## Part 3 · Whose it is

Part 2's row is right, and it is Maya's. Every row is filed under the person who said it, and Harbor has more than one person. Sam starts on Breeze and buys an AI picture, because Maya's photo rule never reaches Sam. In this part Maya is asked before a row is kept, and whether it is just hers or for everyone at Harbor. A row kept for everyone reaches Sam. You build the ask; at the end, Sam's Breeze run asks for the photo.

### Break it first

On the chat page, sign in as **Sam** at Harbor, press **New conversation**, and send: "Breeze launches next month. Same as Tidal — concepts, then every size."

**What to look for:**

- **Sam's run:**
    - a concept and a new AI picture in the Trace tab;
    - 0 tokens of memory in the Context tab;
    - Maya's clean row is filed under `maya`, so it never reaches Sam.
- **The real model may ask for a photo anyway.** Read Sam's Context tab: at 0 tokens of memory, Maya's rule did not reach Sam, and the ask is the model's own caution.
- **Sam's own message:** with agentic memory on, the agent decides whether Sam's message is worth an `update_user_memory` call. "Breeze launches next month…" is a request about a product, not a fact about Sam, so there is usually no call and no row.
    - To see Sam get a row of Sam's own, send: "I'm new at Harbor and I always start with the picture before the copy."
    - Then run `uv run launchkit memories harbor --user sam`. Sam's habit is kept under `sam`, and Maya's photo rule is still nowhere in Sam's list.

Check the store from the terminal:

```
uv run launchkit store agno_memories               # every row, every column: user_id maya or sam
uv run launchkit memories harbor --user sam        # what Sam may read: none of Maya's rows
```

The obvious repair is to give everyone at Harbor the same id. It works on the Monday. By Friday, Maya's habit of reviewing the square format first has become Harbor policy, and Sam, who works picture-first, argues with the agent every day without knowing why.

### What changes, and why

- **Before:** a row is kept as soon as the rules let it through, and always as the speaker's.
- **After:** Maya is asked before a row is kept, and asked again whether it is for everyone at Harbor, with a warning that this changes the agent for everybody. Personal by default, workspace only on a yes.
- The ask is Session 2's approval rule, now in front of the memory table. The scope is chosen when the fact is written, not when it is read.
- A row already kept can be shared later. Maya says so in the chat, and her answer to the second ask moves the row (`MemoryDb` does the moving, ready-made).

### Prompt card, for your coding agent

```
4. In launchkit/memory/write_gate.py, build ask_before_keeping(memory, topics, approve): remove the
   @todo and the raise. Find the kind among topics (preference, domain fact, workflow, correction).
   Call approve("keep_in_memory", {"memory": memory, "kind": kind}); on no, return None. Then call
   approve("keep_for_everyone", {"memory": memory, "warning": "This changes the agent for everybody
   at the brand, not only you."}); return "workspace" on yes, "user" on no.
```

### Run it again

Carry on where you are: no need to empty the store or resend the Tidal messages. Maya shares the rule she already kept, in the conversation she has open.

Saving `write_gate.py` restarted the page by itself, so it runs your gate: check the terminal says `Reloading...`, then reload the browser tab.

On the chat page:

1. Signed in as Maya, stay in your open conversation and send: "Use our own shoot photos, never AI pictures. That goes for everyone at Harbor."
2. The chat stops to ask, twice:
    - *The agent wants to keep_in_memory*, with the sentence and its kind;
    - *keep_for_everyone*, with the warning.
3. **Allow** both.
4. Sign in as **Sam**, press **New conversation**, and send the Breeze message. A new conversation keeps Sam's earlier Breeze turns out of the history.

**What to look for:**

- **The Trace tab, as Maya:** `update_user_memory(…)`, then `note  memory kept · everyone at harbor · …`. The rule was already kept, but who it is for is new, so the agent still calls the tool. If you deny the second ask, the note says `maya`, and Sam never sees it.
- **The store** (`uv run launchkit store agno_memories`):
    - the photo rule now has `user_id` `harbor:everyone`;
    - `topics` carries `preference`, `author:maya` and `source:conversation`;
    - Maya's own copy is gone. Agno never changes a row's `user_id`, so `MemoryDb` moves it: it deletes Maya's copy and writes everyone's new.
    - Sometimes the memory manager writes a fresh row instead of updating Maya's. Then Maya keeps her own copy as well; it does no harm, and Sam reads the shared one.
- **Sam's run:** the agent asks for Harbor's shoot photo instead of buying a picture. Sam's Context tab shows memory in the prompt: the row everyone at Harbor shares.

## Prove it

```
uv run launchkit check mem1
```

The check runs offline on a scripted model, so it gives everyone the same result. The first two pass after Part 1; five after Part 2; all eight after Part 3.

- Part 1: after Maya's two Tidal messages, the store holds rows for her, and the photo rule is one of them.
- Part 1: Breeze in a new chat, after the two launches: no AI picture; the agent asks for Harbor's photo.
- Part 2: with agentic memory on, the main agent calls `update_user_memory` itself, and the call is in the trace.
- Part 2: `memory/write_rules.md` names the four kinds of memory and says what is never kept.
- Part 2: two launches, Maya says yes: one row is kept, the photo rule, with its kind, who said it and where it came from.
- Part 3: Maya says no: nothing is kept, and the trace says she said no.
- Part 3: kept for everyone at Harbor, the photo rule reaches Sam's new chat; Maya's own rows stay hers.
- Part 3: Maya's own photo row, then in the same chat "that goes for everyone at Harbor": the row moves to everyone, and Sam sees it.

## Why it matters

Memory is not one store: the sort named its kinds, and only one of them belongs in the memory table. What decided whether memory worked was never the retrieval. It was the policy at the door:

- typed rows;
- a bar to clear: your rules, then Maya's yes;
- a source on every fact.

A page that can steer a tool call can seed a memory, and the memory outlives the page. And "everyone" is a choice made when the fact is written, with a warning, not a default.

## See it

The trainer turns both flags on together (`update_memory_on_run=True` and `enable_agentic_memory=True`), sends one Tidal message, and shows the extractor does not run: only the agent's own `update_user_memory` calls write.

## Stuck?

The answer is on the branch `session-03-memory-step2`.

No model access (offline, or no key)? Type `fake:memory` in **Model**. Every step on this card works, with scripted replies.
