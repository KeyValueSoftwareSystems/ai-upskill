"""Stage 4: changing one line without changing the rest.

Replaces exactly the text it was given, refuses when that text is missing, and refuses when it appears more than
once, saying how many. It records the edit the way write_file records a write. It does not check whether the file
changed since the agent read it, which is why stage 2's bug gets past it. The stretch closes that: it refuses a
file it has not read, and a file that changed since it was read, and it checks and writes under one lock. Appending
and replacing every match are not part of this tool: they are a discussion, not a build.

Reference page 7, Changing a file, and page 8, What an edit tool can and cannot check.
"""

from launchkit.files.paths import OutsideWorkspace, refuse, resolve_in_workspace
from launchkit.files.record import Record
from launchkit.files.versions import fingerprint, lock_for
from launchkit.tools.catalogue import Entry


def make_edit_file(workspace, trace, message: str = "") -> Entry:
    artifacts = Record(workspace.root)  # built when the tool is built, like write_file's

    def edit_file(path: str, old_text: str, new_text: str) -> str:
        """Replace one exact piece of text in a file this conversation owns, and nothing else. The old text must appear exactly once."""
        try:
            real = resolve_in_workspace(workspace.root, path)
        except OutsideWorkspace as error:
            return refuse(trace, "edit_file", path, error.reason)
        if not real.is_file():
            return f"No file at {path}."
        with lock_for(real):  # the check and the write are one step: no other writer can slip in between them
            data = real.read_bytes()
            seen = workspace.seen.get(str(real))
            if seen is None:
                return f"Read first: {path} has not been read in this conversation, so nothing changed. Read the file, then edit it."
            if fingerprint(data) != seen:
                return f"Changed: {path} changed since it was read, so nothing changed. Read it again and redo the edit."
            text = data.decode("utf-8")
            found = text.count(old_text) if old_text else 0
            if found == 0:
                return f"Not found: {path} does not contain that text, so nothing changed. Read the file and copy the text exactly."
            if found > 1:
                return f"Ambiguous: that text appears {found} times in {path}, so nothing changed. Include more of the surrounding text so it appears once."
            real.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
            workspace.seen[str(real)] = fingerprint(real.read_bytes())
            artifacts.add(real.relative_to(workspace.root.resolve()), "edit_file", message)
            trace.add("file_written", path=path, characters=len(new_text))
            return f"Edited {path}."

    return Entry("edit_file", "pick me to edit, change, update or fix one line or phrase in a saved file, brief or document without rewriting the rest: give the exact old text and the new text", "read", edit_file)
