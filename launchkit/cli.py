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
        f"{result.history_tokens} tokens of history carried in · {result.memory_tokens} tokens of memory in the prompt · took {result.seconds:.1f} s"
    )
    return 0


def cmd_memories(args):
    """What the store holds for one person, as Agno returns it: their own rows, then the workspace's."""
    from launchkit.memory.long_term import everyone, memory_db, memories_for

    db = memory_db(settings, args.workspace, args.user)
    rows = memories_for(db, args.workspace, args.user)
    if not rows:
        console.print(f"No memories for {args.user} at {args.workspace}.")
        return 0
    for n, row in enumerate(rows, 1):
        whose = f"everyone at {args.workspace}" if row.user_id == everyone(args.workspace) else row.user_id
        console.print(f"{n:>2}. {row.memory}", highlight=False, markup=False)
        console.print(f"    [dim]{whose} · topics: {', '.join(row.topics or []) or 'none'}[/dim]", highlight=False)
    return 0


def cmd_store(args):
    """The one Db object Agno writes to, data/sessions.db, read as it is. With no table: every table and how many rows
    it holds. With a table: its rows, column by column, as Agno stored them (like sqlite3's .mode line)."""
    import sqlite3

    path = settings.data_dir / "sessions.db"
    if not path.exists():
        console.print("No store yet: run the agent once.")
        return 0
    with sqlite3.connect(path) as con:
        tables = [row[0] for row in con.execute("select name from sqlite_master where type = 'table' order by name")]
        if not args.table:
            table = Table("table", "rows")
            for name in tables:
                table.add_row(name, str(con.execute(f'select count(*) from "{name}"').fetchone()[0]))
            console.print(f"[bold]{path.relative_to(ROOT)}[/bold]")
            console.print(table)
            return 0
        name = args.table if args.table in tables else f"agno_{args.table}"
        if name not in tables:
            console.print(f"No table {args.table!r}. Tables: {', '.join(tables)}")
            return 1
        columns = [row[1] for row in con.execute(f'pragma table_info("{name}")')]
        if args.schema:
            table = Table("column", "type")
            for row in con.execute(f'pragma table_info("{name}")'):
                table.add_row(row[1], row[2])
            console.print(f"[bold]{name}[/bold]")
            console.print(table)
            return 0
        where, params = ("where user_id = ?", [args.user]) if args.user and "user_id" in columns else ("", [])
        order = "order by created_at" if "created_at" in columns else ""
        rows = con.execute(f'select * from "{name}" {where} {order} limit ?', [*params, args.limit]).fetchall()
    console.print(f"[bold]{name}[/bold] · {len(rows)} rows" + (f" for user_id {args.user}" if where else "") + (f" (first {args.limit})" if len(rows) == args.limit else ""))
    width = max(len(c) for c in columns)
    for n, row in enumerate(rows, 1):
        console.print(f"[dim]── row {n} ──[/dim]")
        for column, value in zip(columns, row):
            text = "NULL" if value is None else str(value)
            if not args.full and len(text) > 100:
                text = text[:100] + f"… ({len(text)} characters; --full shows all)"
            console.print(f"{column:<{width}}  {text}", highlight=False, markup=False)
    return 0


def cmd_seed_memories(args):
    from launchkit.memory.long_term import seed

    console.print(f"Seeded {seed(settings, args.workspace)} rows into {args.workspace}'s memory store.")
    return 0


def cmd_forget(args):
    """Empty the memory store for a workspace: everyone's rows and the workspace's. Sessions stay."""
    from launchkit.memory.long_term import everyone, memory_db
    from launchkit.brands.users import list_logins

    db = memory_db(settings, args.workspace, "")
    owners = [login["user_id"] for login in list_logins(settings) if login["workspace_id"] == args.workspace] + [everyone(args.workspace)]
    ids = [row.memory_id for owner in owners for row in db.get_user_memories(user_id=owner) or []]
    if ids:
        db.delete_user_memories(ids)
    console.print(f"Forgot {len(ids)} rows at {args.workspace}.")
    return 0


def cmd_replay(args):
    """Send each line of a file as one message, in one conversation, the way Maya typed them over a week."""
    from launchkit.agents.main_agent import run_main

    current = replace(settings, model=args.model) if args.model else settings
    lines = [line.strip() for line in Path(args.file).read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    for n, text in enumerate(lines, 1):
        req = Request(workspace_id=args.workspace, user_id=args.user, session_id=args.session, text=text)
        result = run_main(req, settings=current, trace=Trace())
        console.print(f"[bold]{n}. {args.user}[/bold] {text}", highlight=False)
        console.print(f"   {result.reply.splitlines()[0] if result.reply else ''}", highlight=False, markup=False)
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
MEM_STEPS = sorted(p.stem.removeprefix("test_") for p in (ROOT / "checks").glob("test_mem*.py"))
ORCH_GATE = ORCH_STEPS + [name for name in TOOLS_STEPS if name in ("tools3", "tools4", "tools5")]


def cmd_check(args):
    extra = ["onboard", "setup"]
    if args.step == "all":
        names = [f"step{n}" for n in range(5)] + extra
    elif args.step == "rag":
        names = RAG_STEPS
    elif args.step == "orch":
        names = ORCH_GATE
    elif args.step == "mem":
        names = MEM_STEPS
    else:
        names = [args.step if args.step in extra + RAG_STEPS + TOOLS_STEPS + ORCH_STEPS + MEM_STEPS else f"step{args.step}"]
    targets = [ROOT / "checks" / f"test_{name}.py" for name in names]
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
    uvicorn.run("launchkit.web.app:app", host="127.0.0.1", port=args.port, log_level="warning")
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

    check = sub.add_parser("check", help="prove a step with the fakes: check 0..4 or all; retrieval: check rag1.. or rag; orchestration: check orch0.. or orch; memory: check mem0.. or mem")
    check.add_argument("step", choices=["0", "1", "2", "3", "4", "onboard", "setup", "all", *RAG_STEPS, "rag", *TOOLS_STEPS, *ORCH_STEPS, "orch", *MEM_STEPS, "mem"])
    check.set_defaults(func=cmd_check)

    memories = sub.add_parser("memories", help="print what the memory store keeps for one person: their rows and the workspace's")
    memories.add_argument("workspace")
    memories.add_argument("--user", default="maya")
    memories.set_defaults(func=cmd_memories)

    store = sub.add_parser("store", help="read the agent's store, data/sessions.db: its tables, or one table's rows column by column")
    store.add_argument("table", nargs="?", help="a table, e.g. agno_memories, agno_sessions, agno_runs (the agno_ can be left out)")
    store.add_argument("--user", help="only rows with this user_id, e.g. maya, sam, harbor:everyone")
    store.add_argument("--schema", action="store_true", help="the table's columns and their types, not its rows")
    store.add_argument("--full", action="store_true", help="print long values (session_data, run_data) in full")
    store.add_argument("--limit", type=int, default=20, help="at most this many rows (default 20)")
    store.set_defaults(func=cmd_store)

    seed = sub.add_parser("seed-memories", help="write a month of memory rows into a workspace's store (memory step 3)")
    seed.add_argument("workspace")
    seed.set_defaults(func=cmd_seed_memories)

    forget = sub.add_parser("forget", help="empty a workspace's memory store, to run a step again from nothing")
    forget.add_argument("workspace")
    forget.set_defaults(func=cmd_forget)

    replay = sub.add_parser("replay", help="send each line of a file as one message in one conversation (memory step 4)")
    replay.add_argument("workspace")
    replay.add_argument("file")
    replay.add_argument("--user", default="maya")
    replay.add_argument("--session", default="week")
    replay.add_argument("--model", help="override LAUNCHKIT_MODEL, e.g. fake:memory")
    replay.set_defaults(func=cmd_replay)

    ui = sub.add_parser("ui", help="start the chat page")
    ui.add_argument("--port", type=int, default=8000)
    ui.set_defaults(func=cmd_ui)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
