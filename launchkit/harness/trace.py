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

    def validation(self, errors: list[str], attempt: int):
        self.add("validation", errors=errors, attempt=attempt)

    def stop(self, reason: str):
        self.add("stop", reason=reason)

    def picture(self, status: str, **detail):
        self.add("picture", status=status, **detail)

    def files_read(self) -> list[str]:
        return [e.detail["path"] for e in self.events if e.kind == "file"]

    def tool_calls(self, name: str | None = None) -> list[Event]:
        return [
            e for e in self.events if e.kind in ("tool", "refused") and (name is None or e.detail["name"] == name)
        ]

    def lines(self) -> list[str]:
        out = []
        for e in self.events:
            d = e.detail
            match e.kind:
                case "file":
                    out.append(f"file      read {_relative(d['path'])}")
                case "note":
                    out.append(f"note      {d['text']}")
                case "context":
                    parts = " · ".join(
                        f"{s['section']}: " + ("empty" if s['tokens'] == 0 else f"{s['tokens']} tokens" + (" (cut to fit)" if s['trimmed'] else ""))
                        for s in d["sections"]
                    )
                    out.append(f"prompt    {parts}")
                case "model":
                    cached = f", {d['cached_tokens']} of them from cache" if d["cached_tokens"] else ""
                    out.append(f"model     {d['phase']} phase · {d['model']} · sent {d['input_tokens']} tokens{cached}, got back {d['output_tokens']}")
                case "tool":
                    out.append(f"tool      {d['name']}({_short(_args(d['arguments']), 60)}) → {_short(_result(d['result']), 60)} · {d.get('result_tokens', 0)} tokens back")
                case "refused":
                    out.append(f"refused   {d['name']}: {d['reason']}")
                case "validation":
                    out.append(f"check     attempt {d['attempt']}: " + ("; ".join(d["errors"]) if d["errors"] else "spec is clean"))
                case "stop":
                    out.append(f"stop      {d['reason']}")
                case "picture":
                    if d["status"] == "skipped":
                        out.append(f"picture   skipped, {d.get('reason', '')}")
                    elif d["status"] == "done":
                        out.append(f"picture   saved {_relative(d['file'])}")
                    else:
                        out.append("picture   none, the tool returned no file")
                case _:
                    out.append(f"{e.kind:<9} {_short(d)}")
        return out


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


def _short(value, width: int = 90) -> str:
    text = str(value)
    return text if len(text) <= width else text[: width - 1] + "…"
