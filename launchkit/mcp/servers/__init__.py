"""Every MCP server the agent can reach, one file each. To connect a new one, add a file here with two functions:
on(settings), whether .env switches it on, and entries(settings, trace, user), its tools as catalogue entries,
reached through mcp/client.py. A file without them, like local_board_server.py, is not a server the agent picks."""

import importlib
import pkgutil


def server_entries(settings, trace, user: str) -> list:
    entries = []
    for found in pkgutil.iter_modules(__path__):
        server = importlib.import_module(f"{__name__}.{found.name}")
        if hasattr(server, "on") and hasattr(server, "entries") and server.on(settings):
            entries += server.entries(settings, trace, user)
    return entries
