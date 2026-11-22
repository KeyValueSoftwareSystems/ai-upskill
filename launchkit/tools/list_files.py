"""Stage 1: the agent's list tool.

A stub. Built with read and write in stage 1. It lists what this conversation owns, so the agent can find what it
made without being told the path.

Reference page 6, File tools.
"""

from launchkit.files.workspace import Workspace
from launchkit.tools.catalogue import Entry, todo
from launchkit.tools.notes import LIST_FILES
from launchkit.trace import Trace


def make_list_files(workspace: Workspace, trace: Trace) -> Entry:
    @todo
    def list_files(folder: str = ".") -> str:
        """List the saved files in this conversation's workspace, one path per line, under a folder. The default is the whole workspace."""
        # Join the folder onto workspace.root and list every file under it as a path relative to workspace.root.
        # A folder that is not there, or is empty, comes back as the message "Nothing here yet." and nothing raises.
        # Then: trace.add("file_listed", folder=folder, files=len(found))
        raise NotImplementedError("stage 1: list the files in the workspace")

    return Entry("list_files", LIST_FILES, "read", list_files)
