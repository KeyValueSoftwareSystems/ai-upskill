# Memory hands-on 2 · What comes back, and for how long

Hands-on 1 decided what goes in: one clean row, kept with Maya's yes, for the people it should reach. This hands-on is about what comes back out, in two parts. They do not depend on each other: stuck on Part A, you can still do Part B.

- **Part A, read it back cheaply:** after a month the store is full, and every row rides in every prompt. An index in the prompt, and a lookup the agent decides to make.
- **Part B, one long conversation:** a rule Maya stated on Monday is gone by Friday, in the same chat. A summary, and the rules that must survive it, re-stated by code.

## What is already there

Nothing in this list is new to build. It is here so nothing changes without you knowing.

- **Hands-on 1, answered:** `enable_agentic_memory` and the memory manager on the main agent, `launchkit/memory/write_rules.md`, and `ask_before_keeping` in `launchkit/memory/write_gate.py`.
- **For Part A:**
    - `INDEX_HEADER` and `LINE_CAP` in `launchkit/memory/index.py`.
    - The wiring: once both functions are built, the harness swaps the `# Memory` section for the index and adds `recall` to the catalogue.
    - `topic_of` and `kind_of` in `launchkit/memory/long_term.py`.
    - `samples/memory/harbor_month.yaml`, thirty rows invented for this step, and `uv run launchkit seed-memories harbor` to put them in the store.
    - `uv run launchkit memories harbor --prompt`, which prints the `# Memory` section as Maya's prompt carries it.
- **For Part B:**
    - A new section in the prompt, `# This conversation so far` (`launchkit/agents/prompt.py`). LaunchKit writes its own system message, so Agno's `add_session_summary_to_context` never reaches it. The section carries the summary, plus whatever `must_keep` returns (`conversation_text` in `launchkit/memory/compaction.py`).
    - `what_she_said` in the same file, which returns every message Maya sent in the conversation, including the ones the window dropped.
    - `samples/sessions/breeze_week.txt`, Maya's week, invented for this step.
- **For the trainer:** `uv run launchkit optimize harbor --user maya`, a preview of Agno's `optimize_memories`. It rewrites the store with `--apply`, so the trainer runs it, not the room.

The page restarts by itself when you save a change to the code: the terminal says `Reloading...`. Then reload the browser tab.

## The slots

- **Part A:** `launchkit/memory/index.py`, `memory_index(rows)` and `recall(rows, topic)`.
- **Part B:** `launchkit/agents/main_agent.py`, `build_main_agent`: one setting on the `Agent(...)` call; and `launchkit/memory/compaction.py`, `must_keep(said)`.

## Part A · Read it back cheaply

Two scopes mean more rows in front of the model on every run. After a month at Harbor the store holds thirty rows: Maya's, Sam's and everyone's. Maya sends a one-line Breeze brief, and the prompt carries every row she may read, whether or not it has anything to do with Breeze. Harbor pays for all of it on every turn. You build an index and a lookup; at the end, the prompt carries one line per topic, and the agent reads the photo rule only when Breeze needs it.

### Break it first

In the terminal, put a month of rows in the store and look at what the prompt will carry:

```
uv run launchkit forget harbor
uv run launchkit seed-memories harbor
uv run launchkit store agno_memories --limit 30    # thirty rows: user_id maya, sam or harbor:everyone; topics give each row's kind and topic
uv run launchkit memories harbor --prompt          # the Memory section as Maya's prompt carries it: every row she may read
```

On the chat page, sign in as Maya at Harbor, press **New conversation**, leave **Model** empty, and send: "Breeze launches next month. Same as Tidal — concepts, then every size."

**What to look for:**

- **The Context tab:** the tokens of memory in the prompt. Write the number down.
- **What the Breeze brief needed:** one of those topics, photography.

### What changes, and why

- **Before:** every row, every turn, in front of the model. That is Agno's default (`add_memories_to_context`), which LaunchKit's ready-made `# Memory` section does by hand, because LaunchKit writes its own system message.
- **After:** a short table of contents the model reads for free, plus a lookup it has to decide to make.
    - The index is built in plain code, with no model call: one line per topic, the number of facts, and the call that reads them.
    - `recall` is a read tool in the catalogue, so it goes through `run_tool` like every other tool, and its call is in the Trace tab.
- **The cost:** the agent can now miss a fact it would have been handed before, so the index line has to make it clear when to go and look.

### Prompt card, for your coding agent

```
1. In launchkit/memory/index.py, build both slots: remove @todo and the raise from each.

   memory_index(rows): return "" when there are no rows. Group the rows by topic_of(row) (import
   topic_of and kind_of from launchkit.memory.long_term), keeping first-seen order. For each topic,
   one line: '- <topic>: <n> facts · recall("<topic>")' ("1 fact" when there is one). Cut any line
   longer than LINE_CAP to LINE_CAP - 1 characters and add "…". Return INDEX_HEADER, a newline, then
   the lines joined by newlines. No model call.

   recall(rows, topic): the rows whose topic_of equals the topic (trimmed, lower case), one per line
   as "- <the memory> (<kind_of(row)>)". When none match, say nothing is kept under that topic and
   list the topics there are.
```

### Run it again

In the terminal, see the new section:

```
uv run launchkit memories harbor --prompt
```

```
# Memory, as the prompt carries it (the index, about 210 tokens)
Kept from earlier conversations, one line per topic. Before work a topic touches, read it with run_tool("recall", …
- review order: 1 fact · recall("review order")
- headlines: 2 facts · recall("headlines")
- photography: 3 facts · recall("photography")
…
```

Saving `index.py` restarted the page by itself; reload the browser tab. As Maya, press **New conversation** and send the Breeze message again.

**What to look for:**

- **The Trace tab:** `recall("photography")`, then a reply asking for Harbor's shoot photo.
    - The real model may recall a second topic too, such as headlines, or none at all.
    - Note what it did: a missed recall is the cost named above.
- **The Context tab:** memory in the prompt, down from the number you wrote down. Tool results now include the one lookup.

The index grows with topics, not rows, so the gap widens as the store does.

## Part B · One long conversation

This part is not about memory across conversations. It is about one conversation that runs all week. On Monday Maya opened a Breeze chat and said: "For this whole Breeze conversation: never mention the lid. The lid is changing before launch." Then she kept going in the same chat: trends, placements, the colourway, posting days, shoot moods, competitors. On Friday she asked for three Breeze headlines, and one of them sold the lid.

Nothing was wrong with the store. The rule was never a memory: it belongs to this conversation only, and `write_rules.md` rightly keeps it out. It was lost the way long conversations lose things. You build a summary and the rules that must survive it; at the end, Friday's headlines leave the lid out.

### Maya's week

Eight messages, sent one after another **in one conversation**:

1. For this whole Breeze conversation: never mention the lid. The lid is changing before launch.
2. What are hikers talking about this week?
3. Which of our placements does the web banner go on?
4. Remind me what the Breeze colourway looks like.
5. What did we say about posting days?
6. Give me three moods for the Breeze shoot.
7. Which competitor launches should we watch this month?
8. Write three Breeze headlines.

### Break it first

On the chat page, sign in as Maya at Harbor, press **New conversation**, leave **Model** empty, and send the eight messages in order.

Or send the week from the terminal, as one new conversation. It prints each reply's first line, and saves the conversation for the chat page, where you can open it:

```
uv run launchkit replay harbor samples/sessions/breeze_week.txt
```

**What to look for:**

- **The headlines in reply to message 8:** check them for the lid. By then the window carries turns 3 to 7 only, and the rule was turn 1.
- **The real model may keep the rule anyway**, for example because a later reply repeated it and that reply is still in the window. Note what happened, and how often, across the room.

### What changes, and why

The same three levers, all shown on the same conversation:

1. **Sliding window:** keep the last N turns and drop the rest. Since Session 2 this is `add_history_to_context=True` with `num_history_runs=5`. The lid rule is turn 1 of 8, so by turn 8 it has dropped out of the window.
2. **Summarise:** replace what dropped with a summary of it, using `enable_session_summaries=True`.
    - In Agno 3.1.3 a summary is written by a model call **after every run**, not when the conversation passes a size.
    - Agno's own documentation warns that a summary can leave details out or get them wrong.
    - The size-triggered lever in Agno is a different one: `compress_tool_results` with `CompressionManager(compress_token_limit=…)`, which shortens big tool results once the prompt passes a token count. Not built here.
3. **Hybrid:** run both, and re-state the rules that have to survive instead of trusting them to the summary. `must_keep` picks them out of what Maya said in this conversation, in plain code, and the prompt carries them every turn.

### Prompt card, for your coding agent

```
2. In launchkit/agents/main_agent.py, build_main_agent: add enable_session_summaries=True to the
   Agent(...) call, next to num_history_runs. Change nothing else.

3. In launchkit/memory/compaction.py, build must_keep(said): remove @todo and the raise. said is
   every message the marketer sent in this conversation, oldest first. Split each message into
   sentences (after . ! or ?). Keep a sentence when it states a rule: it contains one of the words
   never, always, don't, do not, must, only (whole words, any case), and it is not a question.
   Return the kept sentences in order, each once. Plain code, no model call.
```

**After item 2 alone:**

1. Reload the browser tab, press **New conversation** and send the week again (or replay it).
2. Read the summary Agno wrote, in the terminal or in `agno_sessions` in SQLite Viewer:

```
uv run launchkit store agno_sessions --user maya   # the summary column, one row per conversation
```

The summary is in the prompt now. Is the lid rule in it? Then do item 3.

### Run it again

Reload the browser tab, press **New conversation** and send the week once more (or replay it).

**What to look for:**

- **The headlines in reply to message 8:** the lid is left out. The rule is re-stated in the prompt on every turn, under `# This conversation so far`, from what Maya typed.

## Prove it

```
uv run launchkit check mem2
```

The check runs offline on a scripted model, so it gives everyone the same result. Part A's four pass once `index.py` is built; Part B's three once both of its items are. Neither part needs the other.

- Part A: the index has one line per topic, each under the line cap, each naming the recall call for its topic.
- Part A: `recall("photography")` returns every photography fact, in full, and nothing from another topic.
- Part A: with a month of rows, the prompt carries the index, not every row: the memory section is the index, and smaller.
- Part A: Breeze, with a month of rows: the agent recalls the photography topic once, then asks for Harbor's photo.
- Part B: with session summaries on, the week has a summary, and the prompt's conversation section carries it.
- Part B: `must_keep` picks out the rule Maya stated in the week, and none of her questions.
- Part B: the summary leaves the lid rule out, the window has dropped it, and the headlines still never mention the lid.

## Why it matters

The index is code, not a model: it is exact, it costs nothing, and it cannot make up a summary of a fact. Retrieval could also be a keyword match or an embedding search. We use the cheapest one that works, and nothing in Harbor's store would be found any better by embeddings.

Compaction manages one conversation's budget, and it is a different job from memory. A summary is a model's guess at what mattered. A rule that must survive gets re-stated by code, every turn, from what Maya actually typed. And the rule still did not go into the store: "this whole Breeze conversation" ends with the conversation.

## See it

- **After Part A:** the trainer runs the Breeze message with the seeded month, before and after, and reads the two Context-tab numbers to the room.
- **Between the parts:** the trainer previews Agno's one pruning lever on the seeded month, and looks for a fact that did not survive the merge:

```
uv run launchkit optimize harbor --user maya            # a preview: the rows before and after, nothing written
uv run launchkit optimize harbor --user maya --apply    # writes the merged rows over the old ones; there is no undo
```

## If the real model is not available

Type `fake:memory` in **Model**, or add `--model fake:memory` to `replay`. Every step on this card works, with scripted replies.

- **Part A, on the seeded month:** 455 tokens of memory before; 210 after, plus 67 tokens from its one `recall("photography")`.
- **Part B:** the fake's summary reads: "Maya is preparing the Breeze launch: trends, placements, the colourway, posting days, shoot moods and competitors." Its first headline is "A lid that never leaks." before `must_keep`, and "Cold from trail to train." after.

## The answer

There is no later branch for this hands-on.

```
# launchkit/memory/index.py: remove def todo, and the @todo and raise on each slot
def memory_index(rows: list[UserMemory]) -> str:
    if not rows:
        return ""
    by_topic: dict[str, list[UserMemory]] = {}
    for row in rows:
        by_topic.setdefault(topic_of(row), []).append(row)
    lines = []
    for topic, kept in by_topic.items():
        line = f'- {topic}: {len(kept)} {"fact" if len(kept) == 1 else "facts"} · recall("{topic}")'
        lines.append(line if len(line) <= LINE_CAP else line[: LINE_CAP - 1] + "…")
    return INDEX_HEADER + "\n" + "\n".join(lines)


def recall(rows: list[UserMemory], topic: str) -> str:
    found = [row for row in rows if topic_of(row) == topic.strip().lower()]
    if not found:
        return f'Nothing kept under "{topic}". Topics: ' + ", ".join(sorted({topic_of(row) for row in rows}))
    return "\n".join(f"- {row.memory} ({kind_of(row) or 'no kind'})" for row in found)
```

Add `from launchkit.memory.long_term import kind_of, topic_of` at the top of `index.py`.

```
# launchkit/agents/main_agent.py, in the Agent(...) call
        num_history_runs=5,
        enable_session_summaries=True,
```

```
# launchkit/memory/compaction.py: remove def todo, and the @todo and raise on must_keep
RULE_WORDS = re.compile(r"\b(never|always|don't|do not|must|only)\b", re.I)


def must_keep(said: list[str]) -> list[str]:
    rules = []
    for message in said:
        for sentence in re.split(r"(?<=[.!?])\s+", message.strip()):
            if RULE_WORDS.search(sentence) and not sentence.endswith("?") and sentence not in rules:
                rules.append(sentence)
    return rules
```

Add `import re` at the top of `compaction.py`.
