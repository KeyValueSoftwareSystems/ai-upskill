"""A link to one MCP server, held open for the whole run. MCP clients are async; the harness is not, so the link
runs the client on its own event loop and waits for each answer."""

import asyncio
import inspect
import threading

from mcp.shared.memory import create_connected_server_and_client_session

from launchkit.harness.catalogue import Entry

JSON_TYPES = {"string": str, "integer": int, "number": float, "boolean": bool, "array": list, "object": dict}


class McpLink:
    def __init__(self, server):
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        self.wait(self.open(server))

    async def open(self, server):
        self.opened = create_connected_server_and_client_session(server)
        self.session = await self.opened.__aenter__()

    def wait(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop).result(timeout=30)

    def list_tools(self) -> list:
        return self.wait(self.session.list_tools()).tools

    def call_tool(self, name: str, arguments: dict) -> str:
        result = self.wait(self.session.call_tool(name, arguments))
        return "\n".join(getattr(part, "text", "") for part in result.content)


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
    """Step 4: not built yet. Connect to the server, list its tools, and make each one a catalogue entry."""
    return []
