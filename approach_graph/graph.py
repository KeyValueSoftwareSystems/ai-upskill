"""A LangGraph pipeline: last session's LLM call, with memory, a router and a review loop around it.

    START -> route --"write"--> write -> check --"ok"-----> picture -> END
               |                  ^        |
               |                  +-retry--+--"fail"--> give_up -> END
               +--"resize"--> resize -> END

Each box is a node: a plain Python function that reads the state and returns the fields it changes.
The arrows are edges. The graph, not the model, decides what runs next.

Solved: all four TODOs from the LangGraph hands-on are filled in. Score it:
    uv run python -m launchkit.scoreboard --approach graph
"""
import json
import os

# Only load back the types State declares below (LangGraph's future default); set before importing it.
os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from langgraph.checkpoint.memory import MemorySaver
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
    """Solved TODO 3: decide what this request needs: a new or edited poster ("write"), or only new sizes ("resize")."""
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


def write(state: State) -> dict:
    """Last session's LLM call: Harbor's rules in the prompt, a JSON poster back."""
    messages = build_prompt(state["request"], state["brand"])
    # Solved TODO 1 (part b): show the model the poster we're working on, so it can edit it.
    if state.get("last_spec"):
        messages[0]["content"] += ("\n\nThe poster so far. Change only what the request asks for and keep "
                                   "everything else word for word:\n" + json.dumps(state["last_spec"].to_dict()))
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
    problems += review_claims(spec, state["brand"])  # Solved TODO 4: the rules we can't write down
    return {"spec": spec, "problems": problems}


def review_claims(spec: PosterSpec, brand: dict) -> list[str]:
    """Solved TODO 4: a second model call checks every claim in the copy against the brand's facts."""
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


def picture(state: State) -> dict:
    """The image model makes the picture. Placement sizes come from the resize route, when asked for."""
    spec, brand, conv = state["spec"], state["brand"], state["conversation_id"]
    # Solved TODO 2: start from the uploaded photo, if there is one.
    photo = state["attachments"][0] if state["attachments"] else None
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


# Solved TODO 1 (part a): give the graph a memory. A checkpointer saves the state after every request,
# per conversation (the thread_id below), so the next request in that conversation starts from it.
GRAPH = build_graph(checkpointer=MemorySaver())


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
