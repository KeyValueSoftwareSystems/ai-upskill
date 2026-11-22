"""Stage 1: the agent's write tool. Stage 3 sends every path through the one check.

Writes a file into this conversation's workspace, and adds each one to the conversation's record
(launchkit/files/record.py), which the chat page reads. It is a "read" kind in the catalogue on purpose: it is the
agent's own workspace, so it does not stop to ask the way a write to the outside world does.

Reference page 6, File tools.
"""

from launchkit.files.paths import OutsideWorkspace, refuse, resolve_in_workspace
from launchkit.files.record import Record
from launchkit.files.workspace import Workspace
from launchkit.tools.catalogue import Entry
from launchkit.tools.notes import WRITE_FILE
from launchkit.trace import Trace


def make_write_file(workspace: Workspace, trace: Trace, message: str = "") -> Entry:
    record = Record(workspace.root)

    def write_file(path: str, text: str) -> str:
        """Save text as a file in this conversation's workspace. Finished work goes in outputs/, drafts in work/."""
        try:
            real = resolve_in_workspace(workspace.root, path)
        except OutsideWorkspace as error:
            return refuse(trace, "write_file", path, error.reason)
        real.parent.mkdir(parents=True, exist_ok=True)
        real.write_text(text, encoding="utf-8")
        record.add(real.relative_to(workspace.root.resolve()), "write_file", message)
        trace.add("file_written", path=path, characters=len(text))
        return f"Wrote {path}."

    return Entry("write_file", WRITE_FILE, "read", write_file)
