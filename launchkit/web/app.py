import asyncio
import json
import re
import threading
import time
import uuid
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from queue import Queue

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi import Path as UrlPart
from fastapi import Request as HttpRequest
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from launchkit.agents.main_agent import run_main
from launchkit.brands.onboard import onboard_workspace
from launchkit.brands.request import Request, UnknownWorkspace, resolve_workspace_id
from launchkit.brands.users import list_logins
from launchkit.guardrails.poster_check import SpecError
from launchkit.knowledge.brand_library import asset_path, read_library, workspace_root
from launchkit.mcp.servers.notion import NotionServer, connected, log_in
from launchkit.memory.attached_pictures import Pictures
from launchkit.settings import settings
from launchkit.trace import Trace

app = FastAPI(title="LaunchKit")
HERE = Path(__file__).parent
RUNS: dict[str, Queue] = {}
ASKS: dict[str, tuple[threading.Event, dict]] = {}
DONE = object()
LOGINS_OPEN: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Future]] = {}
CONNECTING: dict[str, str] = {}
ASK_WAIT = 300
MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".mp3", ".wav"}
USER_ID = r"^[a-z0-9-]{1,32}$"  # a login name; it becomes a folder name under data/, so nothing else is accepted


class RunBody(BaseModel):
    workspace_id: str
    user_id: str = Field(pattern=USER_ID)
    text: str
    model: str | None = None
    off: list[str] | None = None  # models switched off for this message; None keeps LAUNCHKIT_DISABLED_MODELS
    session_id: str | None = None
    attached: list[str] = []


class Answer(BaseModel):
    allow: bool = False
    choice: str | None = None


class Person(BaseModel):
    workspace_id: str
    user_id: str = Field(pattern=USER_ID)


@app.get("/", response_class=HTMLResponse)
def index():
    return (HERE / "index.html").read_text(encoding="utf-8")


@app.get("/models")
def models():
    """The models the Model box offers (every model in the rank lists, then the fakes) and the ones switched off in .env."""
    from launchkit.adapters.models import FAKES
    from launchkit.adapters.ranking import JOBS, rank_list

    ranked = list(dict.fromkeys(name for job in JOBS for name in rank_list(job, settings)))
    return {"models": ranked + [f"fake:{name}" for name in ("memory", "tools", "brief") if name in FAKES], "off": sorted(settings.disabled_models)}


@app.post("/off")
def save_off(names: list[str]):
    """The chat page saves its Switched off box here on every change. Routing still uses what each message sends."""
    from launchkit.adapters.ranking import page_off_file

    path = page_off_file(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted({name.strip() for name in names if name.strip()})), encoding="utf-8")
    return {"ok": True}


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
    """The page's version of ask_in_terminal: the run stops, the chat shows Allow and Deny (or one button per choice,
    when the ask carries choices), and the answer comes back through /answer. No answer in five minutes counts as no."""

    def approve(name: str, inputs: dict) -> bool | str | None:
        ask_id = uuid.uuid4().hex[:8]
        answered, answer = threading.Event(), {"allow": False, "choice": None}
        ASKS[ask_id] = (answered, answer)
        queue.put({"type": "ask", "id": ask_id, "name": name, "inputs": inputs})
        answered.wait(ASK_WAIT)
        ASKS.pop(ask_id, None)
        return answer["choice"] if "choices" in inputs else answer["allow"]

    return approve


@app.post("/answer/{ask_id}")
def answer(ask_id: str, body: Answer):
    if ask_id not in ASKS:
        raise HTTPException(404, "that question is no longer open")
    answered, answer = ASKS[ask_id]
    answer["allow"], answer["choice"] = body.allow, body.choice
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
    if body.off is not None:  # the chat page's Switched off box, for this message
        current = replace(current, disabled_models=frozenset(name.strip() for name in body.off if name.strip()))
    if current.disabled_models:
        trace.note("switched off: " + ", ".join(sorted(current.disabled_models)))
    refusal = refuse_bad_workspace(body, current)
    if refusal:
        queue.put({"type": "error", "kind": "UnknownWorkspace", "message": refusal})
        queue.put(DONE)
        return
    conversation = _load_conversation(body.workspace_id, body.user_id, body.session_id)
    req = Request(workspace_id=body.workspace_id, user_id=body.user_id, session_id=conversation["session_id"], text=body.text)
    conversation["turns"].append({"role": "user", "text": body.text, "files": body.attached})
    started = time.time()
    try:
        result = run_main(req, settings=current, trace=trace, approve=ask_on_page(queue))
        answer = {
            "type": "result",
            "reply": result.reply,
            "files": new_files(current, started) + [f"/files/{p.relative_to(current.data_dir).as_posix()}" for p in result.kept],
            "view": {"tool_tokens": result.view_tokens, "history_tokens": result.history_tokens, "seconds": round(result.seconds, 1)},
            "memory_tokens": result.memory_tokens,
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


@app.post("/attach")
async def attach_picture(workspace_id: str = Form(...), user_id: str = Form(..., pattern=USER_ID), session_id: str = Form(...), picture: UploadFile = File(...)):
    """The marketer attached a picture to this conversation. The picture tools work on the newest one."""
    try:
        resolve_workspace_id(Request(workspace_id=workspace_id, user_id=user_id, session_id=session_id, text="attach"), settings)
    except UnknownWorkspace as error:
        raise HTTPException(404, str(error))
    if not re.fullmatch(r"[0-9a-f]{6}", session_id) or Path(picture.filename or "").suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(400, "attach a .png, .jpg or .webp picture to a conversation")
    uploads = settings.data_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    temp = uploads / Path(picture.filename).name
    temp.write_bytes(await picture.read())
    kept = Pictures(settings, workspace_id, user_id, session_id).attach(temp)
    return {"name": kept.name, "url": f"/files/{kept.relative_to(settings.data_dir).as_posix()}"}


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


@app.get("/connections/{workspace_id}/{user_id}")
def connections(workspace_id: str, user_id: str = UrlPart(pattern=USER_ID)):
    """What this person has connected, for the header button."""
    return {"board": settings.board, "notion": connected(settings, user_id), "status": CONNECTING.get(user_id, "")}


@app.post("/connect/notion")
def connect_notion(body: Person, request: HttpRequest):
    """Start this person's Notion login: the page opens the address this returns, Notion sends the browser back to
    /connect/notion/callback, and the login is done. Connecting writes nothing to their Notion."""
    redirect_uri = f"{str(request.base_url).rstrip('/')}/connect/notion/callback"
    ready, box = threading.Event(), {}

    async def send_to_notion(url: str):
        state = parse_qs(urlparse(url).query).get("state", [""])[0]
        LOGINS_OPEN[state] = (asyncio.get_running_loop(), asyncio.get_running_loop().create_future())
        box["url"], box["state"] = url, state
        ready.set()

    async def back_from_notion():
        loop, future = LOGINS_OPEN[box["state"]]
        return await asyncio.wait_for(future, timeout=300), box["state"]

    def run_login():
        CONNECTING[body.user_id] = "waiting for Notion"
        try:
            server = NotionServer(settings, body.user_id, redirect_uri, send_to_notion, back_from_notion)
            CONNECTING[body.user_id] = log_in(settings, body.user_id, server)
        except Exception as error:
            CONNECTING[body.user_id] = f"Not connected: {error or type(error).__name__}"
        finally:
            LOGINS_OPEN.pop(box.get("state", ""), None)
            ready.set()

    threading.Thread(target=run_login, daemon=True).start()
    ready.wait(60)
    if "url" in box:
        return {"url": box["url"]}
    return {"url": None, "status": CONNECTING.get(body.user_id, "")}


@app.get("/connect/notion/callback", response_class=HTMLResponse)
def notion_callback(code: str = "", state: str = "", error: str = ""):
    waiting = LOGINS_OPEN.get(state)
    if waiting is None:
        return "<p>This Notion login has ended. Go back to LaunchKit and press Connect Notion again.</p>"
    loop, future = waiting
    if code:
        loop.call_soon_threadsafe(future.set_result, code)
    else:
        loop.call_soon_threadsafe(future.set_exception, PermissionError(error or "Notion said no"))
    return "<p>Notion is connected. Go back to LaunchKit; you can close this tab.</p>"


@app.get("/explain")
def explain():
    path = settings.data_dir / "last_run.json"
    if not path.exists():
        return JSONResponse({"error": "no run yet"}, status_code=404)
    return json.loads(path.read_text(encoding="utf-8"))
