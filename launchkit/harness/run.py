import json
from dataclasses import dataclass, field
from pathlib import Path

from launchkit.adapters.images import FromPicture, make_images
from launchkit.adapters.models import model_name, resolve_model
from launchkit.adapters.pricing import cost_usd
from agno.exceptions import ModelProviderError
from agno.run.base import RunStatus

from launchkit.harness.agent import build_copy_agent, build_picture_agent
from launchkit.harness.context import ContextBuilder, approx_tokens
from launchkit.harness.request import Request, resolve_workspace_id
from launchkit.harness.spec import PosterSpec, SpecError, Turn, repair_message, validate_spec
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import load_workspace
from launchkit.settings import settings as default_settings


@dataclass
class Result:
    spec: PosterSpec | None = None
    reply: str | None = None
    image: Path | None = None
    trace: Trace = field(default_factory=Trace)
    context: list[dict] = field(default_factory=list)
    history_tokens: int = 0
    history_messages: int = 0
    runs: list = field(default_factory=list)


def run_request(
    req: Request,
    *,
    settings=default_settings,
    model=None,
    images=None,
    trace: Trace | None = None,
    facts: str | None = None,
    previous: dict | None = None,
) -> Result:
    trace = trace if trace is not None else Trace()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    wid = resolve_workspace_id(req, settings)
    ws = load_workspace(wid, settings, trace)
    ctx = ContextBuilder(settings.budgets)
    if facts:
        ctx.set("facts", facts)
    model = model if model is not None else resolve_model(settings, trace)
    images = images if images is not None else make_images(settings)
    result = Result(trace=trace)

    agent = build_copy_agent(ws, ctx, model, settings, trace)
    result.context = ctx.report()
    trace.context(result.context)
    session = f"{wid}:{req.user_id}:{req.session_id}"
    run = agent.run(req.text, session_id=session, user_id=req.user_id)
    result.runs.append(run)
    raise_if_failed(run)
    trace.model("copy", model_name(model), run.metrics)
    result.history_tokens, result.history_messages = history_size(run)

    turn = as_turn(run.content)
    if turn.kind == "reply" or turn.spec is None:
        result.reply = turn.reply or "I can help with posters. Tell me the concept."
        trace.add("reply", text=result.reply)
        write_explain(settings, result, wid, model_name(model))
        return result
    spec = turn.spec
    trace.draft(spec)
    errors = validate_spec(spec, ws.rules)
    if errors:
        trace.validation(errors, attempt=1)
        run = agent.run(repair_message(errors), session_id=session, user_id=req.user_id)
        result.runs.append(run)
        trace.model("repair", model_name(model), run.metrics)
        spec = as_turn(run.content).spec or spec
        errors = validate_spec(spec, ws.rules)
        trace.validation(errors, attempt=2)
        if errors:
            raise SpecError(errors)
    result.spec = spec
    write_explain(settings, result, wid, model_name(model))

    kept = Path(previous["image"]) if previous and previous.get("image") else None
    if kept and previous.get("image_prompt") == spec.image_prompt and kept.exists():
        result.image = kept
        trace.picture("reused", file=str(kept), reason="the image prompt did not change")
        return result

    if kept and kept.exists():
        images = FromPicture(images, kept)
    picture_agent = build_picture_agent(spec, model, images, ws.colours, trace, settings)
    if picture_agent is None:
        trace.picture("skipped", reason="the image tool is step 3")
        return result
    if isinstance(images, FromPicture):
        trace.picture("rework", file=str(kept), reason="the image prompt changed, so the new picture starts from this one")
    picture_run = picture_agent.run(spec.image_prompt, session_id=f"{session}:picture", user_id=req.user_id)
    result.runs.append(picture_run)
    raise_if_failed(picture_run)
    trace.model("picture", model_name(model), picture_run.metrics)
    files = [e.detail["result"].get("file") for e in trace.tool_calls("generate_image") if e.kind == "tool"]
    files = [f for f in files if f]
    result.image = Path(files[-1]) if files else None
    trace.picture("done" if result.image else "none", file=str(result.image) if result.image else None)
    return result


def raise_if_failed(run) -> None:
    """Agno hands a provider error back as a failed run with the message as its content; make it an error again."""
    if getattr(run, "status", None) == RunStatus.error:
        raise ModelProviderError(str(run.content))


def as_turn(content) -> Turn:
    if isinstance(content, Turn):
        return content
    if isinstance(content, PosterSpec):
        return Turn(kind="poster", spec=content)
    if isinstance(content, dict):
        return Turn.model_validate(content)
    if isinstance(content, str):
        try:
            return Turn.model_validate_json(content)
        except ValueError:
            raise ModelProviderError(content)
    raise SpecError([f"the model returned {type(content).__name__}, not a turn"])


def history_size(run) -> tuple[int, int]:
    earlier = [m for m in (run.messages or []) if getattr(m, "from_history", False)]
    return approx_tokens(" ".join(str(m.content or "") for m in earlier)), len(earlier)


def tool_result_size(run) -> tuple[int, int]:
    results = [m for m in (run.messages or []) if m.role == "tool" and not getattr(m, "from_history", False)]
    return approx_tokens(" ".join(str(m.content or "") for m in results)), len(results)


def write_explain(settings, result: Result, workspace_id: str, model_id: str):
    run = result.runs[-1]
    metrics = run.metrics
    payload = {
        "run_id": run.run_id,
        "workspace": workspace_id,
        "model": model_id,
        "sections": result.context,
        "history_tokens": result.history_tokens,
        "history_messages": result.history_messages,
        "tool_tokens": tool_result_size(run)[0],
        "tool_results": tool_result_size(run)[1],
        "input_tokens": getattr(metrics, "input_tokens", 0) or 0,
        "cached_tokens": getattr(metrics, "cache_read_tokens", 0) or 0,
        "output_tokens": getattr(metrics, "output_tokens", 0) or 0,
        "system_message": next((m.content for m in (run.messages or []) if m.role == "system"), ""),
    }
    payload["cost_usd"] = cost_usd(model_id, payload["input_tokens"], payload["cached_tokens"], payload["output_tokens"])
    (settings.data_dir / "last_run.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
