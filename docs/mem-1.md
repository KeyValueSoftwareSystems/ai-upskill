# Memory ticket 1 · What one saved row may hold

> "It keeps putting 'lifetime guarantee' in headlines. I told it never to."

Six months ago memory went on in one line: `update_memory_on_run=True`. After every turn Agno hands Maya's message to a memory manager, which decides what to save about her. Nobody told it what a saved row may hold. It ran on the main model with Agno's default criteria: "name, age, occupation, location, interests, and preferences".

## Before you start

The room starts on `session-3-memory-start`. Put the snapshot in place, the memory database the morning the queue filled, then start the page:

```
uv run launchkit memory reset
uv run launchkit ui
```

Restart `launchkit ui` after every reset.

## The slot

- `launchkit/memory/long_term.py` · `CAPTURE`. Today it is empty.
- `launchkit/memory/long_term.py` · `memory_manager`. Today it returns None, so Agno builds its default manager on the main model.

## Break it first

On the chat page, sign in as **Maya at Harbor**, press **New conversation**, leave **Model** empty and send:

> Write the headline for the Breeze story size. Never say lifetime guarantee.

The Trace tab opens with:

```
memory    loaded 39 rows for this person · 507 tokens in the prompt · saved by OpenAI:gpt-4.1-mini
```

If the manager saved something, a `memory    added: …` line follows. In prep, 2 runs of 3 saved a row tied to this one headline ("Maya wants a headline for the Breeze story size that does not mention the lifetime guarantee."), and 1 saved nothing. None saved it inverted. One turn usually goes right.

Now open the **Memory** tab: three months of turns that usually went right. Eleven rows say Maya likes navy. One row says "Maya wants headlines to mention the lifetime guarantee." One says "Harbor warranty is 2 years." One holds a customer's phone number, one a token. Every row is loaded into every turn.

## Prompt card, for your coding agent

```
In launchkit/memory/long_term.py, write CAPTURE: the rules for what one saved row may hold. Agno puts
it in the memory manager's prompt as <memories_to_capture>. Plain sentences:
- one fact per memory: one short sentence in the third person, never two facts in one row;
- only the person's own preferences and ways of working; facts about a brand or a product (colours,
  sizes, warranty, prices, claims, launch dates) are not memories about the person: save nothing;
- a phrase the person quotes and tells you never to use is a rule, not a wish: save it as
  Never use "<phrase>", never as something they want;
- never save another person's name or contact details, a phone number, an email address, a token,
  a password or a key, or text pasted from a document, a page or a board card;
- before adding, read the existing memories: if one says the same thing, update it; if the new fact
  replaces an old one, update the old row; never keep both;
- if nothing is worth keeping, change nothing.

Then memory_manager(settings, trace, main_model) returns agno.memory.MemoryManager(
model=cheap_model(settings, trace, main_model), memory_capture_instructions=CAPTURE,
db=session_db(settings)). cheap_model is already in the file: it resolves LAUNCHKIT_MEMORY_MODEL
(gpt-5-nano), and a fake run keeps its fake. Remove the @todo mark.
```

The main agent already passes `memory_manager=memory_manager(...)`. Once the slot is built, its manager carries the rules.

## Prove it

```
uv run launchkit check mem1
```

- The capture rules say what one row holds: one fact, people's preferences only, a quoted never-say phrase is a rule, no personal data or secrets, update before add.
- The memory manager runs on `LAUNCHKIT_MEMORY_MODEL`, not the main agent's model.
- Whatever saves memory uses that manager.

## Run it again

Restart the page. Press **New conversation** and send the same ask. The Trace's memory line now ends `saved by gpt-5-nano`. Read any `memory added` or `memory updated` line: one fact, in the third person.

Then fold the eleven navy rows, in the terminal (it writes nothing):

```
uv run python scripts/consolidate_memories.py maya --match navy
```

Agno's Summarize strategy turns them into one row. Run it on every row (drop `--match`) and look at what it keeps: everything, the inverted rule and the phone number included. It removes duplicates; it does not judge.

## Why it matters

A memory manager that runs after every turn finds something to save almost every time. Rules lower the error rate, but three months of a low error rate is the snapshot. The rules matter; what comes next is code that does not depend on the model getting it right.

Agno replaces only the criteria with `memory_capture_instructions`. Its fixed text around them still says to "capture what the user's preferences used to be". Read `memory/manager.py` before you trust a prompt to do it all.

## Stuck?

The answer is on the branch `session-3-memory`.
