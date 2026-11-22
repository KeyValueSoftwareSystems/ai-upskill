"""Stage 1: the agent's list tool.

Lists the files this conversation owns, so the agent can find what it made without being told the path.

Reference page 6, File tools.
"""

from launchkit.files.workspace import Workspace
from launchkit.tools.catalogue import Entry
from launchkit.tools.notes import LIST_FILES
from launchkit.trace import Trace


def make_list_files(workspace: Workspace, trace: Trace) -> Entry:
    def list_files(folder: str = ".") -> str:
        """List the saved files in this conversation's workspace, one path per line, under a folder. The default is the whole workspace."""
        root = workspace.root / folder
        found = sorted(p.relative_to(workspace.root).as_posix() for p in root.rglob("*") if p.is_file()) if root.is_dir() else []
        trace.add("file_listed", folder=folder, files=len(found))
        return "\n".join(found) if found else "Nothing here yet."

    return Entry("list_files", LIST_FILES, "read", list_files)
