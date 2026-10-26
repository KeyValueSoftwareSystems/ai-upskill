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
    text = str(value)
    return text if len(text) <= width else text[: width - 1] + "…"
