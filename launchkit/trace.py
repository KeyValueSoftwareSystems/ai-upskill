"""The trace: every line the Trace tab shows, and the scoreboard built from the call lines.

Ready-made for every ticket. Reference: page 11, "Jobs and the scoreboard". Memory writes `memory kept` and
`memory not kept`; routing writes `route`, `call`, `score` and `total`.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Event:
    kind: str
    detail: dict = field(default_factory=dict)


class Trace:
    def __init__(self):
        self.events: list[Event] = []
        self.listeners: list = []

    def add(self, kind: str, **detail):
        event = Event(kind, detail)
        self.events.append(event)
        for listener in self.listeners:
            listener(event)
        return event

    def file(self, path: Path):
        self.add("file", path=str(path))

    def note(self, text: str):
        self.add("note", text=text)

    def warn(self, text: str):
        """Something the person must act on: the chat page shows it in the chat, not only on the trace."""
        self.add("warning", text=text)

    def context(self, report: list[dict]):
        self.add("context", sections=report)

    def model(self, phase: str, model_id: str, metrics):
        self.add(
            "model",
            phase=phase,
            model=model_id,
            input_tokens=getattr(metrics, "input_tokens", 0) or 0,
            output_tokens=getattr(metrics, "output_tokens", 0) or 0,
            cached_tokens=getattr(metrics, "cache_read_tokens", 0) or 0,
        )

    def tool(self, name: str, arguments: dict, result):
        self.add("tool", name=name, arguments=arguments, result=result, result_tokens=round(len(str(result)) / 4))

    def chunk(self, rank: int, ref: str, score: float | None, text: str):
        """One chunk a search returned, so the trace shows what the model is about to read and why it ranked."""
        self.add("chunk", rank=rank, ref=ref, score=score, text=text)

    def route(self, job: str, model: str, reason: str):
        """Which model a job got, and why: pick, skill, rank N, fallback, retry, or the one setting."""
        self.add("route", job=job, model=model, reason=reason)

    def call(self, job: str, model: str, seconds: float, input_tokens: int, cached_tokens: int, output_tokens: int, usd: float | None):
        """One model call, as the scoreboard counts it. usd is None when nobody knows the price."""
        self.add("call", job=job, model=model, seconds=seconds, input_tokens=input_tokens, cached_tokens=cached_tokens, output_tokens=output_tokens, usd=usd)

    def bill(self) -> list[dict]:
        """The scoreboard: one row per model with its jobs, calls, tokens, seconds and dollars."""
        rows: dict[str, dict] = {}
        for e in self.events:
            if e.kind != "call":
                continue
            d = e.detail
            row = rows.setdefault(d["model"], {"model": d["model"], "jobs": [], "calls": 0, "input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "seconds": 0.0, "usd": 0.0, "unpriced": 0})
            if d["job"] not in row["jobs"]:
                row["jobs"].append(d["job"])
            row["calls"] += 1
            row["input_tokens"] += d["input_tokens"]
            row["cached_tokens"] += d["cached_tokens"]
            row["output_tokens"] += d["output_tokens"]
            row["seconds"] = round(row["seconds"] + d["seconds"], 2)
            if d["usd"] is None:
                row["unpriced"] += 1
            else:
                row["usd"] += d["usd"]
        for row in rows.values():
            if row["unpriced"] == row["calls"]:
                row["usd"] = None
        return list(rows.values())

    def scoreboard(self):
        """Write the scoreboard into the trace: one score line per model and a total line."""
        rows = self.bill()
        if not rows:
            return
        for row in rows:
            self.add("score", **row)
        self.add(
            "total",
            calls=sum(r["calls"] for r in rows),
            seconds=round(sum(r["seconds"] for r in rows), 2),
            usd=sum(r["usd"] for r in rows if r["usd"] is not None),
            unpriced=sum(r["unpriced"] for r in rows),
        )

    def memory_kept(self, scope: str, text: str):
        self.add("memory_kept", scope=scope, text=text)

    def memory_refused(self, text: str, reason: str):
        self.add("memory_refused", text=text, reason=reason)

    def refused(self, name: str, reason: str):
        self.add("refused", name=name, reason=reason)

    def draft(self, spec):
        """The copy as the model first wrote it, before any check, so a repair shows what it changed."""
        self.add("draft", headline=spec.headline, subheadline=spec.subheadline, body=spec.body)

    def validation(self, errors: list[str], attempt: int):
        self.add("validation", errors=errors, attempt=attempt)

    def stop(self, reason: str):
        self.add("stop", reason=reason)

    def written(self, path: Path):
        self.add("written", path=str(path))

    def picture(self, status: str, **detail):
        self.add("picture", status=status, **detail)

    def files_read(self) -> list[str]:
        return [e.detail["path"] for e in self.events if e.kind == "file"]

    def tool_calls(self, name: str | None = None) -> list[Event]:
        return [
            e for e in self.events if e.kind in ("tool", "refused") and (name is None or e.detail["name"] == name)
        ]

    def lines(self) -> list[str]:
        return [self.line(e) for e in self.events]

    def line(self, e: Event) -> str:
        d = e.detail
        match e.kind:
            case "file":
                return f"file      read {_relative(d['path'])}"
            case "note":
                return f"note      {d['text']}"
            case "warning":
                return f"warning   {d['text']}"
            case "written":
                return f"wrote     {_relative(d['path'])}"
            case "reply":
                return f"reply     {_short(d['text'], 80)}  (no poster this turn)"
            case "context":
                parts = " · ".join(
                    f"{s['section']}: {s['tokens']} tokens" + (" (cut to fit)" if s['trimmed'] else "")
                    for s in d["sections"] if s['tokens']
                )
                return f"prompt    {parts}"
            case "model":
                cached = f", {d['cached_tokens']} of them from cache" if d["cached_tokens"] else ""
                return f"model     {d['phase']} phase · {d['model']} · sent {d['input_tokens']} tokens{cached}, got back {d['output_tokens']}"
            case "tool":
                return f"tool      {d['name']}({_short(_args(d['arguments']), 60)}) → {_short(_result(d['result']), 60)} · {d.get('result_tokens', 0)} tokens back"
            case "chunk":
                score = f" · score {d['score']:.3f}" if d.get("score") is not None else ""
                return f"chunk     #{d['rank']} {d['ref']}{score} · {_short(d['text'], 70)}"
            case "refused":
                return f"refused   {d['name']}: {d['reason']}"
            case "route":
                return f"route     {d['job']} · {d['model']} · {d['reason']}"
            case "call":
                price = f"${d['usd']:.4f}" if d["usd"] is not None else "price unknown"
                cached = f" ({d['cached_tokens']} cached)" if d["cached_tokens"] else ""
                return f"call      {d['job']} · {d['model']} · {d['seconds']:.1f} s · {d['input_tokens']} in{cached} · {d['output_tokens']} out · {price}"
            case "score":
                price = f"${d['usd']:.4f}" if d["usd"] is not None else "price unknown"
                return f"score     {d['model']} · {d['calls']} calls · {d['seconds']:.1f} s · {price} · {', '.join(d['jobs'])}"
            case "total":
                unpriced = f" ({d['unpriced']} unpriced)" if d["unpriced"] else ""
                return f"total     {d['calls']} calls · {d['seconds']:.1f} s · ${d['usd']:.4f}{unpriced}"
            case "memory_kept":
                return f"memory    kept · {d['scope']} · {_short(d['text'], 70)}"
            case "memory_refused":
                return f"memory    not kept · {d['reason']} · {_short(d['text'], 70)}"
            case "draft":
                return f'draft     headline "{d["headline"]}" ({_words(d["headline"])} words) · subheadline {_words(d["subheadline"])} words · body {_words(d["body"])} words'
            case "validation":
                return f"check     attempt {d['attempt']}: " + ("; ".join(d["errors"]) if d["errors"] else "spec is clean")
            case "stop":
                return f"stop      {d['reason']}"
            case "picture":
                if d["status"] == "skipped":
                    return f"picture   skipped, {d.get('reason', '')}"
                elif d["status"] == "done":
                    return f"picture   saved {_relative(d['file'])}"
                elif d["status"] == "rework":
                    return f"picture   rework {_relative(d['file'])}, {d.get('reason', '')}"
                elif d["status"] == "reused":
                    return f"picture   reused {_relative(d['file'])}, {d.get('reason', '')}"
                else:
                    return f"picture   none, {d.get('reason') or 'the tool returned no file'}"
            case _:
                return f"{e.kind:<9} {_short(d)}"


def _relative(path) -> str:
    text = str(path)
    for marker in ("/workspaces/", "/data/"):
        if marker in text:
            return text[text.index(marker) + 1 :]
    return text


def _args(arguments: dict) -> str:
    return ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in arguments.values())


def _result(result) -> str:
    if isinstance(result, dict) and "file" in result:
        return "file " + _relative(result["file"])
    if isinstance(result, dict) and result.get("status"):
        return f"{result['status']}: {result.get('reason', '')}"
    return str(result)


def _words(text: str) -> int:
    return len(str(text).split())


def _short(value, width: int = 90) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= width else text[: width - 1] + "…"
