"""Draw the map: a router picks a path, and the graph saves what Maya approved.

    START -> route --"poster"--> write -> picture -> END    (the four shaped calls, then the image model)
               |----"resize"--> resize -> END             (no model: the saved picture, resized by code)
               +----"answer"--> answer -> END             (a question gets an answer in words)

Each box is a node: a plain Python function that reads the state and returns the fields it changes.
The arrows are edges. The graph, not the model, decides what runs next.

Solved: all three TODOs from the LangGraph hands-on are filled in. Score it:
    uv run python -m launchkit.scoreboard --approach graph
R4 (three asks in one message) still fails, by design: the router picks one path.
"""
import json
import os
import re

# Only load back the types State declares below (LangGraph's future default); set before importing it.
os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from approach_llm.app import write as write_poster  # last step's four shaped calls, reused as is
from launchkit.images import generate_image, resize_image
from launchkit.llm import complete
from launchkit.poster import Picture, PosterSpec, Result, SpecError, load_brand


class State(TypedDict, total=False):
    # this request
    request: str
    workspace: str
    conversation_id: str
    brand: dict
    # worked out while handling it
    route: str
    spec: PosterSpec | None
    images: list[Picture]
    answer: str | None
    error: str | None
    # saved from one request to the next (only once the graph has a checkpointer)
    last_spec: PosterSpec | None
    last_picture: Picture | None


# ---- the router

# Small yes/no questions the router can ask about Maya's message. The model answers them; code decides.
QUESTIONS = {
    "changes": "does it ask to change anything about the poster: words, picture, colours, mood, layout?",
    "sizes": "does it ask for the poster in other sizes or placements (story, banner, square, every size, "
             "any dimensions)?",
    "question": "does it ask a question that wants an answer in words, about the product, the brand or its rules "
                "(not a request to make, change or resize something)?",
}


def yes_no(request: str, names: list[str]) -> dict[str, bool]:
    """One small model call: answer the named QUESTIONS about Maya's message with yes or no."""
    reply = complete([
        {"role": "system", "content": "Maya is a marketer working on a poster. Answer each question about her "
                                      "message with yes or no, as: " + " ".join(f"{n}=<yes|no>" for n in names)
                                      + "\n" + "\n".join(f"{n}: {QUESTIONS[n]}" for n in names)},
        {"role": "user", "content": request},
    ], temperature=0).lower().replace(" ", "")
    return {n: f"{n}=yes" in reply for n in names}


def route(state: State) -> dict:
    """Solved TODOs 2 and 3: decide which path this request takes: a new or edited poster ("poster"),
    only new sizes of the saved picture ("resize"), or an answer in words ("answer")."""
    if not state.get("last_picture"):
        return {"route": "poster"}  # nothing saved yet, so make the poster first
    said = yes_no(state["request"], ["changes", "sizes", "question"])
    if said["question"] and not said["changes"] and not said["sizes"]:
        return {"route": "answer"}
    if said["sizes"] and not said["changes"] and not said["question"]:
        return {"route": "resize"}
    return {"route": "poster"}  # a new poster, an edit, or a mix of asks: one path only


# ---- nodes

def write(state: State) -> dict:
    """Write the poster: the four shaped calls (concept, storyboard, words, poster) from approach_llm."""
    text = state["request"]
    if state.get("last_spec"):  # an edit: show the model the poster so far
        text = ("The poster so far:\n" + json.dumps(state["last_spec"].to_dict()) + "\n\n"
                "Change only what this message asks for and keep everything else word for word:\n" + text)
    try:
        return {"spec": write_poster(text, state["brand"])}
    except SpecError as e:
        return {"error": f"not a form: {e}"}


def picture(state: State) -> dict:
    """The image model makes the picture. The graph saves it, with the words, as the approved poster."""
    spec = state["spec"]
    pic = generate_image(spec.visual_concept, state["brand"], conversation_id=state["conversation_id"])
    return {"images": [pic], "last_spec": spec, "last_picture": pic}


def resize(state: State) -> dict:
    """No model at all: the saved picture, resized by code to the sizes Maya named (or every size)."""
    placements = state["brand"]["placements"]
    words = set(re.findall(r"[a-z]+", state["request"].lower()))
    named = {name: size for name, size in placements.items() if words & set(name.split("_"))}
    sizes = [resize_image(state["last_picture"], tuple(size), conversation_id=state["conversation_id"])
             for size in (named or placements).values()]
    return {"spec": state["last_spec"], "images": sizes}


def answer(state: State) -> dict:
    """Solved TODO 3: a question gets an answer in words, from Harbor's facts. No poster, no picture."""
    brand = state["brand"]
    reply = complete([
        {"role": "system", "content": f"You answer questions about {brand['name']}'s {brand['product']} in one or "
                                      "two short sentences, using only these facts. If they don't say, say so.\n"
                                      "Facts:\n- " + "\n- ".join(brand["facts"])},
        {"role": "user", "content": state["request"]},
    ], temperature=0)
    return {"answer": reply}


# ---- edges: what runs after what

def build_graph(checkpointer=None):
    g = StateGraph(State)
    g.add_node("route", route)
    g.add_node("write", write)
    g.add_node("picture", picture)
    g.add_node("resize", resize)
    paths = {"poster": "write", "resize": "resize"}  # route's answer -> the node it leads to
    # Solved TODO 3: the answer path. Every new kind of request needs a node, an edge and a router question.
    g.add_node("answer", answer)
    g.add_edge("answer", END)
    paths["answer"] = "answer"

    g.add_edge(START, "route")
    g.add_conditional_edges("route", lambda state: state["route"], paths)
    g.add_conditional_edges("write", lambda state: "picture" if state["spec"] else "end",
                            {"picture": "picture", "end": END})
    g.add_edge("picture", END)
    g.add_edge("resize", END)
    return g.compile(checkpointer=checkpointer)


# Solved TODO 1: a saved state. A checkpointer saves the state after every request, per conversation
# (the thread_id below), so the next request can see the picture and words Maya approved.
GRAPH = build_graph(checkpointer=MemorySaver())


def handle(text: str, *, workspace: str, conversation_id: str) -> Result:
    """Run one request through the graph. Used by `ask`, the UI and the scoreboard."""
    out = GRAPH.invoke(
        {"request": text, "workspace": workspace, "conversation_id": conversation_id,
         "brand": load_brand(workspace),
         # a clean slate for this request; last_spec and last_picture are left as they were
         "route": "", "spec": None, "images": [], "answer": None, "error": None},
        config={"configurable": {"thread_id": conversation_id}},
    )
    if out["error"]:
        return Result(error=out["error"])
    return Result(spec=out["spec"], images=out["images"], answer=out["answer"])
