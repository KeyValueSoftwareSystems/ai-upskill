"""Stage 1: the agent's write tool.

Writes a file into this conversation's workspace. Finished work goes in outputs/, drafts in work/. It is a "read"
kind in the catalogue on purpose: it is the agent's own workspace, so it does not stop to ask the way a write to
the outside world does.

Reference page 6, File tools.
"""

from launchkit.tools.catalogue import Entry


def make_write_file(workspace, trace, message: str = "") -> Entry:
    def write_file(path: str, text: str) -> str:
        """Write a file into this conversation's workspace. Finished work goes in outputs/, drafts in work/."""
        real = workspace.root / path
        real.parent.mkdir(parents=True, exist_ok=True)
        real.write_text(text, encoding="utf-8")
        trace.add("file_written", path=path, characters=len(text))
        return f"Wrote {path}."

    return Entry("write_file", "pick me to save, write or create a file, brief, document, draft or plan in this conversation's workspace: finished work in outputs/, drafts in work/", "read", write_file)
