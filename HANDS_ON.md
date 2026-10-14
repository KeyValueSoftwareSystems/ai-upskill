# Hands-on: a LangGraph pipeline

Branch `session-01-langgraph` · file `approach_graph/graph.py` · about 3 minutes

This branch already contains the solved LLM call. Paste each snippet into `approach_graph/graph.py`, then run:

```bash
uv run python -m launchkit.scoreboard --approach graph
```

```
START -> start_turn -> write_spec -> validate --ok--> generate_image -> END
                           ^            |
                           +--retry-----+--fail--> give_up -> END
```

## TODO 1: validate node

Solves: each reply must be checked before the graph moves on.

```python
def validate(state: State) -> dict:
    """TODO 1: Parse the reply and validate it. Store the spec and any problems."""
    try:
        spec = parse_spec(state["raw"])
    except SpecError as e:
        return {"spec": None, "problems": [str(e)]}
    return {"spec": spec.to_dict(), "problems": validate_spec(spec, state["brand"])}
```

## TODO 2: route after validate

Solves: a bad reply gets one repair, through a loop the graph controls, instead of failing outright.

```python
def route_after_validate(state: State) -> str:
    """TODO 2: Decide where to go after validate: "ok", "retry" or "fail"."""
    if not state["problems"]:
        return "ok"
    return "retry" if state["attempts"] < MAX_ATTEMPTS else "fail"
```

## TODO 3a: save state between turns

Solves: without a checkpointer, every request starts from nothing. Replace the `GRAPH = ...` line with:

```python
GRAPH = build_graph(checkpointer=MemorySaver())
```

## TODO 3b: use the saved state

Solves: saved state does nothing until the prompt uses it. In `write_spec`, replace the TODO 3 comment with:

```python
    if state.get("last_spec"):
        system += "\nPrevious poster spec (edit this one if the user asks for changes):\n" + json.dumps(state["last_spec"])
```

## TODO 4 (stretch): a resize branch

Solves: a resize-only request should resize the existing poster, not generate a new one. Replace the two stubs with:

```python
def route_request(state: State) -> str:
    """TODO 4 (stretch): send resize-only requests to resize_last instead of write_spec."""
    text = state["request"].lower()
    wants_resize = "story size" in text or "1080x1920" in text or "resize" in text
    return "resize" if wants_resize and state.get("last_image") else "write"


def resize_last(state: State) -> dict:
    """TODO 4 (stretch): resize the previous poster to the story size, no model call."""
    image = resize_image(state["last_image"], (1080, 1920), conversation_id=state["conversation_id"])
    return {"image": image, "spec": state["last_spec"]}
```

Then in `build_graph`, add the node and swap the `start_turn -> write_spec` edge for a routed one:

```python
    g.add_node("resize_last", resize_last)
    g.add_conditional_edges("start_turn", route_request, {"write": "write_spec", "resize": "resize_last"})
    g.add_edge("resize_last", END)
```

Count what one new kind of request cost you. Now imagine every request type Harbor will send.
