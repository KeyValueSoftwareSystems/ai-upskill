"""Stage 1: the agent's read tool.

Reads a file this conversation owns, or just a range of its lines. The search says which file and which line, and
this reads around it, so the answer costs a search and a read or two instead of every file in the folder.

Reference page 6, File tools.
"""

from launchkit.files.workspace import Workspace
from launchkit.tools.catalogue import Entry
from launchkit.tools.notes import READ_FILE
from launchkit.trace import Trace

LIMIT = 200_000  # characters, so one read can never be the whole context


def make_read_file(workspace: Workspace, trace: Trace) -> Entry:
    def read_file(path: str, first_line: int = 1, last_line: int = 0) -> str:
        """Read a saved file in this conversation's workspace, by the path list_files shows, and return its text. Give first_line and last_line, counting from 1, to read part of it."""
        real = workspace.root / path
        if not real.is_file():
            return f"No file at {path}."
        text = real.read_text(encoding="utf-8", errors="replace")
        if first_line > 1 or last_line:
            lines = text.splitlines()
            text = "\n".join(lines[max(first_line, 1) - 1 : last_line or len(lines)])
        text = text[:LIMIT]
        trace.add("file_read", path=path, characters=len(text))
        return text

    return Entry("read_file", READ_FILE, "read", read_file)
