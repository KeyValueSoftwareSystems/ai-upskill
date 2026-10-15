"""Harbor's four requests, and a scoreboard that runs them through an approach.

    uv run python -m launchkit.scoreboard --approach llm
    uv run python -m launchkit.scoreboard --approach graph

Each request comes straight from the problem statement. Order matters: R2 follows R1 in
conversation A, and R4 follows R3 in conversation B.
"""
import argparse
import importlib
import uuid
from difflib import SequenceMatcher

from .poster import OUT, load_brand, validate_spec, word_count

REQUESTS = [
    {"id": "R1", "conversation": "A", "needs": "a concept becomes an on-brand poster",
     "text": "Poster for the Tidal bottle on a misty lakeshore at dawn. Headline idea: cold for 24 hours.",
     "attachments": []},
    {"id": "R2", "conversation": "A", "needs": "follow-up edits",
     "text": "Make the headline shorter.",
     "attachments": []},
    {"id": "R3", "conversation": "B", "needs": "a concept given as a photo",
     "text": "Use this photo of the bottle. Make the bottle bigger and the lake moodier.",
     "attachments": ["assets/tidal_photo.png"]},
    {"id": "R4", "conversation": "B", "needs": "resizing the poster we just made",
     "text": "Now give me the story size (1080x1920) of that poster.",
     "attachments": []},
]
APPROACHES = {"llm": "approach_llm.app", "graph": "approach_graph.graph"}


def load_handle(name: str):
    module = APPROACHES[name]
    try:
        return importlib.import_module(module).handle
    except ModuleNotFoundError as e:
        branch = "session-01-llm-call" if name == "llm" else "session-01-langgraph"
        raise SystemExit(f"Can't load '{module}' ({e}). Did you check out branch {branch}?")


# ---- checks: each returns (passed, reason). `prev` is the earlier results in the same conversation.


def _valid(res, brand):
    if res is None or res.error:
        return False, f"no poster: {res.error if res else 'nothing returned'}"
    if res.spec is None:
        return False, "no poster spec returned"
    problems = validate_spec(res.spec, brand)
    if problems:
        return False, "breaks Harbor's rules: " + "; ".join(problems)
    if not res.images:
        return False, "no image generated"
    return True, ""


def check_r1(res, prev, brand):
    ok, why = _valid(res, brand)
    if not ok:
        return ok, why
    prompt = res.images[0].prompt or ""
    if res.spec.headline.lower() in prompt.replace(res.spec.visual_concept, "").lower():
        return False, "the headline was sent to the image model"
    return True, "valid copy, picture with no words"


def check_r2(res, prev, brand):
    before = next((p for p in reversed(prev) if p and p.spec), None)
    if before is None:
        return False, "R1 produced no poster to edit"
    ok, why = _valid(res, brand)
    if not ok:
        return ok, why
    rest = lambda spec: f"{spec.subheadline} {spec.body} {spec.visual_concept}".lower()
    if SequenceMatcher(None, rest(before.spec), rest(res.spec)).ratio() < 0.7:  # an edit keeps the rest
        return False, (f'a different poster came back ("{before.spec.headline}" became "{res.spec.headline}", '
                       "and everything else changed too): the model never saw the first poster")
    if word_count(res.spec.headline) >= word_count(before.spec.headline):
        return False, f'headline not shorter ("{res.spec.headline}" vs "{before.spec.headline}")'
    return True, f'"{before.spec.headline}" became "{res.spec.headline}"'


def check_r3(res, prev, brand, photo="assets/tidal_photo.png"):
    ok, why = _valid(res, brand)
    if not ok:
        return ok, why
    if not (res.images[0].reference or "").endswith(photo):
        return False, "the uploaded photo was ignored: a text-only call never sees it"
    return True, "poster built from the uploaded photo"


def check_r4(res, prev, brand):
    before = next((p for p in reversed(prev) if p and p.images), None)
    if before is None:
        return False, "no earlier poster to resize"
    if res is None or res.error or not res.images:
        return False, f"no image: {res.error if res else 'nothing returned'}"
    story = [p for p in res.images if tuple(p.size) == (1080, 1920)]
    if not story:
        w, h = res.images[0].size
        return False, f"asked for 1080x1920, got a new {w}x{h} picture"
    if not any(p.resized_from in [b.path for b in before.images] for p in story):
        return False, "a brand-new picture was made: the call doesn't know which poster 'that poster' is"
    return True, "resized the existing poster to 1080x1920"


CHECKS = {"R1": check_r1, "R2": check_r2, "R3": check_r3, "R4": check_r4}


def run(approach: str, workspace: str = "harbor") -> list[dict]:
    handle = load_handle(approach)
    brand = load_brand(workspace)
    run_id = uuid.uuid4().hex[:6]
    history: dict[str, list] = {}
    rows = []
    for req in REQUESTS:
        conv = f"{approach}-{run_id}-{req['conversation']}"
        prev = history.setdefault(conv, [])
        print(f"{req['id']}: {req['text']}", flush=True)
        res = None
        try:
            res = handle(req["text"], workspace=workspace, conversation_id=conv, attachments=list(req["attachments"]))
            ok, why = CHECKS[req["id"]](res, prev, brand)
            status = "PASS" if ok else "FAIL"
        except NotImplementedError as e:
            status, why = "TODO", str(e)
        except Exception as e:  # show the error, keep going
            status, why = "ERROR", f"{type(e).__name__}: {e}"
        prev.append(res)
        rows.append({**req, "status": status, "why": why})
    return rows


def render(rows: list[dict], approach: str) -> str:
    lines = [f"Scoreboard: {approach}", ""]
    for r in rows:
        lines.append(f"{r['id']}  {r['status']:<5}  needs {r['needs']}")
        lines.append(f"           {r['why']}")
    passed = sum(r["status"] == "PASS" for r in rows)
    lines += ["", f"{passed}/{len(rows)} requests pass"]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--approach", required=True, choices=list(APPROACHES))
    parser.add_argument("--workspace", default="harbor")
    args = parser.parse_args()
    text = render(run(args.approach, args.workspace), args.approach)
    print("\n" + text)
    OUT.mkdir(exist_ok=True)
    (OUT / f"scoreboard-{args.approach}.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
