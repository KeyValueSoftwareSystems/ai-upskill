"""Stage 2: changing one line without changing the rest.

A stub. Built in stage 2: replace an exact piece of text, and refuse when it is missing or appears more than once.
Appending and replacing every match are not part of this tool: they are a discussion, not a build.

Reference page 7, Changing a file, and page 8, What an edit tool can and cannot check.
"""

from launchkit.files.record import Record
from launchkit.files.workspace import Workspace
from launchkit.tools.catalogue import Entry, todo
from launchkit.tools.notes import EDIT_FILE
from launchkit.trace import Trace


def make_edit_file(workspace: Workspace, trace: Trace, message: str = "") -> Entry:
    @todo
    def edit_file(path: str, old_text: str, new_text: str) -> str:
        """Replace one exact piece of text in a saved file in this conversation's workspace, and nothing else. The old text must appear exactly once."""
        # Build a Record(workspace.root) once, when the tool is built: put that line above this function. Join the path onto
        # workspace.root. A file that is not there: "No file at <path>." Count how often old_text appears. None: return a
        # message that begins "Not found" and change nothing. More than once: begin "Ambiguous", say how many times, change
        # nothing. Exactly once: replace it, write the file, then record.add(path relative to the root, "edit_file", message),
        # trace.add("file_written", path=path, characters=len(new_text)) and return "Edited <path>."
        raise NotImplementedError("stage 2: edit one piece of a file")

    return Entry("edit_file", EDIT_FILE, "read", edit_file)
