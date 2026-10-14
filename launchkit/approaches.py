import importlib

APPROACHES = {"llm": "approach_llm.app", "graph": "approach_graph.graph"}


def load_handle(name: str):
    module = APPROACHES.get(name)
    if module is None:
        raise SystemExit(f"Unknown approach '{name}'. Choose from: {', '.join(APPROACHES)}")
    try:
        return importlib.import_module(module).handle
    except ModuleNotFoundError as e:
        branch = "session-01-llm-call" if name == "llm" else "session-01-langgraph"
        raise SystemExit(f"Can't load '{module}' ({e}). Did you check out branch {branch}?")
