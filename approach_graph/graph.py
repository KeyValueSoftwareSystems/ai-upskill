"""A LangGraph pipeline.

    START -> start_turn -> write_spec -> validate --ok--> generate_image -> END
                               ^            |
                               +--retry-----+--fail--> give_up -> END

The graph gives us structure the plain call didn't have: a validate-and-retry
loop, and (with a checkpointer) state that survives between turns.
"""
import json

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from launchkit.brand import brand_rules_text, load_brand
from launchkit.images import generate_image
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
    # TODO 3 (part b): give the model the previous poster so follow-ups work.
    if state.get("last_spec"):
        system += "\nPrevious poster spec (edit this one if the user asks for changes):\n" + json.dumps(state["last_spec"])
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
    """TODO 1: Parse the reply and validate it. Store the spec and any problems."""
    try:
        spec = parse_spec(state["raw"])
    except SpecError as e:
        return {"spec": None, "problems": [str(e)]}
    return {"spec": spec.to_dict(), "problems": validate_spec(spec, state["brand"])}


def route_after_validate(state: State) -> str:
    """TODO 2: Decide where to go after validate: "ok", "retry" or "fail"."""
    if not state["problems"]:
        return "ok"
    return "retry" if state["attempts"] < MAX_ATTEMPTS else "fail"


def generate(state: State) -> dict:
    spec = state["spec"]
    image = generate_image(spec["visual_concept"], state["brand"], conversation_id=state["conversation_id"])
    return {"image": image, "last_spec": spec, "last_image": image}


def give_up(state: State) -> dict:
    return {"error": "still invalid after one repair: " + "; ".join(state["problems"])}


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


# TODO 3 (part a): add a checkpointer so state survives between turns.
GRAPH = build_graph(checkpointer=MemorySaver())


def handle(text: str, *, workspace: str, conversation_id: str, attachments: list[str]) -> Result:
    out = GRAPH.invoke(
        {"request": text, "workspace": workspace, "attachments": attachments, "conversation_id": conversation_id},
        config={"configurable": {"thread_id": conversation_id}},
    )
    if out.get("error"):
        return Result(error=out["error"])
    spec = PosterSpec.from_dict(out["spec"]) if out.get("spec") else None
    return Result(spec=spec, images=[out["image"]] if out.get("image") else [])
