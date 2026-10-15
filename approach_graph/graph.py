"""A LangGraph pipeline: last session's LLM call, with memory, a router and a review loop around it.

    START -> route --"write"--> write -> check --"ok"-----> picture -> END
               |                  ^        |
               |                  +-retry--+--"fail"--> give_up -> END
               +--"resize"--> resize -> END

Each box is a node: a plain Python function that reads the state and returns the fields it changes.
The arrows are edges. The graph, not the model, decides what runs next.

You fill in four TODOs (HANDS_ON.md has the code). After each one, score it:
    uv run python -m launchkit.scoreboard --approach graph
"""
import json  # noqa: F401  (TODO 1)
import os

# Only load back the types State declares below (LangGraph's future default); set before importing it.
os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from langgraph.checkpoint.memory import MemorySaver  # noqa: F401  (TODO 1)
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from approach_llm.app import build_prompt  # last session's prompt, reused as is
from launchkit.images import generate_image, resize_image
from launchkit.llm import complete
from launchkit.poster import Picture, PosterSpec, Result, SpecError, load_brand, parse_spec, validate_spec

MAX_ATTEMPTS = 2  # the first try, then one fix


class State(TypedDict, total=False):
    # this request
    request: str
    attachments: list[str]
    workspace: str
    conversation_id: str
    brand: dict
    # worked out while handling it
    route: str
    reply: str
    spec: PosterSpec | None
    problems: list[str]
    attempts: int
    images: list[Picture]
    error: str | None
    # remembered from one request to the next (only once the graph has a checkpointer)
    last_spec: PosterSpec | None
    last_picture: Picture | None


# ---- nodes

def route(state: State) -> dict:
    """TODO 3: decide what this request needs: a new or edited poster ("write"), or only new sizes ("resize")."""
    return {"route": "write"}


def write(state: State) -> dict:
    """Last session's LLM call: Harbor's rules in the prompt, a JSON poster back."""
    messages = build_prompt(state["request"], state["brand"])
    # TODO 1 (part b): show the model the poster we're working on, so it can edit it.
    if state.get("problems"):  # we're back here from check: show the model what was wrong
        messages += [
            {"role": "assistant", "content": state["reply"]},
            {"role": "user", "content": "Fix these problems and reply with only the corrected JSON:\n- "
                                        + "\n- ".join(state["problems"])},
        ]
    return {"reply": complete(messages), "attempts": state["attempts"] + 1}


def check(state: State) -> dict:
    """Turn the reply into a poster spec and list anything wrong with it."""
    try:
        spec = parse_spec(state["reply"])
    except SpecError as e:
        return {"spec": None, "problems": [str(e)]}
    problems = validate_spec(spec, state["brand"])  # the written rules: word limits, banned words
    problems += review_claims(spec, state["brand"])  # TODO 4: the rules we can't write down
    return {"spec": spec, "problems": problems}


def review_claims(spec: PosterSpec, brand: dict) -> list[str]:
    """TODO 4: a second model call checks every claim in the copy against the brand's facts."""
    return []


def picture(state: State) -> dict:
    """The image model makes the picture. Placement sizes come from the resize route, when asked for."""
    spec, brand, conv = state["spec"], state["brand"], state["conversation_id"]
    # TODO 2: start from the uploaded photo, if there is one.
    photo = None
    pic = generate_image(spec.visual_concept, brand, conversation_id=conv, reference=photo)
    return {"images": [pic], "last_spec": spec, "last_picture": pic}


def resize(state: State) -> dict:
    """No model at all: the poster we already made, in every placement size."""
    pic, conv = state["last_picture"], state["conversation_id"]
    sizes = [resize_image(pic, tuple(size), conversation_id=conv) for size in state["brand"]["placements"].values()]
    return {"spec": state["last_spec"], "images": sizes}


def give_up(state: State) -> dict:
    return {"error": f"still not right after {state['attempts']} tries: " + "; ".join(state["problems"])}


# ---- edges: what runs after what

def after_check(state: State) -> str:
    if not state["problems"]:
        return "ok"
    return "retry" if state["attempts"] < MAX_ATTEMPTS else "fail"


def build_graph(checkpointer=None):
    g = StateGraph(State)
    g.add_node("route", route)
    g.add_node("write", write)
    g.add_node("check", check)
    g.add_node("picture", picture)
    g.add_node("resize", resize)
    g.add_node("give_up", give_up)

    g.add_edge(START, "route")
    g.add_conditional_edges("route", lambda state: state["route"], {"write": "write", "resize": "resize"})
    g.add_edge("write", "check")
    g.add_conditional_edges("check", after_check, {"ok": "picture", "retry": "write", "fail": "give_up"})
    g.add_edge("picture", END)
    g.add_edge("resize", END)
    g.add_edge("give_up", END)
    return g.compile(checkpointer=checkpointer)


# TODO 1 (part a): give the graph a memory. A checkpointer saves the state after every request,
# per conversation (the thread_id below), so the next request in that conversation starts from it.
GRAPH = build_graph()


def handle(text: str, *, workspace: str, conversation_id: str, attachments: list[str]) -> Result:
    """Run one request through the graph. Used by `ask`, the UI and the scoreboard."""
    out = GRAPH.invoke(
        {"request": text, "attachments": attachments, "workspace": workspace, "conversation_id": conversation_id,
         "brand": load_brand(workspace),
         # a clean slate for this request; last_spec and last_picture are left as they were
         "route": "", "reply": "", "spec": None, "problems": [], "attempts": 0, "images": [], "error": None},
        config={"configurable": {"thread_id": conversation_id}},
    )
    if out["error"]:
        return Result(error=out["error"])
    return Result(spec=out["spec"], images=out["images"])
