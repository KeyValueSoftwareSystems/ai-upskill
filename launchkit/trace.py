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
            seconds=getattr(metrics, "duration", 0) or 0,
        )

    def route(self, job: str, model_id: str, reason: str):
        """route()'s choice for one job: the model and why (pick, skill, rank N, fallback)."""
        self.add("route", job=job, model=model_id, reason=reason)

    def call(self, job: str, model_id: str, seconds: float, input_tokens: int, cached_tokens: int, output_tokens: int, usd: float | None = None):
        """One real model call, timed: what the scoreboard adds up. usd is what the proxy said it charged, when it said."""
        self.add("call", job=job, model=model_id, seconds=seconds, input_tokens=input_tokens, cached_tokens=cached_tokens, output_tokens=output_tokens, usd=usd)

    def bill(self) -> list[dict]:
        """The scoreboard: one row per model, with the jobs it did, its calls, tokens, seconds and dollars. The dollars are
        what the proxy said it charged; for a call it said nothing about, an estimate from launchkit/adapters/pricing.py,
        and the row says so. Pictures and voice-overs are not on it. Real calls are timed one by one; a run on a fake model
        counts as one call. Reads the trace; adds no model call."""
        from launchkit.adapters.pricing import cost_usd

        calls = [e.detail for e in self.events if e.kind == "call"]
        if not calls:
            calls = [{**e.detail, "job": e.detail["phase"]} for e in self.events if e.kind == "model"]
        rows: dict[str, dict] = {}
        for c in calls:
            row = rows.setdefault(c["model"], {"model": c["model"], "jobs": [], "calls": 0, "input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "seconds": 0.0, "usd": 0.0, "estimated": False, "unknown": False})
            if c["job"] not in row["jobs"]:
                row["jobs"].append(c["job"])
            row["calls"] += 1
            for key in ("input_tokens", "cached_tokens", "output_tokens", "seconds"):
                row[key] += c.get(key, 0) or 0
            usd = c.get("usd")
            if usd is None:
                usd = cost_usd(c["model"], c.get("input_tokens", 0) or 0, c.get("cached_tokens", 0) or 0, c.get("output_tokens", 0) or 0)
                row["estimated"] = True
            if usd is None:
                row["unknown"] = True
            else:
                row["usd"] += usd
        for row in rows.values():
            if row["unknown"] and not row["usd"]:
                row["usd"] = None
        return list(rows.values())

    def checks(self) -> dict:
        """The quality column: Harbor's checks this turn, in the order they ran. check_copy and the poster check pass or
        fail; describe_image finding words or another brand's logo is the photo check catching something."""
        copy = [bool(e.detail["result"]["ok"]) for e in self.events
                if e.kind == "tool" and e.detail["name"] == "check_copy" and isinstance(e.detail["result"], dict) and "ok" in e.detail["result"]]
        validations = [e.detail for e in self.events if e.kind == "validation"]
        photos = [e.detail["result"] for e in self.events if e.kind == "tool" and e.detail["name"] == "describe_image" and isinstance(e.detail["result"], dict)]
        return {"copy": copy, "poster": (not validations[-1]["errors"]) if validations else None,
                "photo_flags": sum(1 for r in photos if r.get("other_brand") or r.get("text"))}

    def scoreboard(self):
        """Add the scoreboard to the trace, so the chat page's Trace tab and the terminal both show it."""
        rows = self.bill()
        for row in rows:
            self.add("score", **row)
        if rows:
            priced = [r["usd"] for r in rows if r["usd"] is not None]
            self.add("total", calls=sum(r["calls"] for r in rows), seconds=sum(r["seconds"] for r in rows),
                     usd=sum(priced) if priced else None, estimated=any(r["estimated"] or r["unknown"] for r in rows),
                     unpriced=len(priced) < len(rows))
        self.add("quality", **self.checks())

    def tool(self, name: str, arguments: dict, result):
        self.add("tool", name=name, arguments=arguments, result=result, result_tokens=round(len(str(result)) / 4))

    def chunk(self, rank: int, ref: str, score: float | None, text: str):
        """One chunk a search returned, so the trace shows what the model is about to read and why it ranked."""
        self.add("chunk", rank=rank, ref=ref, score=score, text=text)

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
            case "route":
                return f"route     {d['job']} · {d['model']} · {d['reason']}"
            case "call":
                return f"call      {d['job']} · {d['model']} · {d['seconds']:.1f} s · sent {d['input_tokens']}, got back {d['output_tokens']}"
            case "score":
                if d.get("usd") is None:
                    usd = "price unknown"
                elif d.get("estimated") or d.get("unknown"):
                    usd = f"≈ ${d['usd']:.4f} (estimate from our price table)"
                else:
                    usd = f"${d['usd']:.4f} (charged by the proxy)"
                return (f"score     {d['model']} · {', '.join(d['jobs'])} · {d['calls']} calls · {d['input_tokens']} tokens in, "
                        f"{d['output_tokens']} out · {d['seconds']:.1f} s · {usd}")
            case "total":
                if d["usd"] is None:
                    usd = "price unknown"
                else:
                    usd = f"≈ ${d['usd']:.4f}" if d["estimated"] else f"${d['usd']:.4f}"
                    usd += " (some calls not priced)" if d["unpriced"] else ""
                return f"total     {usd} · {d['calls']} calls · {d['seconds']:.1f} s"
            case "quality":
                parts = []
                copy = d["copy"]
                if copy:
                    failed = copy.count(False)
                    if copy[-1]:
                        parts.append(f"check_copy failed {failed}, then passed" if failed else "check_copy passed")
                    else:
                        parts.append("check_copy failed" + (f" {len(copy)} times" if len(copy) > 1 else ""))
                if d["poster"] is not None:
                    parts.append("poster check passed" if d["poster"] else "poster check failed")
                if d["photo_flags"]:
                    parts.append("photo check caught another brand's logo or words")
                return "quality   " + (" · ".join(parts) if parts else "no check ran this turn")
            case "chunk":
                score = f" · score {d['score']:.3f}" if d.get("score") is not None else ""
                return f"chunk     #{d['rank']} {d['ref']}{score} · {_short(d['text'], 70)}"
            case "refused":
                return f"refused   {d['name']}: {d['reason']}"
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
