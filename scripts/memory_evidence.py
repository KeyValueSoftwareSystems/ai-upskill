"""Prep only: run Session 3's live pains on the real model from the checked-in snapshot and save every outcome.

    uv run python scripts/memory_evidence.py t1 --label after                      # this checkout's code
    .venv/bin/python scripts/memory_evidence.py t1 --label before --code <tree>    # another checkout's code (the starting state)

Each run starts from a fresh copy of fixtures/memory-snapshot*, in a new conversation, and records the reply, the
Trace's memory and tool lines, what was asked for approval, tokens, seconds, and the rows before and after. The JSON in
docs/sessions/session-3/evidence/ is also the recorded run to show when the proxy is slow. An approval is answered the
way Maya would: yes, unless the planned change says "lifetime".

Pains: t1 t2a t2b t3 (one turn, three runs), t4a (the power user's turn; --retention first prunes and Summarizes),
t4b (the long Tidal job: eight turns, then the brief is asked back).
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
os.environ["LAUNCHKIT_IMAGE_PROVIDER"] = "placeholder"  # no picture matters to memory; none is paid for

ONE_TURN = {
    "t1": ("harbor", "maya", "Write the headline for the Breeze story size. Never say lifetime guarantee."),
    "t2a": ("harbor", "maya", "The warranty is five years now, redo the Tidal headline."),
    "t2b": ("harbor", "maya", "How is Cairnline launching its Summit bottle this season? One paragraph: message, channels, what to avoid copying."),
    "t3": ("alder", "agency-manager", "Headline for Alder's spring poster."),
    "t4a": ("harbor", "power-user", "Write one headline for the Tidal poster."),
}
LONG_JOB = [
    "Here is the Tidal launch brief. Four tasks: 1) what hikers are talking about this season, 2) how five competitors are launching, "
    "3) every Harbor size of the approved poster, 4) hand it back on the board. Deadline: Friday 13 November. Keep the lid out of all copy: "
    "it changes before launch. Just confirm you have it, nothing else yet.",
    "Which of our placements does the web banner go on?",
    "Give me three moods for a Breeze shoot.",
    "What is our headline word limit?",
    "Suggest a calm tagline for the Breeze colourway.",
    "What colours does Harbor use?",
    "Write one line for a Tuesday feed post about weekend hikes.",
    "Back to the Tidal brief: list its four tasks, the deadline and the copy rule.",
]
RECALL = {"deadline": ("13 november", "friday"), "lid rule": ("lid",), "trends": ("trend", "hikers"), "competitors": ("competitor",),
          "sizes": ("size",), "board": ("board",)}


def rows(data: Path, user: str) -> dict:
    out = {"memories": [], "learnings": [], "learning_text_with_lifetime": [], "brand_facts": []}
    with sqlite3.connect(data / "sessions.db") as con:
        q = lambda sql, *a: (lambda: con.execute(sql, a).fetchall())
        for name, sql, args in [("memories", "select memory from agno_memories where user_id = ? order by updated_at", (user,)),
                                ("learnings", "select name, metadata from agno_knowledge", ()),
                                ("brand_facts", "select subject, value, valid_from, valid_to, source from brand_facts where brand = 'harbor'", ())]:
            try:
                out[name] = [list(r) if len(r) > 1 else r[0] for r in q(sql, *args)()]
            except sqlite3.OperationalError:
                pass
    import lancedb

    if (data / "learnings").exists() and "learnings" in lancedb.connect(str(data / "learnings")).table_names():
        for r in lancedb.connect(str(data / "learnings")).open_table("learnings").to_arrow().to_pylist():
            if "lifetime" in (r.get("payload") or "").lower():
                out["learning_text_with_lifetime"].append(json.loads(r["payload"]).get("name"))
    return out


def fresh(tmp: Path, start: Path | None) -> Path:
    data = tmp / "data"
    shutil.rmtree(data, ignore_errors=True)
    data.mkdir(parents=True)
    source = start or HERE / "fixtures"
    shutil.copyfile(source / "memory-snapshot.db", data / "sessions.db")
    shutil.copytree(source / "memory-snapshot-learnings", data / "learnings")
    shutil.copytree(HERE / "data" / "brand-store", data / "brand-store")
    return data


def turn(settings, workspace, user, session, text, asked):
    from launchkit.agents.main_agent import run_main
    from launchkit.brands.request import Request
    from launchkit.trace import Trace

    trace = Trace()
    approve = lambda name, plan: asked.append({"name": name, "plan": plan}) or "lifetime" not in json.dumps(plan).lower()
    started = time.perf_counter()
    try:
        result = run_main(Request(workspace_id=workspace, user_id=user, session_id=session, text=text), settings=settings, trace=trace, approve=approve)
        reply, spec, error = result.reply, result.spec.model_dump() if result.spec else None, None
    except Exception as exc:  # a failed run is an outcome too
        reply, spec, error = "", None, f"{type(exc).__name__}: {exc}"
    models = [e.detail for e in trace.events if e.kind == "model"]
    return {
        "text": text, "reply": reply, "spec": spec, "error": error, "seconds": round(time.perf_counter() - started, 1),
        "input_tokens": sum(m["input_tokens"] for m in models), "output_tokens": sum(m["output_tokens"] for m in models),
        "main_call_input_tokens": [m["input_tokens"] for m in models if m["phase"] == "main"],
        "trace": [trace.line(e) for e in trace.events if e.kind in ("memory", "tool", "refused", "model", "validation", "stop")],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pain", choices=[*ONE_TURN, "t4b"])
    parser.add_argument("--label", required=True)
    parser.add_argument("--code", type=Path, default=HERE, help="the checkout whose launchkit/ runs")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--retention", action="store_true", help="t4a: run the retention job (--days 90 --apply) on the snapshot first")
    args = parser.parse_args()
    sys.path.insert(0, str(args.code.resolve()))
    from launchkit.settings import settings as base

    out_dir = HERE / "docs" / "sessions" / "session-3" / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    record = {"pain": args.pain, "label": args.label, "code": str(args.code), "model": base.model, "memory_model": getattr(base, "memory_model", None), "runs": []}
    with tempfile.TemporaryDirectory() as tmp:
        start = None
        if args.retention:
            data = fresh(Path(tmp) / "prep", None)
            settings = replace(base, data_dir=data, search="saved", board="local")
            from launchkit.adapters.models import resolve_model
            from launchkit.memory.long_term import memory_manager
            from launchkit.memory.retention import retain
            from launchkit.trace import Trace

            record["retention"] = retain(memory_manager(settings, Trace(), resolve_model(settings, Trace())), 90, 100, apply=True)
            start = Path(tmp) / "after-retention"
            start.mkdir()
            with sqlite3.connect(data / "sessions.db") as s, sqlite3.connect(start / "memory-snapshot.db") as t:
                s.backup(t)
            shutil.copytree(data / "learnings", start / "memory-snapshot-learnings")
            record["retention_rows_after"] = rows(data, "power-user")["memories"]
        for n in range(1, args.runs + 1):
            data = fresh(Path(tmp) / f"run{n}", start)
            settings = replace(base, data_dir=data, search="saved", board="local")
            workspace, user = ("harbor", "maya") if args.pain == "t4b" else ONE_TURN[args.pain][:2]
            before, asked = rows(data, user), []
            turns = [turn(settings, workspace, user, f"{args.pain}-{args.label}-{n}", text, asked)
                     for text in (LONG_JOB if args.pain == "t4b" else [ONE_TURN[args.pain][2]])]
            after = rows(data, user)
            run = {"run": n, "turns": turns, "asked": asked,
                   "memories_added": [m for m in after["memories"] if m not in before["memories"]],
                   "memories_removed": [m for m in before["memories"] if m not in after["memories"]],
                   "learnings_after": after["learnings"], "learning_text_with_lifetime": after["learning_text_with_lifetime"],
                   "brand_facts_after": after["brand_facts"]}
            if args.pain == "t4b":
                last = (turns[-1]["reply"] or "").lower()
                run["recall"] = {k: any(w in last for w in words) for k, words in RECALL.items()}
            record["runs"].append(run)
            print(f"{args.pain} {args.label} run {n}: {turns[-1]['seconds']} s, {turns[-1]['input_tokens']} tokens in · {(turns[-1]['reply'] or turns[-1]['error'] or '')[:100]!r}", flush=True)
    path = out_dir / f"{args.pain}-{args.label}{'-retention' if args.retention else ''}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"wrote {path.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
