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

from launchkit.harness.request import Request, UnknownWorkspace
from launchkit.harness.run import run_request
from launchkit.harness.spec import SpecError
from launchkit.harness.trace import Trace
from launchkit.settings import ROOT, settings

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
    from launchkit.harness.main import run_main

    current = replace(settings, model=args.model) if args.model else settings
    req = Request(workspace_id=args.workspace, user_id=args.user, session_id=args.session, text=args.text)
    trace = Trace()
    try:
        result = run_main(req, settings=current, trace=trace)
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

    from launchkit.harness.brand import make_get_brand_details
    from launchkit.harness.context import approx_tokens
    from launchkit.harness.request import resolve_workspace_id
    from launchkit.harness.workspace import load_workspace

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
    from launchkit.harness.context import approx_tokens
    from launchkit.harness.request import resolve_workspace_id
    from launchkit.harness.search import load_chunks

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
    from launchkit.harness.store import index_brand

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
    from launchkit.harness.onboard import onboard_workspace

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
    from launchkit.harness.notion import set_up_card

    console.print(set_up_card(settings, args.user), highlight=False)
    console.print("\nThe Tidal card is in your Notion. With LAUNCHKIT_BOARD=notion the agent reaches it through Notion's MCP server.")
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


def cmd_check(args):
    extra = ["onboard", "setup"]
    if args.step == "all":
        names = [f"step{n}" for n in range(5)] + extra
    elif args.step == "rag":
        names = RAG_STEPS
    elif args.step == "orch":
        names = ORCH_GATE
    else:
        names = [args.step if args.step in extra + RAG_STEPS + TOOLS_STEPS + ORCH_STEPS else f"step{args.step}"]
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

    notion = sub.add_parser("notion", help="log in to Notion once and put the Tidal card in your Notion (the chat page has a Connect Notion button too)")
    notion.add_argument("--user", default="maya", help="whose Notion: a person id from the brand's users.yaml")
    notion.set_defaults(func=cmd_notion)

    explain = sub.add_parser("explain", help="what the model saw on the last run, in what order, at what cost")
    explain.add_argument("--show", action="store_true", help="print the system message as sent")
    explain.set_defaults(func=cmd_explain)

    check = sub.add_parser("check", help="prove a step with the fakes: check 0..4 or all; retrieval: check rag1.. or rag; orchestration: check orch0.. or orch")
    check.add_argument("step", choices=["0", "1", "2", "3", "4", "onboard", "setup", "all", *RAG_STEPS, "rag", *TOOLS_STEPS, *ORCH_STEPS, "orch"])
    check.set_defaults(func=cmd_check)

    ui = sub.add_parser("ui", help="start the chat page")
    ui.add_argument("--port", type=int, default=8000)
    ui.set_defaults(func=cmd_ui)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
