"""A LangGraph pipeline.

Work through TODO 1 to 3 in order, rerunning the scoreboard after each:
    uv run python -m launchkit.scoreboard --approach graph
TODO 4 is a stretch.

    START -> start_turn -> write_spec -> validate --ok--> generate_image -> END
                               ^            |
                               +--retry-----+--fail--> give_up -> END

The graph gives us structure the plain call didn't have: a validate-and-retry
loop, and (with a checkpointer) state that survives between turns.
"""
import json

from langgraph.checkpoint.memory import MemorySaver  # noqa: F401  (TODO 3)
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from launchkit.brand import brand_rules_text, load_brand
from launchkit.images import generate_image, resize_image  # noqa: F401  (TODO 4)
from launchkit.llm import complete
from launchkit.result import Result
from launchkit.spec import PosterSpec, SpecError, validate_spec

MAX_ATTEMPTS = 2  # the first try plus one repair


class State(TypedDict, total=False):
    # input for this turn
    request: str
    workspace: str
    conversation_id: str
    attachments: list[str]
    # working state for this turn
    brand: dict
    raw: str
    spec: dict | None
    problems: list[str]
    attempts: int
    image: str | None
    error: str | None
    # carried between turns by the checkpointer
    last_spec: dict | None
    last_image: str | None


def start_turn(state: State) -> dict:
    """Reset per-turn fields. Fields a checkpointer keeps (last_*) are left alone."""
    return {"brand": load_brand(state["workspace"]), "raw": "", "spec": None,
            "problems": [], "attempts": 0, "image": None, "error": None}


def write_spec(state: State) -> dict:
    brand = state["brand"]
    system = (
        "You write poster ad specs.\n"
        f"{brand_rules_text(brand)}\n"
        "Reply with ONLY a JSON object with the keys headline, subheadline, body and visual_concept. "
        "visual_concept describes the picture only and must never contain words to be drawn."
    )
    # TODO 3 (part b): if state has a "last_spec", append it to the system message, e.g.
    #   "Previous poster spec (edit this one if the user asks for changes):\n" + json.dumps(...)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": state["request"]}]
    if state.get("problems"):
        messages += [
            {"role": "assistant", "content": state["raw"]},
            {"role": "user", "content": "Fix these problems and reply with only the corrected JSON:\n- " + "\n- ".join(state["problems"])},
        ]
    return {"raw": complete(messages), "attempts": state.get("attempts", 0) + 1}


def parse_spec(raw: str) -> PosterSpec:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise SpecError("no JSON object in the model's reply")
    try:
        return PosterSpec.from_dict(json.loads(raw[start:end + 1]))
    except json.JSONDecodeError as e:
        raise SpecError(f"invalid JSON: {e}") from e


def validate(state: State) -> dict:
    """TODO 1: Parse the reply and validate it. Store the spec and any problems.

    Use parse_spec(state["raw"]) and validate_spec(spec, state["brand"]).
    Return {"spec": spec.to_dict(), "problems": [...]}. If parsing raises
    SpecError, return {"spec": None, "problems": [str(error)]}.
    """
    raise NotImplementedError("TODO 1: validate in approach_graph/graph.py")


def route_after_validate(state: State) -> str:
    """TODO 2: Decide where to go after validate: "ok", "retry" or "fail".

    "ok" when there are no problems; "retry" while state["attempts"] < MAX_ATTEMPTS;
    otherwise "fail". The edges for these three names are already wired in build_graph.
    """
    raise NotImplementedError("TODO 2: route_after_validate in approach_graph/graph.py")


def generate(state: State) -> dict:
    spec = state["spec"]
    image = generate_image(spec["visual_concept"], state["brand"], conversation_id=state["conversation_id"])
    return {"image": image, "last_spec": spec, "last_image": image}


def give_up(state: State) -> dict:
    return {"error": "still invalid after one repair: " + "; ".join(state["problems"])}


def route_request(state: State) -> str:
    """TODO 4 (stretch): return "resize" for resize-only requests, otherwise "write".

    A request is resize-only if it mentions "story size", "1080x1920" or "resize"
    AND there is a state["last_image"] to resize.
    """
    raise NotImplementedError("TODO 4: route_request in approach_graph/graph.py")


def resize_last(state: State) -> dict:
    """TODO 4 (stretch): resize state["last_image"] to (1080, 1920) with resize_image.

    No model call. Return {"image": new_path, "spec": state["last_spec"]}.
    Then in build_graph: add this node, replace the start_turn -> write_spec edge with
    g.add_conditional_edges("start_turn", route_request, {"write": "write_spec", "resize": "resize_last"}),
    and add g.add_edge("resize_last", END).
    """
    raise NotImplementedError("TODO 4: resize_last in approach_graph/graph.py")


def build_graph(checkpointer=None):
    g = StateGraph(State)
    g.add_node("start_turn", start_turn)
    g.add_node("write_spec", write_spec)
    g.add_node("validate", validate)
    g.add_node("generate_image", generate)
    g.add_node("give_up", give_up)
    g.add_edge(START, "start_turn")
    g.add_edge("start_turn", "write_spec")
    g.add_edge("write_spec", "validate")
    g.add_conditional_edges("validate", route_after_validate,
                            {"ok": "generate_image", "retry": "write_spec", "fail": "give_up"})
    g.add_edge("generate_image", END)
    g.add_edge("give_up", END)
    return g.compile(checkpointer=checkpointer)


# TODO 3 (part a): pass checkpointer=MemorySaver() so state survives between turns
# of the same conversation (handle() already passes the conversation ID as thread_id).
GRAPH = build_graph(checkpointer=None)


def handle(text: str, *, workspace: str, conversation_id: str, attachments: list[str]) -> Result:
    out = GRAPH.invoke(
        {"request": text, "workspace": workspace, "attachments": attachments, "conversation_id": conversation_id},
        config={"configurable": {"thread_id": conversation_id}},
    )
    if out.get("error"):
        return Result(error=out["error"])
    spec = PosterSpec.from_dict(out["spec"]) if out.get("spec") else None
    return Result(spec=spec, images=[out["image"]] if out.get("image") else [])
