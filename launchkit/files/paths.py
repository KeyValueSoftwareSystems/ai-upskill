"""Stage 3: the one door every path passes before it is used.

Not built yet. The room builds this in stage 3, after watching Jonas at Ember read Harbor's brief with a `..`.

What it must do. Four callers need the same answer about a path: the file tools, the search, the chat page's file
list and the download route. A check only one of them calls is not a fence, so there is one function.

Four forms have to be refused:

    ../../harbor/...          climbing out
    /etc/passwd               an absolute path
    a symlink pointing out    the name is inside, the file is not
    t3a9-old                  a conversation whose name starts the same way as t3a9

The last one is why the check resolves before it compares. Comparing the text of a path says t3a9-old is inside
ember, because one string starts with the other.

Reference page 9, Who may touch which file.
"""

from pathlib import Path


class OutsideWorkspace(Exception):
    """A path that does not resolve inside the workspace. The tool layer turns this into a refusal on the trace."""

    def __init__(self, asked: str, reason: str):
        self.asked = asked
        self.reason = reason
        super().__init__(f"refused {asked!r}: {reason}")


def resolve_in_workspace(root: Path, asked: str | Path) -> Path:
    raise NotImplementedError("stage 3: the real location of `asked` inside `root`, or OutsideWorkspace")


def refuse(trace, tool: str, asked: str, reason: str) -> str:
    """One refusal, on the trace and in words the agent can pass back. Criterion 11 counts these."""
    trace.add("file_refused", tool=tool, path=asked, reason=reason)
    return f"Refused: {reason}. Ask for a file inside this conversation's workspace."
