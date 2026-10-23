"""Maya's four requests, and a scoreboard that runs them through an approach.

    uv run python -m launchkit.scoreboard --approach llm
    uv run python -m launchkit.scoreboard --approach graph

Maya is Harbor's marketer. Her requests come one after another in one conversation, so order
matters: R2 to R4 all build on the poster she approved in R1.
"""
import argparse
import importlib
import re
import uuid

from .poster import OUT, load_brand, validate_spec

STORY = (1080, 1920)
REQUESTS = [
    {"id": "R1", "needs": "a full poster from one idea",
     "text": "Tidal launch, a misty lakeshore at dawn. Can I get a concept, a storyboard, the words and a poster?"},
    {"id": "R2", "needs": "keep my picture: the story size of the approved poster",
     "text": "Love it. Just the story size now, please."},
    {"id": "R3", "needs": "an answer, not a new poster",
     "text": "What does your brand book say about washing the lid?"},
    {"id": "R4", "needs": "three asks in one message",
     "text": "Is the lid dishwasher-safe? If not, fix the copy, then give me the story size."},
]
APPROACHES = {"llm": "approach_llm.app", "graph": "approach_graph.graph"}


def load_handle(name: str):
    module = APPROACHES[name]
    try:
        return importlib.import_module(module).handle
    except ModuleNotFoundError as e:
        branch = "session-01-llm-call" if name == "llm" else "session-01-langgraph"
        raise SystemExit(f"Can't load '{module}' ({e}). Did you check out branch {branch}?")


# ---- checks: each returns (passed, reason). `prev` is the earlier results in the conversation.


def _valid(res, brand):
    if res is None or res.error:
        return False, f"no poster: {res.error if res else 'nothing returned'}"
    if res.spec is None:
        return False, "no poster spec returned"
    problems = validate_spec(res.spec, brand)
    if problems:
        return False, "breaks Harbor's rules: " + "; ".join(problems)
    return True, ""


def _new_pictures(res):
    """Pictures the image model made for this request (each one paid for), as opposed to resized by code."""
    return [p for p in res.images if not p.resized_from] if res else []


def _approved(prev):
    """The paths of the pictures Maya has already seen in this conversation."""
    return [p.path for r in prev if r for p in r.images]


def _story_of_approved(res, prev):
    approved = _approved(prev)
    return any(tuple(p.size) == STORY and p.resized_from in approved for p in (res.images if res else []))


def _answers_the_lid(res):
    return bool(res and res.answer and re.search(r"hand[- ]?wash", res.answer, re.I))


def check_r1(res, prev, brand):
    ok, why = _valid(res, brand)
    if not ok:
        return ok, why
    if not _new_pictures(res):
        return False, "no picture was made"
    prompt = _new_pictures(res)[0].prompt or ""
    if res.spec.headline.lower() in prompt.replace(res.spec.visual_concept, "").lower():
        return False, "the headline was sent to the image model"
    return True, f'concept, {len(res.spec.storyboard)} frames, words that follow the rules, a picture with no words'


def check_r2(res, prev, brand):
    if not _approved(prev):
        return False, "R1 made no poster, so there is nothing to resize"
    if res is None or res.error:
        return False, f"nothing came back: {res.error if res else 'nothing returned'}"
    if _new_pictures(res):
        return False, ("it drew a new one: every step ran again, so a new picture came back (and was paid for) "
                       "instead of the one she approved")
    if not _story_of_approved(res, prev):
        return False, f"no {STORY[0]}x{STORY[1]} version of the approved picture"
    return True, "the approved picture, resized by code to the story size; no new picture"


def check_r3(res, prev, brand):
    if res is None or res.error:
        return False, f"nothing came back: {res.error if res else 'nothing returned'}"
    if not res.answer:
        made = "a new poster and a new picture" if _new_pictures(res) else "a poster"
        return False, f"she asked a question and got {made} instead of an answer"
    if _new_pictures(res):
        return False, "answered, but also drew a new picture nobody asked for"
    if not _answers_the_lid(res):
        return False, f'the answer misses the fact: the lid is hand-wash only ("{res.answer[:80]}")'
    return True, "answered from Harbor's facts: the lid is hand-wash only"


def check_r4(res, prev, brand):
    if res is None or res.error:
        return False, f"nothing came back: {res.error if res else 'nothing returned'}"
    asks = {
        "answer the lid question": _answers_the_lid(res),
        "fix the copy": _valid(res, brand)[0],
        "the story size of the approved picture": _story_of_approved(res, prev) and not _new_pictures(res),
    }
    dropped = [ask for ask, done in asks.items() if not done]
    if dropped:
        done = [ask for ask, ok in asks.items() if ok]
        return False, (f"{len(dropped)} of her 3 asks vanished, and nobody told her: " + "; ".join(dropped)
                       + (f" (done: {'; '.join(done)})" if done else ""))
    return True, "all three asks done: the answer, the copy and the story size"


CHECKS = {"R1": check_r1, "R2": check_r2, "R3": check_r3, "R4": check_r4}


def run(approach: str, workspace: str = "harbor") -> list[dict]:
    handle = load_handle(approach)
    brand = load_brand(workspace)
    run_id = uuid.uuid4().hex[:6]
    conv = f"{approach}-{run_id}"  # one conversation: Maya's requests follow each other
    prev, rows = [], []
    for req in REQUESTS:
        print(f"{req['id']}: {req['text']}", flush=True)
        res = None
        try:
            res = handle(req["text"], workspace=workspace, conversation_id=conv)
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
