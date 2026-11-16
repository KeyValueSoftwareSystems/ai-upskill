"""Stage 1: the agent's read tool.

Reads a file this conversation owns, or just a range of its lines. The range is what stage 2 adds: the search says
which file and which line, and this reads around it, so the answer costs a search and a read or two instead of
every file in the folder.

Reference page 6, File tools.
"""

from launchkit.tools.catalogue import Entry

LIMIT = 200_000  # characters, so one read can never be the whole context


def make_read_file(workspace, trace) -> Entry:
    def read_file(path: str, first_line: int = 1, last_line: int = 0) -> str:
        """Read a file this conversation owns. Give first_line and last_line, counting from 1, to read part of it."""
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

    return Entry("read_file", "pick me to open, read or show a saved file, brief, document or draft from this conversation's workspace, or a range of its lines; the brand's own files are brand/<name>", "read", read_file)
