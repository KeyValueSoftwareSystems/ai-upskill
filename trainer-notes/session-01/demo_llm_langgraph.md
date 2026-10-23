# Opener demo: one AI call, then LangGraph

Branches `session-01-llm-call` → `session-01-langgraph` (both solved: `session-01-llm-langgraph-solution`) · steps 2 and 3 of the session story

**This is a trainer demo.** The trainer runs it live and the room watches the scoreboard move. Use the hands-on only if the room needs it and there is time: trainees paste the same snippets on the same branches. To demo without pasting, run everything from `session-01-llm-langgraph-solution`.

Before the session, add `LAUNCHKIT_IMAGES=placeholder` to `.env`. A real image takes about a minute; show real ones from a run done earlier.

Maya, Harbor's marketer, asked: *why don't we just use ChatGPT?* So we start where ChatGPT starts: one call to a model. Every step is scored on Maya's four requests, sent in order in one conversation:

| | Maya says | Needs |
| --- | --- | --- |
| R1 | Tidal launch, a misty lakeshore at dawn. Can I get a concept, a storyboard, the words and a poster? | a full poster from one idea |
| R2 | Love it. Just the story size now, please. | keep my picture |
| R3 | What does your brand book say about washing the lid? | an answer, not a new poster |
| R4 | Is the lid dishwasher-safe? If not, fix the copy, then give me the story size. | three asks in one message |

Score each step with:

```bash
uv run python -m launchkit.scoreboard --approach llm      # part 1
uv run python -m launchkit.scoreboard --approach graph    # part 2
```

## Part 1 · One AI call (`session-01-llm-call`, `approach_llm/app.py`)

**Start: 0/4.** Harbor's rules are in the prompt, yet R1 says `not a form: no JSON object in the model's reply`. Show it with `uv run python -m launchkit.ask R1`: the reply is a chat answer that makes up a tagline and ends with a question. People can read it; code can't use it.

**TODO 1: give the answer a shape.** Can't a better prompt fix this? Yes. Paste over `build_prompt`:

```python
def build_prompt(keys: dict, brand: dict) -> str:
    """The system message: Harbor's rules, and the shape of answer we need."""
    shape = "\n".join(f"- {key}: {what}" for key, what in keys.items())
    return (f"You write poster ads.\n{brand_rules_text(brand)}\n"
            f"Reply with ONLY a JSON object with these keys, and nothing else:\n{shape}")
```

Scoreboard: **1/4.** The one call now fills in the whole form.

**TODO 2: split the job into four calls.** Concept, storyboard, words and poster, each with Harbor's rules and its own fixed shape. Earlier messages go with each call, so the picture and the words carry on together. Paste over `write`:

```python
def write(text: str, brand: dict) -> PosterSpec:
    """The model's part: Maya's brief in, the filled-in form out."""
    messages, form = [{"role": "user", "content": text}], {}
    for stage, keys in STAGES.items():
        messages.append({"role": "user", "content": f"Now the {stage}."})
        reply = complete([{"role": "system", "content": build_prompt(keys, brand)}] + messages)
        form.update(parse_json(reply))
        messages.append({"role": "assistant", "content": reply})  # the next call sees this one
    return PosterSpec.from_dict(form)
```

Scoreboard: **still 1/4**, but `ask R1` now shows four short calls. Maya gets four pieces: the concept (something like "A serene, misty lakeshore at dawn"), three storyboard frames, the words (such as "Cold for 24 Hours") and the poster.

**Read the reasons under R2 to R4.** R2: **it drew a new one.** The code runs every step every time, so a new bottle on new rocks comes back; she loses the poster she approved and pays for a picture she never asked for. R3: she asked a question and got a new poster. R4: three asks, and the code knows one way to answer.

**Ask the room: one `if` per request?** "Just the story size" → resize only; "make the headline shorter" → words only; "use our own photo" → skip the picture; "show me three options" → three pictures; "go back to the first one" → reload the old poster. And "story size, and a shorter headline"? No rule at all. Why not draw every path ahead of time?

## Part 2 · LangGraph (`session-01-langgraph`, `approach_graph/graph.py`)

LangGraph draws the map ahead of time: a router picks a path, and a saved state keeps what Maya approved. The branch starts with part 1 solved and puts a graph around `write`:

```
START -> route --"poster"--> write -> picture -> END    (the four shaped calls, then the image model)
           |----"resize"--> resize -> END             (no model: the saved picture, resized by code)
           +----"answer"--> answer -> END             (TODO 3)
```

**Start: 1/4**, the same as part 1.

**TODO 1: a saved state.** A checkpointer saves the state after every request, per conversation, so the next request can see the picture and words Maya approved. Replace the `GRAPH = build_graph()` line with:

```python
GRAPH = build_graph(checkpointer=MemorySaver())
```

Still 1/4: the graph remembers the picture, but the router sends every message to `write`.

**TODO 2: the router.** The `resize` node and its edge exist, but `route` always says `"poster"`. Paste over `route`:

```python
def route(state: State) -> dict:
    """Decide which path this request takes: a new or edited poster, or only new sizes of the saved picture."""
    if not state.get("last_picture"):
        return {"route": "poster"}  # nothing saved yet, so nothing to resize
    said = yes_no(state["request"], ["changes", "sizes"])
    return {"route": "resize" if said["sizes"] and not said["changes"] else "poster"}
```

Scoreboard: **2/4.** R2 makes one small model call (the router) and no image call; its picture says *resized by code*.

**Ask the room: R3 fails.** The lid question goes to `write`: she gets a new poster with a new picture. How do we fix it?

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

**R4 still fails, by design.** The router can pick only one path. Two of Maya's asks vanish, and nobody tells her. **Ask the room: how many paths for 10 kinds of request, and every mix of them?** Then: can't the AI pick the steps itself? That's where step 3 starts.

**The graph doesn't make the model smarter. It decides what runs and remembers what happened, but only along the paths someone drew.**

## Showing it in the browser

`uv run python -m launchkit.ui` opens http://localhost:8000. Pick the approach under *Approach* (*LangGraph* for part 2), then send R1 to R4 in order. Memory lives inside one running program, so separate `ask` commands don't remember each other, and restarting the UI, saving `graph.py` or reloading the page starts over from R1.

## After the session

**Are the answers the same each run?** No. Run `ask R1` three times and compare the headlines. Step 7 shows how we trust it anyway: check it in code, and keep a trace.

**The four LangGraph ideas.** *State*: one dict every node reads and adds to (`State` in `graph.py`). *Node*: a plain Python function that returns the fields it changes. *Edge*: what runs next; a conditional edge picks from the state, like `route` → `resize`. *Checkpointer*: saves the state per conversation (`thread_id` in `handle`). LangGraph also gives a save point after each step, a pause for Maya's approval, and a trace for each step. The model never decides what runs next; the graph does.

**Why small yes/no questions for the router?** Asked one question ("which path?"), a model is easy to tip over: "Can I get this as a web banner too?" or "Story size, and make the lake moodier". Small yes/no questions, with code combining the answers, are steadier. Let the model answer small questions; let code make the decision.

**Why did Pencil never use LangGraph?** Every path is mapped in advance. Pencil's users' work can't be written down as a fixed map.

**Stretch.**
- *"Show me three options."* Add a path that draws three pictures. Count what it took: a node, an edge, a router question, and a decision rule that must not break the others.
- *Memory that survives a restart.* `MemorySaver` forgets when the program stops; LangGraph has database-backed checkpointers (such as `SqliteSaver` in `langgraph-checkpoint-sqlite`).
- *Make R4 pass.* Add a path for "answer, then fix the copy, then resize". Now try "story size, and a shorter headline".

| Maya needs | One AI call | LangGraph |
| --- | --- | --- |
| a full poster from one idea (R1) | yes, once the answer has a shape | the same four calls |
| keep my picture (R2) | ran every step, so a new picture | a saved state and a router; the resize path has no model at all |
| an answer, not a new poster (R3) | made a poster | one more path: a node, an edge and a router question |
| three asks in one message (R4) | one way to answer | the router picks one path; two asks vanish |

Next: `git checkout session-01-harness`
