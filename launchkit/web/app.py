import asyncio
import json
import re
import threading
import time
import uuid
from dataclasses import replace
from pathlib import Path
from queue import Queue

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from launchkit.harness.library import asset_path, read_library, workspace_root
from launchkit.harness.onboard import onboard_workspace
from launchkit.harness.request import Request, UnknownWorkspace, resolve_workspace_id
from launchkit.harness.main import run_main
from launchkit.harness.spec import SpecError
from launchkit.harness.trace import Trace
from launchkit.harness.users import list_logins
from launchkit.settings import settings

app = FastAPI(title="LaunchKit")
HERE = Path(__file__).parent
RUNS: dict[str, Queue] = {}
ASKS: dict[str, tuple[threading.Event, dict]] = {}
DONE = object()
ASK_WAIT = 300
MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".mp3", ".wav"}


class RunBody(BaseModel):
    workspace_id: str
    user_id: str
    text: str
    model: str | None = None
    session_id: str | None = None


class Answer(BaseModel):
    allow: bool


@app.get("/", response_class=HTMLResponse)
def index():
    return (HERE / "index.html").read_text(encoding="utf-8")


@app.get("/workspaces")
def workspaces():
    return sorted(p.name for p in settings.workspaces_dir.iterdir() if p.is_dir())


@app.get("/logins")
def logins():
    return list_logins(settings)


def _conversation_dir(workspace_id: str, user_id: str) -> Path:
    safe = Path(workspace_id).name, Path(user_id).name
    folder = settings.data_dir / "conversations" / safe[0] / safe[1]
    older = folder.with_suffix(".json")
    if older.is_file():
        data = json.loads(older.read_text(encoding="utf-8"))
        folder.mkdir(parents=True, exist_ok=True)
        older.rename(folder / f"{data['session_id']}.json")
    return folder


def _conversations(workspace_id: str, user_id: str) -> list[Path]:
    folder = _conversation_dir(workspace_id, user_id)
    return sorted(folder.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True) if folder.is_dir() else []


def _load_conversation(workspace_id: str, user_id: str, session_id: str | None = None) -> dict:
    saved = _conversations(workspace_id, user_id)
    if session_id and re.fullmatch(r"[0-9a-f]{6}", session_id):
        saved = [path for path in saved if path.stem == session_id]
    if saved:
        return json.loads(saved[0].read_text(encoding="utf-8"))
    return {"session_id": uuid.uuid4().hex[:6], "turns": []}


def _save_conversation(workspace_id: str, user_id: str, data: dict):
    folder = _conversation_dir(workspace_id, user_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{data['session_id']}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def _with_list(workspace_id: str, user_id: str, data: dict) -> dict:
    """The conversation plus every saved one for this person at this brand, newest first, for the picker."""
    listed = []
    for path in _conversations(workspace_id, user_id):
        turns = json.loads(path.read_text(encoding="utf-8"))["turns"]
        first = next((t["text"] for t in turns if t.get("role") == "user"), "")
        listed.append({"session_id": path.stem, "first": first[:60], "updated": path.stat().st_mtime})
    return {**data, "conversations": listed}


@app.get("/conversations/{workspace_id}/{user_id}")
def conversation(workspace_id: str, user_id: str, session_id: str | None = None):
    data = _load_conversation(workspace_id, user_id, session_id)
    _save_conversation(workspace_id, user_id, data)
    return _with_list(workspace_id, user_id, data)


@app.post("/conversations/{workspace_id}/{user_id}/new")
def new_conversation(workspace_id: str, user_id: str):
    data = {"session_id": uuid.uuid4().hex[:6], "turns": []}
    _save_conversation(workspace_id, user_id, data)
    return _with_list(workspace_id, user_id, data)


@app.post("/run")
def start_run(body: RunBody):
    run_id = uuid.uuid4().hex[:8]
    queue: Queue = Queue()
    RUNS[run_id] = queue
    threading.Thread(target=_worker, args=(body, queue), daemon=True).start()
    return {"run_id": run_id}


def ask_on_page(queue: Queue):
    """The page's version of ask_in_terminal: the run stops, the chat shows Allow and Deny, and the answer comes back
    through /answer. No answer in five minutes counts as no."""

    def approve(name: str, inputs: dict) -> bool:
        ask_id = uuid.uuid4().hex[:8]
        answered, answer = threading.Event(), {"allow": False}
        ASKS[ask_id] = (answered, answer)
        queue.put({"type": "ask", "id": ask_id, "name": name, "inputs": inputs})
        answered.wait(ASK_WAIT)
        ASKS.pop(ask_id, None)
        return answer["allow"]

    return approve


@app.post("/answer/{ask_id}")
def answer(ask_id: str, body: Answer):
    if ask_id not in ASKS:
        raise HTTPException(404, "that question is no longer open")
    answered, answer = ASKS[ask_id]
    answer["allow"] = body.allow
    answered.set()
    return {"ok": True}


def new_files(current, since: float) -> list[str]:
    """Pictures and sounds the run wrote under data/, as page addresses."""
    found = [p for p in current.data_dir.rglob("*") if p.suffix.lower() in MEDIA and p.stat().st_mtime >= since]
    return [f"/files/{p.relative_to(current.data_dir).as_posix()}" for p in sorted(found)]


def refuse_bad_workspace(body: RunBody, current) -> str | None:
    """Step 4's check, run before any conversation file is opened, so a bad id never reads or rewrites another brand's history."""
    try:
        resolve_workspace_id(Request(workspace_id=body.workspace_id, user_id=body.user_id, session_id="check", text=body.text), current)
    except UnknownWorkspace as error:
        return str(error)
    return None


def _echo(trace: Trace, heading: str):
    """Print the trace in the terminal that runs `launchkit ui`, line by line as it happens, the same lines as the Trace tab."""
    print(f"\n{heading}", flush=True)
    trace.listeners.append(lambda event: print("  " + trace.line(event), flush=True))


def _worker(body: RunBody, queue: Queue):
    trace = Trace()
    trace.listeners.append(lambda event: queue.put({"type": "trace", "kind": event.kind, "detail": event.detail, "line": trace.line(event)}))
    _echo(trace, f'run · {body.workspace_id} · {body.user_id} · "{body.text}"')
    current = replace(settings, model=body.model) if body.model else settings
    refusal = refuse_bad_workspace(body, current)
    if refusal:
        queue.put({"type": "error", "kind": "UnknownWorkspace", "message": refusal})
        queue.put(DONE)
        return
    conversation = _load_conversation(body.workspace_id, body.user_id, body.session_id)
    req = Request(workspace_id=body.workspace_id, user_id=body.user_id, session_id=conversation["session_id"], text=body.text)
    conversation["turns"].append({"role": "user", "text": body.text})
    started = time.time()
    try:
        result = run_main(req, settings=current, trace=trace, approve=ask_on_page(queue))
        answer = {
            "type": "result",
            "reply": result.reply,
            "files": new_files(current, started),
            "view": {"tool_tokens": result.view_tokens, "history_tokens": result.history_tokens, "seconds": round(result.seconds, 1)},
        }
        conversation["turns"].append({"role": "assistant", "reply": answer["reply"], "files": answer["files"]})
        queue.put(answer)
    except (UnknownWorkspace, SpecError) as error:
        conversation["turns"].append({"role": "error", "kind": type(error).__name__, "message": str(error)})
        queue.put({"type": "error", "kind": type(error).__name__, "message": str(error), "errors": getattr(error, "errors", None)})
    except Exception as error:
        conversation["turns"].append({"role": "error", "kind": type(error).__name__, "message": str(error)})
        queue.put({"type": "error", "kind": type(error).__name__, "message": str(error)})
    finally:
        _save_conversation(body.workspace_id, body.user_id, conversation)
        queue.put(DONE)


@app.post("/onboard")
async def start_onboard(model: str = Form(""), workspace_id: str = Form(""), pdf: UploadFile = File(...)):
    workspace_id = workspace_id.strip() or None
    if workspace_id is not None:
        try:
            workspace_root(workspace_id, settings)
        except UnknownWorkspace as error:
            raise HTTPException(404, str(error))
    run_id = uuid.uuid4().hex[:8]
    queue: Queue = Queue()
    RUNS[run_id] = queue
    uploads = settings.data_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    path = uploads / Path(pdf.filename or "brand-pack.pdf").name
    path.write_bytes(await pdf.read())
    threading.Thread(target=_onboard_worker, args=(path, workspace_id, model.strip() or None, queue), daemon=True).start()
    return {"run_id": run_id}


def _onboard_worker(path: Path, workspace_id: str | None, model: str | None, queue: Queue):
    trace = Trace()
    trace.listeners.append(lambda event: queue.put({"type": "trace", "kind": event.kind, "detail": event.detail, "line": trace.line(event)}))
    _echo(trace, f"onboard · {workspace_id or 'new brand'} · {path.name}")
    current = replace(settings, model=model) if model else settings
    try:
        written = onboard_workspace(path, workspace_id=workspace_id, settings=current, trace=trace)
        files = {p.name: p.read_text(encoding="utf-8") for p in written if p.name != "brand-book.md"}
        queue.put({"type": "onboarded", "workspace_id": written[0].parent.name, "files": files})
    except (UnknownWorkspace, ValueError) as error:
        queue.put({"type": "error", "kind": type(error).__name__, "message": str(error)})
    except Exception as error:
        queue.put({"type": "error", "kind": type(error).__name__, "message": str(error)})
    finally:
        queue.put(DONE)


@app.get("/library/{workspace_id}")
def library(workspace_id: str):
    try:
        return read_library(workspace_id, settings)
    except UnknownWorkspace as error:
        raise HTTPException(404, str(error))


@app.get("/library/{workspace_id}/assets/{name}")
def library_asset(workspace_id: str, name: str):
    try:
        return FileResponse(asset_path(workspace_id, name, settings))
    except (UnknownWorkspace, FileNotFoundError):
        raise HTTPException(404)


@app.get("/events/{run_id}")
async def events(run_id: str):
    queue = RUNS.get(run_id)
    if queue is None:
        raise HTTPException(404, "unknown run")

    async def stream():
        loop = asyncio.get_running_loop()
        while True:
            item = await loop.run_in_executor(None, queue.get)
            if item is DONE:
                RUNS.pop(run_id, None)
                yield "event: done\ndata: {}\n\n"
                return
            yield f"data: {json.dumps(item, default=str)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/outputs/{name}")
def output(name: str):
    path = settings.data_dir / "outputs" / Path(name).name
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


@app.get("/files/{name:path}")
def data_file(name: str):
    root = settings.data_dir.resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or path.suffix.lower() not in MEDIA or not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


@app.get("/explain")
def explain():
    path = settings.data_dir / "last_run.json"
    if not path.exists():
        return JSONResponse({"error": "no run yet"}, status_code=404)
    return json.loads(path.read_text(encoding="utf-8"))
