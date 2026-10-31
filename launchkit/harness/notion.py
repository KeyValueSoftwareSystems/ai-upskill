"""Maya's real board: Notion's hosted MCP server. Each person connects their own Notion once, from the chat page or
`launchkit notion --user <id>`; the login is kept in data/users/<id>/notion-auth.json, so later runs need no browser.
A run never starts a login: a person who has not connected gets no Notion tools. Notion lists 68 tools; the harness
plugs in only the ones a board job needs."""

import asyncio
import json
import webbrowser
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from launchkit.settings import ROOT

NOTION_MCP = "https://mcp.notion.com/mcp"
CALLBACK_PORT = 8765
BOARD_TOOLS = ("notion-search", "notion-fetch", "notion-update-page", "notion-create-comment", "notion-get-comments", "notion-delete-pages")
CARD = ROOT / "samples" / "board" / "tidal.md"
TERMINAL_CALLBACK = f"http://localhost:{CALLBACK_PORT}/callback"


class NotConnected(Exception):
    pass


def auth_file(settings, user: str):
    return settings.data_dir / "users" / user / "notion-auth.json"


def connected(settings, user: str) -> bool:
    return bool(FileTokens(auth_file(settings, user)).read().get("tokens"))


class FileTokens(TokenStorage):
    def __init__(self, path, redirect_uri: str | None = None):
        self.path = path
        self.redirect_uri = redirect_uri

    def read(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def write(self, key: str, value):
        data = self.read()
        data[key] = value.model_dump(mode="json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data))
        self.path.chmod(0o600)

    async def get_tokens(self):
        found = self.read().get("tokens")
        return OAuthToken(**found) if found else None

    async def set_tokens(self, tokens):
        self.write("tokens", tokens)

    async def get_client_info(self):
        found = self.read().get("client")
        if found and self.redirect_uri and self.redirect_uri not in found.get("redirect_uris", []):
            return None  # registered for the other way in (page or terminal): register again for this one
        return OAuthClientInformationFull(**found) if found else None

    async def set_client_info(self, client_info):
        self.write("client", client_info)


async def no_login(*_):
    raise NotConnected("Notion is not connected")


async def open_browser(url: str):
    print("Opening the browser to log in to Notion. Pick the workspace for the session.")
    webbrowser.open(url)


async def wait_for_login() -> tuple[str, str | None]:
    got = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            got["code"], got["state"] = query.get("code", [""])[0], query.get("state", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Logged in to Notion. You can close this tab.")

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", CALLBACK_PORT), Callback)
    await asyncio.to_thread(server.handle_request)
    server.server_close()
    return got["code"], got["state"]


class NotionServer:
    """What McpLink connects to for the real board: Notion's server over HTTP, logged in as one person. With no
    redirect_uri it never asks for a login; a missing or dead login raises NotConnected."""

    only = BOARD_TOOLS

    def __init__(self, settings, user: str, redirect_uri: str | None = None, redirect_handler=no_login, callback_handler=no_login):
        self.auth = OAuthClientProvider(
            server_url=NOTION_MCP,
            client_metadata=OAuthClientMetadata(
                client_name="LaunchKit",
                redirect_uris=[redirect_uri or TERMINAL_CALLBACK],
                grant_types=["authorization_code", "refresh_token"],
                response_types=["code"],
                token_endpoint_auth_method="none",
            ),
            storage=FileTokens(auth_file(settings, user), redirect_uri),
            redirect_handler=redirect_handler,
            callback_handler=callback_handler,
        )

    @asynccontextmanager
    async def session(self):
        async with streamablehttp_client(NOTION_MCP, auth=self.auth) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


class NotionBoard:
    def __init__(self, settings, trace, user: str):
        self.settings, self.trace, self.user = settings, trace, user

    def entries(self):
        """This person's Notion board tools, as catalogue entries, reached over MCP. Not connected: no board tools."""
        from launchkit.harness.mcp_link import connect

        if not connected(self.settings, self.user):
            self.trace.note(f"Notion is not connected for {self.user}: press Connect Notion on the chat page, so there are no board tools this run")
            return []
        try:
            return connect(NotionServer(self.settings, self.user))
        except NotConnected:
            self.trace.note(f"{self.user}'s Notion login has ended: press Connect Notion on the chat page again")
            return []


def make_board(settings, trace, user: str):
    from launchkit.harness.board import Board

    return NotionBoard(settings, trace, user) if settings.board == "notion" else Board()


def set_up_card(settings, user: str, server: NotionServer | None = None) -> str:
    """Log in, then put the Tidal card in this person's Notion as a private page, or set it back to the brief if it is
    there. The terminal logs in through a browser tab and a local callback; the chat page passes its own server."""
    from launchkit.harness.board import LAST_WEEK
    from launchkit.harness.mcp_link import McpLink

    link = McpLink(server or NotionServer(settings, user, TERMINAL_CALLBACK, open_browser, wait_for_login))
    title, _, body = CARD.read_text(encoding="utf-8").partition("\n")
    title = title.removeprefix("# ")
    content = f"{body.strip()}\n\nStatus: Brief ready\n\nFiles: {', '.join(LAST_WEEK)}"
    found = json.loads(link.call_tool("notion-search", {"query": title})).get("results", [])
    page = next((r["id"] for r in found if r.get("title") == title), None)
    if page is None:
        link.call_tool("notion-create-pages", {"pages": [{"properties": {"title": title}, "content": content}]})
        return f"Made the card: {title}"
    link.call_tool("notion-update-page", {"page_id": page, "command": "replace_content", "new_str": content, "allow_deleting_content": True})
    return f"Set the card back to the brief: {title}"
