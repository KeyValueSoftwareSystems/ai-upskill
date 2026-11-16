"""Stage 1: the agent's read tool. Stage 2 adds the line range. Stage 3 sends every path through the one check.

Reads a file this conversation owns, or just a range of its lines. Anything the brand keeps for itself, the
brand book and the rules, is read as `brand/<name>`: reads may reach those, and nothing ever writes them.

Reference page 6, File tools, and page 9, Who may touch which file.
"""

from launchkit.files.paths import OutsideWorkspace, refuse, resolve_in_workspace
from launchkit.tools.catalogue import Entry

LIMIT = 200_000  # characters, so one read can never be the whole context


def make_read_file(workspace, trace) -> Entry:
    def read_file(path: str, first_line: int = 1, last_line: int = 0) -> str:
        """Read a file this conversation owns, or the brand's own files as brand/<name>. Give first_line and last_line, counting from 1, to read part of it."""
        try:
            if path.startswith("brand/"):
                real = resolve_in_workspace(workspace.shared, path[len("brand/"):])
            else:
                real = resolve_in_workspace(workspace.root, path)
        except OutsideWorkspace as error:
            return refuse(trace, "read_file", path, error.reason)
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
