"""Run the four Harbor requests through an approach and score them.

    python -m launchkit.scoreboard --approach llm
    python -m launchkit.scoreboard --approach graph
"""
import argparse
import uuid

from .approaches import load_handle
from .brand import load_brand
from .checks import CHECKS
from .paths import OUT
from .requests_fixture import REQUESTS


def run(approach: str, workspace: str = "harbor") -> list[dict]:
    handle = load_handle(approach)
    brand = load_brand(workspace)
    run_id = uuid.uuid4().hex[:6]
    history: dict[str, list] = {}
    rows = []
    for req in REQUESTS:
        conv = f"{approach}-{run_id}-{req['conversation']}"
        prev = history.setdefault(conv, [])
        res = None
        try:
            res = handle(req["text"], workspace=workspace, conversation_id=conv, attachments=list(req["attachments"]))
            status, why = CHECKS[req["id"]](res, prev, brand)
            status = "PASS" if status else "FAIL"
        except NotImplementedError as e:
            status, why = "TODO", str(e)
        except Exception as e:  # show the error, keep going
            status, why = "ERROR", f"{type(e).__name__}: {e}"
        prev.append(res)
        rows.append({"id": req["id"], "tests": req["tests"], "status": status, "why": why})
    return rows


def render(rows: list[dict], approach: str) -> str:
    lines = [f"Scoreboard: {approach}", ""]
    for r in rows:
        lines.append(f"{r['id']}  {r['status']:<5}  {r['tests']}")
        lines.append(f"           {r['why']}")
    passed = sum(r["status"] == "PASS" for r in rows)
    lines += ["", f"{passed}/{len(rows)} requests pass"]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--approach", required=True, choices=["llm", "graph"])
    parser.add_argument("--workspace", default="harbor")
    args = parser.parse_args()
    text = render(run(args.approach, args.workspace), args.approach)
    print(text)
    OUT.mkdir(exist_ok=True)
    (OUT / f"scoreboard-{args.approach}.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
