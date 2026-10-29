"""Maya's board: a local fake of her team's Notion board, the same every run. The agent never calls it directly:
it reaches the board through the board's MCP server (board_server.py), the way it would reach the real one."""

from launchkit.settings import ROOT

CARDS_DIR = ROOT / "samples" / "board"
LAST_WEEK = ["tidal-feed-1080x1080-approved.png", "tidal-story-1080x1920-approved.png"]


def key(card: str) -> str:
    """"Tidal", "tidal" and "Tidal card" all mean the tidal card."""
    return card.lower().removesuffix(" card").strip()


class Board:
    def __init__(self):
        self.cards = {path.stem: {"text": path.read_text(encoding="utf-8"), "status": "Brief ready", "files": list(LAST_WEEK)} for path in sorted(CARDS_DIR.glob("*.md"))}

    def read_card(self, card: str) -> str:
        found = self.cards.get(key(card))
        if found is None:
            return f"No card named {card}. Cards: {', '.join(self.cards)}"
        return f"{found['text']}\nStatus: {found['status']}\nFiles: {', '.join(found['files']) or 'none'}"

    def attach_files(self, card: str, files: list[str]) -> str:
        self.cards[key(card)]["files"] += files
        return f"Attached {len(files)} files to {card}."

    def update_status(self, card: str, status: str) -> str:
        self.cards[key(card)]["status"] = status
        return f"{card} is now {status}."

    def remove_files(self, card: str, files: list[str]) -> str:
        kept = self.cards[key(card)]["files"]
        self.cards[key(card)]["files"] = [f for f in kept if f not in files]
        return f"Removed {len(kept) - len(self.cards[key(card)]['files'])} files from {card}."

    def entries(self):
        """The board's tools, as catalogue entries, reached over MCP."""
        from launchkit.harness.board_server import make_board_server
        from launchkit.harness.mcp_link import connect

        return connect(make_board_server(self))
