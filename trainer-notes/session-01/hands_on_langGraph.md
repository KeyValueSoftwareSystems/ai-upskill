# Hands-on: why not draw every path ahead of time?

Branch `session-01-langgraph` · you edit one file, `approach_graph/graph.py` · **7 minutes in the session**; the rest is for afterwards

Keep `LAUNCHKIT_IMAGES=placeholder` in `.env`, as for the one AI call.

One `if` per request doesn't scale by hand. LangGraph draws the map ahead of time: a router picks a path, and a saved state keeps what Maya approved. This branch starts from the solved four-step `write` and puts a graph around it:

```
START -> route --"poster"--> write -> picture -> END    (the four shaped calls, then the image model)
           |----"resize"--> resize -> END             (no model: the saved picture, resized by code)
           +----"answer"--> answer -> END             (TODO 3)
```

## In the session (7 minutes)

Paste each snippet, then run the scoreboard:

```bash
uv run python -m launchkit.scoreboard --approach graph
```

It starts at **1/4**, the same as the one AI call.

**TODO 1: a saved state.** A checkpointer saves the state after every request, per conversation, so the next request can see the picture and words Maya approved. Replace the `GRAPH = build_graph()` line with:

```python
GRAPH = build_graph(checkpointer=MemorySaver())
```

Still 1/4: the graph remembers the picture, but the router sends every message to `write`.

**TODO 2: the router.** "Just the story size" needs the picture we have, resized, with no new picture. The `resize` node and its edge exist, but `route` always says `"poster"`. Paste over `route`:

```python
def route(state: State) -> dict:
    """Decide which path this request takes: a new or edited poster, or only new sizes of the saved picture."""
    if not state.get("last_picture"):
        return {"route": "poster"}  # nothing saved yet, so nothing to resize
    said = yes_no(state["request"], ["changes", "sizes"])
    return {"route": "resize" if said["sizes"] and not said["changes"] else "poster"}
```

Scoreboard: **2/4.** R2 makes one small model call (the router) and no image call; its picture says *resized by code*.

**Ask the room: R3 fails.** "What does your brand book say about washing the lid?" goes to `write`: she gets a new poster with a new picture. How do we fix it?

**TODO 3: one more path.** A new kind of request needs a node, an edge and a router question. In `build_graph`, uncomment the three lines under `# TODO 3 (part a)`. Then paste over `route`:

```python
def route(state: State) -> dict:
    """Decide which path this request takes: a new or edited poster, only new sizes, or an answer in words."""
    if not state.get("last_picture"):
        return {"route": "poster"}  # nothing saved yet, so make the poster first
    said = yes_no(state["request"], ["changes", "sizes", "question"])
    if said["question"] and not said["changes"] and not said["sizes"]:
        return {"route": "answer"}
    if said["sizes"] and not said["changes"] and not said["question"]:
        return {"route": "resize"}
    return {"route": "poster"}  # a new poster, an edit, or a mix of asks: one path only
```

Scoreboard: **3/4.** R3 gets an answer from Harbor's facts: the lid is hand-wash only.

**R4 still fails, by design.** "Is the lid dishwasher-safe? If not, fix the copy, then give me the story size." The router can pick only one path. Two of Maya's asks vanish, and nobody tells her. **Ask the room: how many paths for 10 kinds of request, and every mix of them?** Then: can't the AI pick the steps itself? That's where step 3 starts.

**The graph doesn't make the model smarter. It decides what runs and remembers what happened, but only along the paths someone drew.**

## After the session

**The four ideas.** *State*: one dict every node reads and adds to (`State` in `graph.py`). *Node*: a plain Python function that returns the fields it changes. *Edge*: what runs next; a conditional edge picks from the state, like `route` → `resize`. *Checkpointer*: saves the state per conversation (`thread_id` in `handle`). LangGraph also gives a save point after each step, a pause for Maya's approval, and a trace for each step. The model never decides what runs next; the graph does.

**Try a conversation in the browser.** Memory lives inside one running program, so separate `ask` commands don't remember each other. Run `uv run python -m launchkit.ui` (http://localhost:8000), pick *LangGraph* under *Approach*, then send R1 to R4 in order. Saving `graph.py` reloads it and resets that memory, so start again from R1 after an edit.

**Why does the router ask small yes/no questions?** Asked one question ("which path?"), a model is easy to tip over: "Can I get this as a web banner too?" or "Story size, and make the lake moodier". Small yes/no questions, with code combining the answers, are steadier. Let the model answer small questions; let code make the decision.

**Why did Pencil never use LangGraph?** Every path is mapped in advance. Pencil's users' work can't be written down as a fixed map.

**Stretch.**
- *"Show me three options."* Add a path that draws three pictures. Count what it took: a node, an edge, a router question, and a decision rule that must not break the others.
- *Memory that survives a restart.* `MemorySaver` forgets when the program stops; LangGraph has database-backed checkpointers (such as `SqliteSaver` in `langgraph-checkpoint-sqlite`).
- *Make R4 pass.* Add a path for "answer, then fix the copy, then resize". Now try "story size, and a shorter headline".

| Maya needs | One AI call | LangGraph |
| --- | --- | --- |
| keep my picture (R2) | ran every step, so a new picture | a saved state and a router; the resize path has no model at all |
| an answer, not a new poster (R3) | made a poster | one more path: a node, an edge and a router question |
| three asks in one message (R4) | one way to answer | the router picks one path; two asks vanish |

Next: `git checkout session-01-harness`
