# Hands-on: what LangGraph adds around the LLM call

Branch `session-01-langgraph` · you edit one file, `approach_graph/graph.py` · **7 minutes in the session**; the rest is for afterwards

Keep `LAUNCHKIT_IMAGES=placeholder` in `.env`, as for the LLM call.

One LLM call got R1 right and nothing else. This branch starts from that solved call (`write` reuses its prompt) and puts a graph around it. Each TODO closes one gap:

```
START -> route --"write"--> write -> check --"ok"-----> picture -> END
           |                  ^        |
           |                  +-retry--+--"fail"--> give_up -> END
           +--"resize"--> resize -> END
```

## In the session (7 minutes)

Paste each snippet, then run the scoreboard:

```bash
uv run python -m launchkit.scoreboard --approach graph
```

It starts at **1/4**, the same as last session, and goes up by one with each of TODOs 1 to 3.

**TODO 1: remember the last poster (R2, follow-up edits).** A checkpointer saves the state after every request, per conversation. Replace the `GRAPH = build_graph()` line with:

```python
GRAPH = build_graph(checkpointer=MemorySaver())
```

Remembering isn't enough: the model has to see the poster too. In `write`, under `# TODO 1 (part b)`, add:

```python
    if state.get("last_spec"):
        messages[0]["content"] += ("\n\nThe poster so far. Change only what the request asks for and keep "
                                   "everything else word for word:\n" + json.dumps(state["last_spec"].to_dict()))
```

Scoreboard: **2/4.**

**TODO 2: use the photo (R3).** The photo has been in the state all along; the image step just never used it. In `picture`, replace `photo = None` with:

```python
    photo = state["attachments"][0] if state["attachments"] else None
```

Scoreboard: **3/4.**

**TODO 3: route resize-only requests (R4).** "Story size of that poster" needs the poster we have, resized, with no new image. The `resize` node and its edge exist, but `route` always says `"write"`. Paste over `route`:

```python
def route(state: State) -> dict:
    """TODO 3: decide what this request needs: a new or edited poster ("write"), or only new sizes ("resize")."""
    if not state.get("last_picture"):
        return {"route": "write"}  # nothing to resize yet
    answer = complete([
        {"role": "system", "content": "The user already has a poster. Answer two questions about their request, "
                                      "each with yes or no, as: changes=<yes|no> sizes=<yes|no>\n"
                                      "changes: does it ask to change anything about the poster: words, picture, "
                                      "colours, mood, layout?\n"
                                      "sizes: does it ask for the poster in other sizes or placements "
                                      "(story, banner, square, every size, any dimensions)?"},
        {"role": "user", "content": state["request"]},
    ], temperature=0).lower().replace(" ", "")
    only_sizes = "sizes=yes" in answer and "changes=no" in answer
    return {"route": "resize" if only_sizes else "write"}
```

Scoreboard: **4/4.** R4 makes one small model call (the router) and no image call; its five images say *resized by code*.

**TODO 4: check the claims, loop until they're right ("reliably").** Last session's festival brief got ✓ from the rules check yet claimed "Ready for any drop". Give `check` a reviewer, a second model call that checks each claim against Harbor's facts. Paste over `review_claims`:

```python
def review_claims(spec: PosterSpec, brand: dict) -> list[str]:
    """TODO 4: a second model call checks every claim in the copy against the brand's facts."""
    reply = complete([
        {"role": "system", "content": f"You check ad copy for {brand['name']}'s {brand['product']} against its "
                                      "approved facts. For each sentence or phrase of the copy, write one line: "
                                      "<phrase> => OK or UNSUPPORTED. UNSUPPORTED means it says or hints that the "
                                      "product does, survives or is made of something no fact states. A fact in other "
                                      "words is OK (\"cold all day\" is backed by \"cold for 24 hours\"); the "
                                      "product's name, mood, setting and look are OK.\nFacts:\n- "
                                      + "\n- ".join(brand["facts"])},
        {"role": "user", "content": f"{spec.headline}\n{spec.subheadline}\n{spec.body}"},
    ], temperature=0)
    return [f"not in {brand['name']}'s facts: {line.split('=>')[0].strip(' -*')}"
            for line in reply.splitlines() if "UNSUPPORTED" in line.upper()]
```

Run the festival brief once:

```bash
uv run python -m launchkit.ask --approach graph "Summer festival poster: the Tidal bottle survives being dropped on concrete and keeps water ice cold all day."
```

**Look for:** a reviewer reply with `=> UNSUPPORTED`, then another `write` call carrying "Fix these problems", then a clean poster. The loop was in the graph from the start; it just had nothing to catch. (It doesn't trigger on every run.)

**The graph doesn't make the model smarter. It decides what runs, remembers what happened and loops until a check passes.**

## After the session

**The four ideas.** *State*: one dict every node reads and adds to (`State` in `graph.py`). *Node*: a plain Python function that returns the fields it changes. *Edge*: what runs next; a conditional edge picks from the state, like `check` → `picture` or back to `write`. *Checkpointer*: saves the state per conversation (`thread_id` in `handle`). The model never decides what runs next; the graph does.

**Try a conversation in the browser.** Memory lives inside one running program, so separate `ask` commands don't remember each other. Run `uv run python -m launchkit.ui` (http://localhost:8000), pick *LangGraph* under *Approach*, then click R1, *Make poster*, R2, *Make poster*: R2's system message ends with the first poster. Saving `graph.py` reloads it and resets that memory, so run R1 again after an edit.

**Why does the router ask two questions?** Asked one question ("is this only a resize?"), the model kept getting some requests wrong: missing "Can I get this as a web banner too?", or sending "Story size, and make the lake moodier" to `resize`. With two yes/no questions and code combining the answers, it got all 9 test requests right, 4 times each. Let the model answer small questions; let code make the decision.

**What checks the checker?** In our dry run the festival brief made a drop claim in 4 of 5 posters before TODO 4 and 0 of 8 after; half of them needed the loop. But the reviewer is an LLM too: on a test set it never flagged good copy, yet let 3 of 12 bad claims through, mostly hinted ones. A person still signs off on what ships.

**Stretch.**
- *Edits keep the picture.* R2 only changed the headline, yet `picture` made a new image. Add a route for copy-only edits that reuses `last_picture`.
- *Memory that survives a restart.* `MemorySaver` forgets when the program stops; LangGraph has database-backed checkpointers (such as `SqliteSaver` in `langgraph-checkpoint-sqlite`).
- *Count the cost of one new kind of request.* R4 needed a node, an edge and a router prompt. Now imagine every kind of request Harbor will send. That's where the next session starts.

| Problem | One LLM call | LangGraph |
| --- | --- | --- |
| follow-up edits (R2) | starts from nothing every time | a checkpointer keeps the state per conversation |
| a photo (R3) | had no step to hand it on | the state carries it to the node that needs it |
| resize "that poster" (R4) | made a new poster | a router node; the resize path has no model at all |
| "reliably" | nothing noticed bad claims | a review node and a loop back to `write` |

Next: `git checkout session-01-harness`
