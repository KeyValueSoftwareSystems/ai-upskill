"""A link to one MCP server, held open for one turn. MCP clients are async; the harness is not, so the link
runs the client on its own event loop and waits for each answer. run_main closes every link its turn opened."""

import asyncio
import functools
import inspect
import threading
import time

from mcp.shared.memory import create_connected_server_and_client_session

from launchkit.tools.catalogue import Entry

JSON_TYPES = {"string": str, "integer": int, "number": float, "boolean": bool, "array": list, "object": dict}


OPENED_HERE = threading.local()  # the links this thread's turn opened, so the turn can close them at the end


class McpLink:
    def __init__(self, server, timeout: float = 300):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.ready = threading.Event()
        self.held = asyncio.run_coroutine_threadsafe(self.hold(server), self.loop)
        give_up = time.monotonic() + timeout
        while not self.ready.wait(0.05):
            if self.held.done():
                self.held.result()  # the link failed to open: raise its error here
            if time.monotonic() > give_up:
                self.close()
                raise TimeoutError(f"the MCP server did not answer in {timeout:g} s")
        OPENED_HERE.__dict__.setdefault("links", []).append(self)

    async def hold(self, server):
        """Open the session, keep it open until close(), then shut it in the same task, as the MCP client needs."""
        self.only = getattr(server, "only", None)
        self.release = asyncio.Event()
        opened = server.session() if hasattr(server, "session") else create_connected_server_and_client_session(server)
        async with opened as session:
            self.session = session
            self.ready.set()
            await self.release.wait()

    def close(self):
        if self.loop.is_closed():
            return
        if self.ready.is_set():
            self.loop.call_soon_threadsafe(self.release.set)
        try:
            self.held.result(timeout=10)
        except BaseException:
            self.held.cancel()
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=10)
        if not self.thread.is_alive():
            self.loop.close()

    def wait(self, coroutine, timeout: float = 60):
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop).result(timeout=timeout)

    def list_tools(self) -> list:
        tools = self.wait(self.session.list_tools()).tools
        return [tool for tool in tools if self.only is None or tool.name in self.only]

    def call_tool(self, name: str, arguments: dict) -> str:
        result = self.wait(self.session.call_tool(name, arguments))
        text = "\n".join(getattr(part, "text", "") for part in result.content)
        return f"{name} failed: {text}" if result.isError else text


def close_links_opened_here():
    """Close every MCP link this thread opened: the end of a turn."""
    for link in OPENED_HERE.__dict__.pop("links", []):
        link.close()


def closes_its_mcp_links(run):
    """Wrap a turn so every MCP link it opened closes when it ends, even when it fails."""

    @functools.wraps(run)
    def turn(*args, **kwargs):
        try:
            return run(*args, **kwargs)
        finally:
            close_links_opened_here()

    return turn


def tool_function(tool, link: McpLink):
    """A Python function that calls one MCP tool, with its name, description and inputs, so find_tool and run_tool
    treat it like any other tool."""

    def call(**arguments):
        return link.call_tool(tool.name, arguments)

    props = tool.inputSchema.get("properties", {})
    required = set(tool.inputSchema.get("required", []))
    call.__name__ = tool.name
    call.__doc__ = tool.description
    call.__signature__ = inspect.Signature(
        [inspect.Parameter(n, inspect.Parameter.KEYWORD_ONLY, annotation=JSON_TYPES.get(p.get("type"), str), default=inspect.Parameter.empty if n in required else None) for n, p in props.items()]
    )
    return call


def connect(server) -> list[Entry]:
    """Connect to an MCP server, list its tools, and make each one a catalogue entry. The server describes its own
    tools, and says which ones only read."""
    link = McpLink(server)
    return [
        Entry(tool.name, (tool.description or tool.name).split("\n")[0], "read" if tool.annotations and tool.annotations.readOnlyHint else "write", tool_function(tool, link))
        for tool in link.list_tools()
    ]
