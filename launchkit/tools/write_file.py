"""Stage 1: the agent's write tool.

A stub. Built with read and list in stage 1. Writes land in the conversation's workspace, and each one is added to
the conversation's record (launchkit/files/record.py), which the chat page reads. It is a "read" kind in the
catalogue on purpose: it is the agent's own workspace, so it does not stop to ask the way a write to the outside
world does.

Reference page 6, File tools.
"""

from launchkit.files.record import Record
from launchkit.files.workspace import Workspace
from launchkit.tools.catalogue import Entry, todo
from launchkit.tools.notes import WRITE_FILE
from launchkit.trace import Trace


def make_write_file(workspace: Workspace, trace: Trace, message: str = "") -> Entry:
    @todo
    def write_file(path: str, text: str) -> str:
        """Save text as a file in this conversation's workspace. Finished work goes in outputs/, drafts in work/."""
        # Build a Record(workspace.root) once, when the tool is built: put that line above this function. Join the path onto
        # workspace.root, make its folder, write the text. Then: record.add(path relative to the root, "write_file", message)
        # and trace.add("file_written", path=path, characters=len(text)). Return "Wrote <path>."
        raise NotImplementedError("stage 1: write a file in the workspace")

    return Entry("write_file", WRITE_FILE, "read", write_file)
