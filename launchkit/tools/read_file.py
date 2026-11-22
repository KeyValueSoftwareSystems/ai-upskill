"""Stage 1: the agent's read tool.

A stub. The room builds read, list and write together in stage 1, in the workspace from launchkit/files/workspace.py.
Reading takes a line range, so the agent can read the lines a search points at instead of the whole file.

Reference page 6, File tools.
"""

from launchkit.files.workspace import Workspace
from launchkit.tools.catalogue import Entry, todo
from launchkit.tools.notes import READ_FILE
from launchkit.trace import Trace


def make_read_file(workspace: Workspace, trace: Trace) -> Entry:
    @todo
    def read_file(path: str, first_line: int = 1, last_line: int = 0) -> str:
        """Read a saved file in this conversation's workspace, by the path list_files shows, and return its text. Give first_line and last_line, counting from 1, to read part of it."""
        # Join the path onto workspace.root. A file that is not there comes back as a message, "No file at <path>.",
        # and nothing raises. last_line 0 means to the end. Then: trace.add("file_read", path=path, characters=len(text))
        raise NotImplementedError("stage 1: read a file in the workspace")

    return Entry("read_file", READ_FILE, "read", read_file)
