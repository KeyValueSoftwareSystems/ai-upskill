"""LaunchKit's commands. Session 3 adds setup, forget, retention, models, and ui --reload.

Ready-made for every ticket. Reference: READY-MADE.md.
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from rich.console import Console
from rich.table import Table

from launchkit.adapters.pricing import PRICES_AS_OF
from agno.exceptions import ModelProviderError

from launchkit.agents.poster_flow import run_request
from launchkit.brands.request import Request, UnknownWorkspace
from launchkit.guardrails.poster_check import SpecError
from launchkit.settings import ROOT, settings
from launchkit.trace import Trace

console = Console(soft_wrap=True)


def cmd_run(args):
    current = replace(settings, model=args.model) if args.model else settings
    facts = Path(args.facts).read_text(encoding="utf-8") if args.facts else None
    req = Request(workspace_id=args.workspace, user_id=args.user, session_id=args.session, text=args.text)
    trace = Trace()
    console.print("[bold]what happened[/bold]")
    trace.listeners.append(lambda event: console.print("  " + trace.line(event), highlight=False))
    try:
        result = run_request(req, settings=current, trace=trace, facts=facts)
    except (UnknownWorkspace, SpecError) as error:
        console.print(f"\n[red]{type(error).__name__}[/red]  {error}")
        return 1
    except ModelProviderError as error:
        console.print(f"\n[red]model error[/red]  {error.message}", highlight=False)
        return 1
    if result.reply:
        console.print(f"\n[bold]reply[/bold]  {result.reply}")
        return 0
    console.print("\n[bold]the spec the model filled in[/bold]")
    for name, value in result.spec.model_dump().items():
        console.print(f"  {name:<13} {value}", highlight=False)
    if result.image:
        console.print(f"\n[bold]picture[/bold]  {result.image}")
    return 0


def cmd_main(args):
    from launchkit.agents.main_agent import run_main

    current = replace(settings, model=args.model) if args.model else settings
    req = Request(workspace_id=args.workspace, user_id=args.user, session_id=args.session, text=args.text)
    trace = Trace()
    try:
        result = run_main(req, settings=current, trace=trace, attach=args.attach)
    except UnknownWorkspace as error:
        print_trace(trace)
        console.print(f"\n[red]{type(error).__name__}[/red]  {error}")
        return 1
    except ModelProviderError as error:
        print_trace(trace)
        console.print(f"\n[red]model error[/red]  {error.message}", highlight=False)
        return 1
    print_trace(trace)
    console.print("\n[bold]reply[/bold]")
    console.print(result.reply, highlight=False, markup=False)
    console.print(
        f"\n[bold]main agent's view[/bold]  {result.view_tokens} tokens of tool results this turn · "
        f"{result.history_tokens} tokens of history carried in · took {result.seconds:.1f} s"
    )
    return 0


def print_trace(trace: Trace):
    console.print("[bold]what happened[/bold]")
    for line in trace.lines():
        console.print("  " + line, highlight=False)


def cmd_lookup(args):
    """Call get_brand_details the way the agent would, and print exactly what the model gets back."""
    import inspect

    from launchkit.tools.get_brand_details import make_get_brand_details
    from launchkit.agents.prompt import approx_tokens
    from launchkit.brands.request import resolve_workspace_id
    from launchkit.brands.workspace import load_workspace

    trace = Trace()
    try:
        wid = resolve_workspace_id(Request(workspace_id=args.workspace, text=args.query or "lookup"), settings)
    except UnknownWorkspace as error:
        console.print(f"[red]UnknownWorkspace[/red]  {error}")
        return 1
    ws = load_workspace(wid, settings, Trace())
    extra = {"settings": settings} if "settings" in inspect.signature(make_get_brand_details).parameters else {}
    tool = make_get_brand_details(ws, trace, **extra)
    takes_query = bool(inspect.signature(tool).parameters)
    call = f'get_brand_details("{args.query}")' if takes_query else "get_brand_details()"
    result = tool(args.query) if takes_query else tool()
    print_trace(trace)
    lines = result.splitlines()
    console.print(f"\n[bold]{call} returns {approx_tokens(result)} tokens, {len(lines)} lines. This is what the model reads:[/bold]\n")
    shown = lines if args.full or len(lines) <= 60 else lines[:40]
    console.print("\n".join(shown), highlight=False, markup=False)
    if len(shown) < len(lines):
        console.print(f"\n[dim]… {len(lines) - len(shown)} more lines. --full prints them all.[/dim]")
    return 0


def cmd_chunks(args):
    """How a brand's guide is split before anything is searched: one row per chunk."""
    from launchkit.agents.prompt import approx_tokens
    from launchkit.brands.request import resolve_workspace_id
    from launchkit.knowledge.brand_search import load_chunks

    try:
        wid = resolve_workspace_id(Request(workspace_id=args.workspace, text="chunks"), settings)
    except UnknownWorkspace as error:
        console.print(f"[red]UnknownWorkspace[/red]  {error}")
        return 1
    chunks = load_chunks(settings.workspaces_dir / wid)
    table = Table(title=f"{wid}: {len(chunks)} chunks, one per ## section of brand-book.md and one per line of facts.md")
    table.add_column("#", justify="right")
    table.add_column("chunk id", no_wrap=True)
    table.add_column("tokens", justify="right")
    table.add_column("starts with", no_wrap=True, overflow="ellipsis")
    for n, chunk in enumerate(chunks, 1):
        table.add_row(str(n), chunk.ref, str(approx_tokens(f"{chunk.heading} {chunk.text}")), " ".join(chunk.text.split())[:60])
    console.print(table)
    if args.show:
        for chunk in chunks:
            console.print(f"\n[bold]{chunk.ref}[/bold]\n{chunk.text}", highlight=False)
    return 0


def cmd_index(args):
    """Document processing for brands whose files were written by hand: chunk, embed and store them once."""
    from launchkit.knowledge.brand_index import index_brand

    names = args.workspaces or sorted(p.name for p in settings.workspaces_dir.iterdir() if p.is_dir())
    trace = Trace()
    for name in names:
        try:
            index_brand(name, settings, trace)
        except UnknownWorkspace as error:
            console.print(f"[red]UnknownWorkspace[/red]  {error}")
            return 1
    print_trace(trace)
    return 0


def cmd_onboard(args):
    from launchkit.brands.onboard import onboard_workspace

    current = replace(settings, model=args.model) if args.model else settings
    trace = Trace()
    try:
        written = onboard_workspace(Path(args.pdf), workspace_id=args.id, settings=current, trace=trace)
    except (UnknownWorkspace, ValueError) as error:
        print_trace(trace)
        console.print(f"\n[red]{type(error).__name__}[/red]  {error}")
        return 1
    print_trace(trace)
    console.print(f"\n[bold]{len(written)} files written to {written[0].parent.relative_to(ROOT)}/[/bold]. Read them. The model drafted them; you own them.")
    return 0


def cmd_notion(args):
    from launchkit.mcp.servers.notion import log_in

    console.print(log_in(settings, args.user), highlight=False)
    console.print("\nWith LAUNCHKIT_BOARD=notion the agent reaches your Notion through Notion's MCP server when an ask needs the board.")
    return 0


def cmd_explain(args):
    path = settings.data_dir / "last_run.json"
    if not path.exists():
        console.print("No run yet. Run one first: uv run launchkit run harbor \"Poster for the Tidal bottle on a misty lakeshore at dawn.\"")
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    console.print(f"run {data['run_id'][:8]} · {data['workspace']} · {data['model']} · copy phase\n")
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("section")
    table.add_column("tokens", justify="right")
    table.add_column("budget", justify="right")
    table.add_column("")
    for row in data["sections"]:
        note = "(empty)" if row["given"] == 0 else (f"trimmed from {row['given']}" if row["trimmed"] else "")
        table.add_row(row["section"], str(row["tokens"]), str(row["budget"]), note)
    table.add_row("history", str(data["history_tokens"]), str(settings.budgets["history"]), f"{data['history_messages']} earlier messages")
    table.add_row("tool results", str(data.get("tool_tokens", 0)), "", f"{data.get('tool_results', 0)} tool calls this turn")
    console.print(table)
    cost = data.get("cost_usd")
    cost_text = f"${cost:.4f}" if cost is not None else "price unknown for this model"
    console.print(
        f"\ninput {data['input_tokens']} · cached {data['cached_tokens']} · output {data['output_tokens']} · {cost_text}"
        f"  (tokens per section are approximate: 4 characters each; totals are the provider's; prices as of {PRICES_AS_OF})"
    )
    if args.show:
        console.print("\n[bold]system message as sent[/bold]\n")
        console.print(data["system_message"], highlight=False, markup=False)
    return 0


RAG_STEPS = sorted(p.stem.removeprefix("test_") for p in (ROOT / "checks").glob("test_rag*.py"))
TOOLS_STEPS = sorted(p.stem.removeprefix("test_") for p in (ROOT / "checks").glob("test_tools*.py"))
ORCH_STEPS = sorted(p.stem.removeprefix("test_") for p in (ROOT / "checks").glob("test_orch*.py"))
ORCH_GATE = ORCH_STEPS + [name for name in TOOLS_STEPS if name in ("tools3", "tools4", "tools5")]

# Session 3 (alternative format). Participants never run these; they are the
# trainers' proof that the ready-made plumbing and the answer branches work.
ALT_CHECKS = ("alt-setup", "alt-ready", "alt-build-a", "alt-build-b", "alt-build-c")
CHECK_NAMES = ("0", "1", "2", "3", "4", "onboard", "setup", "all", *RAG_STEPS, "rag", *TOOLS_STEPS, *ORCH_STEPS, "orch", *ALT_CHECKS, "alt")
COMMANDS = ("run", "main", "lookup", "chunks", "index", "onboard", "notion", "explain", "check", "ui", "setup", "forget", "retention", "models")


def check_targets(step: str) -> list[Path]:
    """The test files `launchkit check <step>` runs, in order."""
    extra = ["onboard", "setup"]
    if step == "all":
        names = [f"step{n}" for n in range(5)] + extra
    elif step == "rag":
        names = RAG_STEPS
    elif step == "orch":
        names = ORCH_GATE
    elif step == "alt":
        names = ["alt_setup", "alt_ready"]
    elif step in ALT_CHECKS:
        names = [step.replace("-", "_")]
    elif step in extra + RAG_STEPS + TOOLS_STEPS + ORCH_STEPS:
        names = [step]
    else:
        names = [f"step{step}"]
    return [ROOT / "checks" / f"test_{name}.py" for name in names]


def cmd_check(args):
    targets = check_targets(args.step)
    command = [sys.executable, "-m", "pytest", "-q", "--tb=no", "-rN", "-p", "no:cacheprovider", *map(str, targets)]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    for line in proc.stdout.splitlines():
        if line.startswith("PASS"):
            console.print("[green]PASS[/green]  ", end="", highlight=False); console.print(line[6:], highlight=False, markup=False)
        elif line.startswith("FAIL"):
            console.print("[red]FAIL[/red]  ", end="", highlight=False); console.print(line[6:], highlight=False, markup=False)
    summary = re.search(r"(\d+ failed, )?\d+ passed|\d+ failed", proc.stdout)
    console.print(f"\n{summary.group(0) if summary else proc.stdout[-300:]}")
    if proc.returncode not in (0, 1):
        console.print(proc.stderr[-2000:])
    return proc.returncode


def cmd_ui(args):
    import uvicorn

    console.print(f"LaunchKit chat page: http://localhost:{args.port}")
    # --reload restarts the server when a file under launchkit/ changes, so a
    # participant sees their edit without stopping and starting the page.
    uvicorn.run(
        "launchkit.web.app:app",
        host="127.0.0.1",
        port=args.port,
        log_level="warning",
        reload=args.reload,
        reload_dirs=[str(ROOT / "launchkit")] if args.reload else None,
    )
    return 0


def _has_brand_facts(db_file: Path) -> bool:
    """True when a database already has the Session 3 tables."""
    import sqlite3

    with sqlite3.connect(db_file) as db:
        names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    return "brand_facts" in names


def _relative_to_root(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def cmd_setup(args):
    """Prepare a fresh clone for Session 3: the seeded database, the Alder brand and the rank file.

    Runs once. It copies nothing over an existing database, so running it
    again is safe.
    """
    import shutil

    import sqlite3

    problems = []
    seed = ROOT / "samples" / "memory" / "seed.db"
    target = settings.data_dir / "sessions.db"
    if target.exists() and not _has_brand_facts(target):
        # A Session 1 or 2 database. Keep it under another name, so nothing is lost, and seed the Session 3 start.
        kept = target.with_name("sessions.before-session-3.db")
        target.rename(kept)
        console.print(f"database      the earlier sessions' database is kept as {kept.name}")
    if target.exists():
        console.print(f"database      {_relative_to_root(target)} already there, left as it is")
    elif seed.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(seed, target)
        console.print(f"database      copied the seeded start to {_relative_to_root(target)}")
    else:
        problems.append(f"the seeded database is missing: {seed.relative_to(ROOT)}")
    alder = settings.workspaces_dir / "alder" / "users.yaml"
    if alder.exists():
        console.print("brands        Harbor, Ember and Alder")
    else:
        problems.append(f"the Alder brand is missing: {alder}")
    ranking = ROOT / "launchkit" / "ranking.json"
    try:
        json.loads(ranking.read_text(encoding="utf-8"))
        console.print(f"models        {ranking.relative_to(ROOT)} reads")
    except (OSError, ValueError) as error:
        problems.append(f"the rank file does not read: {error}")
    if problems:
        console.print(f"\n[red]Setup stopped[/red]  {problems[0]}")
        return 1
    console.print("\n[green]Setup complete[/green]  start the chat page with: uv run launchkit ui")
    return 0


def cmd_models(args):
    """Print the rank file: for every job, its models best first, with their scores, total and whether they are on."""
    from launchkit.adapters.ranking import job_table

    table = job_table(settings)
    for job, entry in table["jobs"].items():
        weights = " · ".join(f"{k} {v}" for k, v in entry["weights"].items())
        console.print(f"\n[bold]{job}[/bold]  {entry['about']}  (weights: {weights})")
        for rank, row in enumerate(entry["models"], 1):
            state = "" if row["enabled"] else "  [red]off[/red]"
            console.print(f"  {rank}. {row['model']:<20} eval {row['eval']:.2f} · cost {row['cost']:.2f} · latency {row['latency']:.2f} · total {row['total']:.3f}{state}", highlight=False)
    return 0


def cmd_forget(args):
    """Remove everything memory holds about some text for one person at one brand: `launchkit forget harbor maya "555-0142"`."""
    from launchkit.memory.forget import forget
    from launchkit.memory.store import open_store

    store = open_store(settings, args.workspace, args.user, Trace())
    try:
        result = forget(store, args.workspace, args.user, args.text)
    except ValueError as error:
        console.print(f"[red]{error}[/red]")
        return 1
    console.print(f"memories {result['memories']} · summaries {result['summaries']} · learnings {result['learnings']}")
    return 0


def cmd_retention(args):
    """Remove rows older than the limit for one brand: `launchkit retention harbor --days 180`."""
    from datetime import date

    from launchkit.memory.retention import prune
    from launchkit.memory.store import open_store

    store = open_store(settings, args.workspace, "retention", Trace())
    gone = prune(store, args.workspace, date.today(), max_age_days=args.days)
    console.print(f"removed {gone} rows older than {args.days} days")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="launchkit", description="LaunchKit harness commands")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run one request in the terminal")
    run.add_argument("workspace")
    run.add_argument("text")
    run.add_argument("--user", default="maya")
    run.add_argument("--session", default="terminal")
    run.add_argument("--model", help="override LAUNCHKIT_MODEL, e.g. fake:echo")
    run.add_argument("--facts", help="a text file to load into the facts section")
    run.set_defaults(func=cmd_run)

    main_agent = sub.add_parser("main", help="talk to the main agent: it finds skills and tools and runs them")
    main_agent.add_argument("workspace")
    main_agent.add_argument("text")
    main_agent.add_argument("--user", default="maya")
    main_agent.add_argument("--session", default="terminal")
    main_agent.add_argument("--model", help="override LAUNCHKIT_MODEL, e.g. fake:brief")
    main_agent.add_argument("--attach", action="append", default=[], metavar="FILE", help="attach a picture to the conversation, e.g. samples/approved/tidal-poster.jpg")
    main_agent.set_defaults(func=cmd_main)

    lookup = sub.add_parser("lookup", help="call get_brand_details as the agent would and print what the model gets back")
    lookup.add_argument("workspace")
    lookup.add_argument("query", nargs="?", default="", help="the question the agent would ask (from RAG step 2 on)")
    lookup.add_argument("--full", action="store_true", help="print the whole result, however long")
    lookup.set_defaults(func=cmd_lookup)

    chunks = sub.add_parser("chunks", help="show how a brand's guide is split into chunks")
    chunks.add_argument("workspace")
    chunks.add_argument("--show", action="store_true", help="print every chunk in full after the table")
    chunks.set_defaults(func=cmd_chunks)

    index = sub.add_parser("index", help="chunk, embed and store brand documents in the vector database (once per change)")
    index.add_argument("workspaces", nargs="*", help="brands to index; all of them when none is given")
    index.set_defaults(func=cmd_index)

    onboard = sub.add_parser("onboard", help="draft a workspace's files from a brand pack PDF")
    onboard.add_argument("pdf")
    onboard.add_argument("--id", help="the workspace to draft into; by default it is made from the brand name in the pack. An existing workspace has its drafted files replaced")
    onboard.add_argument("--model", help="override LAUNCHKIT_MODEL, e.g. fake:profile")
    onboard.set_defaults(func=cmd_onboard)

    notion = sub.add_parser("notion", help="log in to Notion once; it writes nothing (the chat page has a Connect Notion button too)")
    notion.add_argument("--user", default="maya", help="whose Notion: a person id from the brand's users.yaml")
    notion.set_defaults(func=cmd_notion)

    explain = sub.add_parser("explain", help="what the model saw on the last run, in what order, at what cost")
    explain.add_argument("--show", action="store_true", help="print the system message as sent")
    explain.set_defaults(func=cmd_explain)

    check = sub.add_parser("check", help="prove a step with the fakes: check 0..4 or all; retrieval: check rag1.. or rag; orchestration: check orch0.. or orch")
    check.add_argument("step", choices=list(CHECK_NAMES))
    check.set_defaults(func=cmd_check)

    ui = sub.add_parser("ui", help="start the chat page")
    ui.add_argument("--port", type=int, default=8000)
    ui.add_argument("--reload", action="store_true", help="restart the page when a file under launchkit/ changes")
    ui.set_defaults(func=cmd_ui)

    setup = sub.add_parser("setup", help="prepare a fresh clone for Session 3: the seeded database, the brands, the rank file")
    setup.set_defaults(func=cmd_setup)

    forget = sub.add_parser("forget", help="remove everything memory holds about some text, for one person at one brand")
    forget.add_argument("workspace")
    forget.add_argument("user")
    forget.add_argument("text")
    forget.set_defaults(func=cmd_forget)

    models = sub.add_parser("models", help="print the rank file: each job's models best first, with scores")
    models.set_defaults(func=cmd_models)

    retention = sub.add_parser("retention", help="remove a brand's rows older than a number of days")
    retention.add_argument("workspace")
    retention.add_argument("--days", type=int, default=180)
    retention.set_defaults(func=cmd_retention)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
