"""Stage 4: changing one line without changing the rest.

The only way to change a file before this stage was to write the whole thing again, so the model rewrote
everything and drifted in the parts nobody asked about. This replaces one exact piece of text and refuses when it
is not sure: when the text is missing, and when it appears more than once.

What this check is about, and what it is not. It looks at content. It catches a collision that overwrote your
lines, and it permits one that did not. That is exactly what the ticket after shipping turns on: five writers each
appending a different line, every edit matching once, four entries lost. An edit tool's check is about content, not
about write ordering.

Appending is not part of this tool. That question arrives at the fork after the ticket.

Reference page 7, Changing a file, and page 8, What an edit tool can and cannot check.
"""

from launchkit.files.paths import OutsideWorkspace, refuse, resolve_in_workspace
from launchkit.tools.catalogue import Entry


def make_edit_file(workspace, trace, message: str = "") -> Entry:
    def edit_file(path: str, old_text: str, new_text: str) -> str:
        """Replace one exact piece of text in a file this conversation owns, and nothing else. The old text must appear exactly once."""
        try:
            real = resolve_in_workspace(workspace.root, path)
        except OutsideWorkspace as error:
            return refuse(trace, "edit_file", path, error.reason)
        if not real.is_file():
            return f"No file at {path}."
        text = real.read_text(encoding="utf-8")
        found = text.count(old_text) if old_text else 0
        if found == 0:
            return f"Not found: {path} does not contain that text, so nothing changed. Read the file and copy the text exactly."
        if found > 1:
            return f"Ambiguous: that text appears {found} times in {path}, so nothing changed. Include more of the surrounding text so it appears once."
        real.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
        trace.add("file_written", path=path, characters=len(new_text))
        return f"Edited {path}."

    return Entry("edit_file", "pick me to edit, change, update or fix one line or phrase in a saved file, brief or document without rewriting the rest: give the exact old text and the new text", "read", edit_file)
