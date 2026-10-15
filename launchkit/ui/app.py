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

from launchkit.harness.onboard import onboard_workspace
from launchkit.harness.request import Request, UnknownWorkspace
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
    user_id: str = "maya"
    session_id: str = "web"
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


@app.post("/run")
def start_run(body: RunBody):
    run_id = uuid.uuid4().hex[:8]
    queue: Queue = Queue()
    RUNS[run_id] = queue
    threading.Thread(target=_worker, args=(body, queue), daemon=True).start()
    return {"run_id": run_id}


def _worker(body: RunBody, queue: Queue):
    trace = Trace()
    trace.listeners.append(lambda event: queue.put({"type": "trace", "kind": event.kind, "detail": event.detail, "line": trace.lines()[-1]}))
    current = replace(settings, model=body.model) if body.model else settings
    req = Request(workspace_id=body.workspace_id, user_id=body.user_id, session_id=body.session_id, text=body.text)
    try:
        result = run_request(req, settings=current, trace=trace)
        queue.put(
            {
                "type": "result",
                "reply": result.reply,
                "spec": result.spec.model_dump() if result.spec else None,
                "image": f"/outputs/{result.image.name}" if result.image else None,
                "explain": json.loads((current.data_dir / "last_run.json").read_text(encoding="utf-8")),
            }
        )
    except (UnknownWorkspace, SpecError) as error:
        queue.put({"type": "error", "kind": type(error).__name__, "message": str(error), "errors": getattr(error, "errors", None)})
    except Exception as error:
        queue.put({"type": "error", "kind": type(error).__name__, "message": str(error)})
    finally:
        queue.put(DONE)


@app.post("/onboard")
async def start_onboard(model: str = Form(""), pdf: UploadFile = File(...)):
    run_id = uuid.uuid4().hex[:8]
    queue: Queue = Queue()
    RUNS[run_id] = queue
    uploads = settings.data_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    path = uploads / Path(pdf.filename or "brand-pack.pdf").name
    path.write_bytes(await pdf.read())
    threading.Thread(target=_onboard_worker, args=(path, model.strip() or None, queue), daemon=True).start()
    return {"run_id": run_id}


def _onboard_worker(path: Path, model: str | None, queue: Queue):
    trace = Trace()
    trace.listeners.append(lambda event: queue.put({"type": "trace", "kind": event.kind, "detail": event.detail, "line": trace.lines()[-1]}))
    current = replace(settings, model=model) if model else settings
    try:
        written = onboard_workspace(path, settings=current, trace=trace)
        files = {p.name: p.read_text(encoding="utf-8") for p in written if p.name != "brand-book.md"}
        queue.put({"type": "onboarded", "workspace_id": written[0].parent.name, "files": files})
    except (UnknownWorkspace, ValueError, FileExistsError) as error:
        queue.put({"type": "error", "kind": type(error).__name__, "message": str(error)})
    except Exception as error:
        queue.put({"type": "error", "kind": type(error).__name__, "message": str(error)})
    finally:
        queue.put(DONE)


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
