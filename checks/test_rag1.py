import inspect

from launchkit.harness.agent import build_copy_agent
from launchkit.harness.brand import make_get_brand_details
from launchkit.harness.context import ContextBuilder
from launchkit.harness.run import run_request
from launchkit.harness.trace import Trace
from launchkit.harness.workspace import load_workspace

DISHWASHER = "Poster for the Tidal bottle. Mention it's dishwasher-safe."


def test_the_tool_is_registered_on_the_copy_agent(settings, good):
    """get_brand_details is a tool on the copy agent, so the agent can look the brand up when a task needs it."""
    trace = Trace()
    ws = load_workspace("harbor", settings, trace)
    agent = build_copy_agent(ws, ContextBuilder(settings.budgets), good, settings, trace)
    assert "get_brand_details" in [getattr(t, "__name__", getattr(t, "name", "")) for t in agent.tools]


def test_the_tool_takes_no_workspace_argument(settings):
    """The model never names the workspace: the harness binds it from the trusted request."""
    tool = make_get_brand_details(load_workspace("harbor", settings, Trace()), Trace())
    assert "workspace" not in str(inspect.signature(tool))


def test_the_tool_reads_the_requesting_workspaces_brand_file(settings, images, trace, request_for, lookup):
    """A Harbor request reads Harbor's brand book; an Ember request reads Ember's file and never sees Harbor's."""
    run_request(request_for(text=DISHWASHER), settings=settings, model=lookup, images=images, trace=trace)
    assert any(path.endswith("harbor/brand-book.md") for path in trace.files_read())
    ember = Trace()
    run_request(request_for(workspace_id="ember", user_id="jonas", text="Poster for Night Shift"), settings=settings, model=lookup, images=images, trace=ember)
    result = str(ember.tool_calls("get_brand_details")[0].detail["result"])
    assert "Night Shift" in result and "Tidal" not in result and "Harbor" not in result


def test_the_dishwasher_copy_is_now_correct(settings, images, trace, request_for, lookup):
    """'Mention it's dishwasher-safe': body yes, lid no. The copy says the lid is hand-wash only, never 'fully dishwasher-safe'."""
    result = run_request(request_for(text=DISHWASHER), settings=settings, model=lookup, images=images, trace=trace)
    copy = f"{result.spec.headline} {result.spec.subheadline} {result.spec.body}".lower()
    assert "lid is hand-wash only" in copy
    assert "fully dishwasher-safe" not in copy


def test_without_the_tool_the_copy_is_plausible_not_true(settings, images, trace, request_for, lookup, monkeypatch):
    """The failure the tool fixes: with no way to look the brand up, the same model writes the banned claim."""
    import launchkit.harness.agent as agent
    from launchkit.harness.spec import SpecError
    import pytest

    monkeypatch.setattr(agent, "make_get_brand_details", lambda ws, trace: (lambda: "This brand has no brand guide or facts on file."))
    with pytest.raises(SpecError, match="fully dishwasher-safe"):
        run_request(request_for(text=DISHWASHER), settings=settings, model=lookup, images=images, trace=trace)


def test_lookup_prints_what_the_model_gets_back(settings, monkeypatch, capsys):
    """`launchkit lookup harbor` calls the tool the way the agent would and prints exactly what comes back."""
    import launchkit.cli as cli

    monkeypatch.setattr(cli, "settings", settings)
    assert cli.main(["lookup", "harbor", "Is the lid dishwasher-safe?", "--full"]) == 0
    out = capsys.readouterr().out
    assert "This is what the model reads" in out and "hand-wash only" in out


def test_the_trace_shows_the_tool_output_in_tokens(settings, images, trace, request_for, lookup):
    """The trace has the tool call with its result size in tokens, and explain counts it as a row."""
    import json

    run_request(request_for(text=DISHWASHER), settings=settings, model=lookup, images=images, trace=trace)
    call = trace.tool_calls("get_brand_details")[0]
    assert call.detail["result_tokens"] > 500, "v1 returns the whole guide"
    assert any(line.startswith("tool      get_brand_details") and "tokens back" in line for line in trace.lines())
    explain = json.loads((settings.data_dir / "last_run.json").read_text())
    assert explain["tool_results"] >= 1 and explain["tool_tokens"] > 500


def test_the_page_shows_the_tool_results_and_the_terminal_prints_the_trace(settings, monkeypatch, capsys):
    """The Context tab has a tool results row, and `launchkit ui` prints each run's trace in its terminal, tool call and size included."""
    from queue import Queue

    from launchkit.settings import ROOT
    import launchkit.web.app as web

    page = (ROOT / "launchkit" / "web" / "index.html").read_text(encoding="utf-8")
    assert "<td>tool results</td>" in page and "x.tool_tokens" in page
    monkeypatch.setattr(web, "settings", settings)
    web._worker(web.RunBody(workspace_id="harbor", user_id="maya", text=DISHWASHER, model="fake:lookup"), Queue())
    out = capsys.readouterr().out
    assert 'run · harbor · maya · "' in out and "tool      get_brand_details" in out and "tokens back" in out
