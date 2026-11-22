"""Stage 2: changing one line without changing the rest.

Replaces exactly the text it was given, refuses when that text is missing, and refuses when it appears more than
once, saying how many. It records the edit the way write_file records a write. It does not check whether the file
changed since the agent read it, which is the gap the stretch closes. Appending and replacing every match are not
part of this tool: they are a discussion, not a build.

Reference page 7, Changing a file, and page 8, What an edit tool can and cannot check.
"""

from launchkit.files.record import Record
from launchkit.files.workspace import Workspace
from launchkit.tools.catalogue import Entry
from launchkit.tools.notes import EDIT_FILE
from launchkit.trace import Trace


def make_edit_file(workspace: Workspace, trace: Trace, message: str = "") -> Entry:
    record = Record(workspace.root)

    def edit_file(path: str, old_text: str, new_text: str) -> str:
        """Replace one exact piece of text in a saved file in this conversation's workspace, and nothing else. The old text must appear exactly once."""
        real = workspace.root / path
        if not real.is_file():
            return f"No file at {path}."
        text = real.read_text(encoding="utf-8")
        found = text.count(old_text) if old_text else 0
        if found == 0:
            return f"Not found: {path} does not contain that text, so nothing changed. Read the file and copy the text exactly."
        if found > 1:
            return f"Ambiguous: that text appears {found} times in {path}, so nothing changed. Include more of the surrounding text so it appears once."
        real.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
        record.add(real.relative_to(workspace.root), "edit_file", message)
        trace.add("file_written", path=path, characters=len(new_text))
        return f"Edited {path}."

    return Entry("edit_file", EDIT_FILE, "read", edit_file)
