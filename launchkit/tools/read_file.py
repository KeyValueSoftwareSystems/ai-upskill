"""Stage 1: the agent's read tool.

Reads a file this conversation owns. Stage 2's search is what lets the agent read just a line range of one,
instead of the whole thing.

Reference page 6, File tools.
"""

from launchkit.tools.catalogue import Entry

LIMIT = 200_000  # characters, so one read can never be the whole context


def make_read_file(workspace, trace) -> Entry:
    def read_file(path: str) -> str:
        """Read a file this conversation owns."""
        real = workspace.root / path
        if not real.is_file():
            return f"No file at {path}."
        text = real.read_text(encoding="utf-8", errors="replace")[:LIMIT]
        trace.add("file_read", path=path, characters=len(text))
        return text

    return Entry("read_file", "pick me to open, read or show a saved file, brief, document or draft from this conversation's workspace, or a range of its lines; the brand's own files are brand/<name>", "read", read_file)
