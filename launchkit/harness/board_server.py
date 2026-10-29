"""The board's MCP server. It lists its own tools, each with a name, a description and a schema, and says which
ones only read. Run it on its own with: uv run python -m launchkit.harness.board_server"""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from launchkit.harness.board import Board

READS = ToolAnnotations(readOnlyHint=True)
WRITES = ToolAnnotations(readOnlyHint=False, destructiveHint=False)
DELETES = ToolAnnotations(readOnlyHint=False, destructiveHint=True)


def make_board_server(board: Board | None = None) -> FastMCP:
    board = board or Board()
    server = FastMCP("maya-board", log_level="WARNING")

    @server.tool(annotations=READS)
    def read_card(card: str) -> str:
        """Read a card on Maya's board, e.g. the tidal card with the campaign brief, its status and its files."""
        return board.read_card(card)

    @server.tool(annotations=WRITES)
    def attach_files(card: str, files: list[str]) -> str:
        """Attach finished files to a card on Maya's board."""
        return board.attach_files(card, files)

    @server.tool(annotations=WRITES)
    def update_status(card: str, status: str) -> str:
        """Move a card on Maya's board to a new status, e.g. Ready for review."""
        return board.update_status(card, status)

    @server.tool(annotations=DELETES)
    def remove_files(card: str, files: list[str]) -> str:
        """Remove files from a card on Maya's board, e.g. to keep the card tidy."""
        return board.remove_files(card, files)

    return server


if __name__ == "__main__":
    make_board_server().run()
