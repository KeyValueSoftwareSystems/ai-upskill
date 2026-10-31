from launchkit.harness.board import Board
from launchkit.harness.board_server import make_board_server
from launchkit.harness.catalogue import load_skills
from launchkit.harness.main import build_catalogue, run_main
from launchkit.harness.mcp_link import McpLink
from launchkit.harness.trace import Trace

NO = lambda name, inputs: False
YES = lambda name, inputs: True


def test_the_board_server_lists_its_own_tools():
    """Over MCP, the board's server lists its tools, each with a description, a schema, and whether it only reads."""
    tools = {t.name: t for t in McpLink(make_board_server(Board())).list_tools()}
    assert set(tools) == {"read_card", "attach_files", "update_status", "remove_files"}
    assert all(t.description and t.inputSchema.get("properties") for t in tools.values())
    assert tools["read_card"].annotations.readOnlyHint is True
    assert tools["remove_files"].annotations.readOnlyHint is False


def test_the_board_tools_join_the_catalogue_with_read_or_write():
    """connect turns each MCP tool into a catalogue entry: its description is the note, read or write comes from the server."""
    kinds = {e.name: e.kind for e in Board().entries()}
    assert kinds == {"read_card": "read", "attach_files": "write", "update_status": "write", "remove_files": "write"}


def test_run_tool_reads_the_tidal_card_over_mcp(settings):
    """run_tool runs an MCP tool like any other: the Tidal card's brief comes back from the board's server."""
    card = build_catalogue(settings, Trace(), NO, Board()).make_run_tool()("read_card", {"card": "tidal"})
    assert "Tidal launch" in card and "Klean Kanteen" in card and "approved.png" in card


def test_an_mcp_write_changes_the_board(settings):
    """A write through MCP changes Maya's board."""
    board = Board()
    build_catalogue(settings, Trace(), YES, board).make_run_tool()("update_status", {"card": "tidal", "status": "Ready for review"})
    assert board.cards["tidal"]["status"] == "Ready for review"


def test_the_post_to_board_skill_writes_harbors_routine_down():
    """Ready-made: post_to_board says when to pick it and names the board's tools in order."""
    skill = load_skills()["post_to_board"]
    assert "board" in skill.note.lower()
    text = skill.text
    assert text.index("read_card") < text.index("attach_files") < text.index("update_status")


def test_the_main_agent_puts_the_sizes_on_the_card(settings, request_for):
    """Asked to put the sizes on the Tidal card, the main agent loads post_to_board and the files land on the card."""
    from launchkit.adapters.fakes import ToolsModel

    board, trace = Board(), Trace()
    run_main(request_for(text="Put the new sizes on the Tidal card."), settings=settings, model=ToolsModel(), trace=trace, approve=YES, board=board)
    assert [e.detail["arguments"] for e in trace.tool_calls("run_skill")] == [{"name": "post_to_board"}]
    assert "tidal-1080x1920.png" in board.cards["tidal"]["files"]


def test_a_person_without_a_notion_login_gets_no_board_tools_and_no_browser(settings, monkeypatch):
    """Ready-made: a run never starts a Notion login. Nobody connected: no board tools, a note in the trace, no wait."""
    from dataclasses import replace

    import launchkit.harness.notion as notion

    monkeypatch.setattr(notion.webbrowser, "open", lambda url: (_ for _ in ()).throw(AssertionError("opened a browser")))
    trace = Trace()
    assert notion.make_board(replace(settings, board="notion"), trace, "sam").entries() == []
    assert any("Notion is not connected for sam" in line for line in trace.lines())


def test_each_person_keeps_their_own_notion_login(settings):
    """Ready-made: Maya's login is hers. Sam is still not connected, and the file sits under data/users/<id>/."""
    import asyncio
    import json

    import launchkit.harness.notion as notion

    path = notion.auth_file(settings, "maya")
    assert path == settings.data_dir / "users" / "maya" / "notion-auth.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"tokens": {"access_token": "t", "token_type": "Bearer"}}))
    assert notion.connected(settings, "maya") and not notion.connected(settings, "sam")
    registered = {"client_id": "c", "redirect_uris": ["http://localhost:8765/callback"]}
    path.write_text(json.dumps({"client": registered}))
    page = notion.FileTokens(path, "http://localhost:8000/connect/notion/callback")
    terminal = notion.FileTokens(path, "http://localhost:8765/callback")
    assert asyncio.run(page.get_client_info()) is None and asyncio.run(terminal.get_client_info()).client_id == "c"
