import asyncio
import json
import threading
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
from launchkit.harness.run import run_request
from launchkit.harness.spec import SpecError
from launchkit.harness.trace import Trace
from launchkit.harness.users import list_logins
from launchkit.settings import settings

app = FastAPI(title="LaunchKit")
HERE = Path(__file__).parent
RUNS: dict[str, Queue] = {}
DONE = object()


class RunBody(BaseModel):
    workspace_id: str
    user_id: str
    text: str
    model: str | None = None


@app.get("/", response_class=HTMLResponse)
def index():
    return (HERE / "index.html").read_text(encoding="utf-8")


@app.get("/workspaces")
def workspaces():
    return sorted(p.name for p in settings.workspaces_dir.iterdir() if p.is_dir())


@app.get("/logins")
def logins():
    return list_logins(settings)


def _conversation_file(workspace_id: str, user_id: str) -> Path:
    safe = Path(workspace_id).name, Path(user_id).name
    return settings.data_dir / "conversations" / safe[0] / f"{safe[1]}.json"


def _load_conversation(workspace_id: str, user_id: str) -> dict:
    path = _conversation_file(workspace_id, user_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"session_id": uuid.uuid4().hex[:6], "turns": []}


def _save_conversation(workspace_id: str, user_id: str, data: dict):
    path = _conversation_file(workspace_id, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


@app.get("/conversations/{workspace_id}/{user_id}")
def conversation(workspace_id: str, user_id: str):
    data = _load_conversation(workspace_id, user_id)
    _save_conversation(workspace_id, user_id, data)
    return data


@app.post("/conversations/{workspace_id}/{user_id}/new")
def new_conversation(workspace_id: str, user_id: str):
    data = {"session_id": uuid.uuid4().hex[:6], "turns": []}
    _save_conversation(workspace_id, user_id, data)
    return data


@app.post("/run")
def start_run(body: RunBody):
    run_id = uuid.uuid4().hex[:8]
    queue: Queue = Queue()
    RUNS[run_id] = queue
    threading.Thread(target=_worker, args=(body, queue), daemon=True).start()
    return {"run_id": run_id}


def _previous_picture(conversation: dict, current) -> dict | None:
    for turn in reversed(conversation["turns"]):
        if turn.get("role") == "assistant" and turn.get("spec") and turn.get("image"):
            return {"image_prompt": turn["spec"].get("image_prompt"), "image": str(current.data_dir / "outputs" / Path(turn["image"]).name)}
    return None


def refuse_bad_workspace(body: RunBody, current) -> str | None:
    """Step 4's check, run before any conversation file is opened, so a bad id never reads or rewrites another brand's history."""
    try:
        resolve_workspace_id(Request(workspace_id=body.workspace_id, user_id=body.user_id, session_id="check", text=body.text), current)
    except UnknownWorkspace as error:
        return str(error)
    return None


def _worker(body: RunBody, queue: Queue):
    trace = Trace()
    trace.listeners.append(lambda event: queue.put({"type": "trace", "kind": event.kind, "detail": event.detail, "line": trace.lines()[-1]}))
    current = replace(settings, model=body.model) if body.model else settings
    refusal = refuse_bad_workspace(body, current)
    if refusal:
        queue.put({"type": "error", "kind": "UnknownWorkspace", "message": refusal})
        queue.put(DONE)
        return
    conversation = _load_conversation(body.workspace_id, body.user_id)
    req = Request(workspace_id=body.workspace_id, user_id=body.user_id, session_id=conversation["session_id"], text=body.text)
    conversation["turns"].append({"role": "user", "text": body.text})
    try:
        result = run_request(req, settings=current, trace=trace, previous=_previous_picture(conversation, current))
        answer = {
            "type": "result",
            "reply": result.reply,
            "spec": result.spec.model_dump() if result.spec else None,
            "image": f"/outputs/{result.image.name}" if result.image else None,
            "explain": json.loads((current.data_dir / "last_run.json").read_text(encoding="utf-8")),
        }
        conversation["turns"].append({"role": "assistant", "reply": answer["reply"], "spec": answer["spec"], "image": answer["image"]})
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
    trace.listeners.append(lambda event: queue.put({"type": "trace", "kind": event.kind, "detail": event.detail, "line": trace.lines()[-1]}))
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


@app.get("/explain")
def explain():
    path = settings.data_dir / "last_run.json"
    if not path.exists():
        return JSONResponse({"error": "no run yet"}, status_code=404)
    return json.loads(path.read_text(encoding="utf-8"))
