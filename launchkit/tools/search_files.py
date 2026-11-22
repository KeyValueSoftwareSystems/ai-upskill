"""The agent's search tool. Ready-made, capped from the start.

Finds which file says something and where, so the agent reads just that line instead of every file in the folder.
One match per line, as `path:line: snippet`, the snippet cut around the match so the word always shows, because a
brief is often one long line. It stops after MAX_MATCHES and says so, skips anything that is not
text, and skips anything over a size limit, because a search that returns 5,000 lines has the same problem as
reading everything.

About fifteen lines of Python rather than a wrapper around ripgrep. `rg` is not installed by default on macOS,
Windows or most Linux images, and nobody should spend session time installing one. Most coding editors do bundle
their own copy for speed, which is worth saying in the room and is not what this needs to be.

Stage 3 sends its folder through the one check every path passes, like the other tools.

Reference page 4, Finding a file, and page 5, What an index costs to keep true.
"""

import re

from launchkit.files.paths import OutsideWorkspace, refuse, resolve_in_workspace
from launchkit.tools.catalogue import Entry
from launchkit.tools.notes import SEARCH_FILES

TEXT = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}
MAX_BYTES = 500_000
MAX_MATCHES = 10
SNIPPET = 160
LEFT_OUT = {"the", "and", "for", "with", "what", "did", "say", "about", "from", "that", "this", "are", "was", "our", "which", "one", "them"}


def snippet(line: str, wanted: str) -> str:
    """About SNIPPET characters of the line, centred on the match, with "..." where text was cut."""
    if len(line) <= SNIPPET:
        return line
    at = line.lower().find(wanted)
    start = max(0, min(at + len(wanted) // 2 - SNIPPET // 2, len(line) - SNIPPET))
    end = start + SNIPPET
    return ("..." if start else "") + line[start:end] + ("..." if end < len(line) else "")


def make_search_files(workspace, trace) -> Entry:
    def search_files(pattern: str, folder: str = ".") -> str:
        """Find which of this conversation's files mention a word or phrase, and on which line, before reading any of them."""
        try:
            root = resolve_in_workspace(workspace.root, folder)
        except OutsideWorkspace as error:
            return refuse(trace, "search_files", folder, error.reason)
        wanted = pattern.lower()
        matches, stopped = [], False
        for file in sorted(root.rglob("*")) if root.is_dir() else []:
            if not file.is_file() or file.suffix.lower() not in TEXT or file.stat().st_size > MAX_BYTES:
                continue
            for number, line in enumerate(file.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if wanted in line.lower():
                    if len(matches) == MAX_MATCHES:
                        stopped = True
                        break
                    matches.append(f"{file.relative_to(workspace.root.resolve()).as_posix()}:{number}: {snippet(line.strip(), wanted)}")
            if stopped:
                break
        if not matches:
            # The whole phrase is nowhere, so say which lines hold some of its words: a phrase is rarely written word for word.
            words = [w for w in dict.fromkeys(re.findall(r"[a-z0-9]+", wanted)) if len(w) > 2 and w not in LEFT_OUT]
            partial = []
            if len(words) > 1:
                for file in sorted(root.rglob("*")) if root.is_dir() else []:
                    if not file.is_file() or file.suffix.lower() not in TEXT or file.stat().st_size > MAX_BYTES:
                        continue
                    for number, line in enumerate(file.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                        hit = [w for w in words if w in line.lower()]
                        if hit:
                            partial.append((len(hit), f"{file.relative_to(workspace.root.resolve()).as_posix()}:{number}: {snippet(line.strip(), hit[0])}"))
                partial.sort(key=lambda p: -p[0])
            trace.add("search", pattern=pattern, matches=len(partial[:MAX_MATCHES]), stopped=False)
            if not partial:
                return f"Nothing matched {pattern!r}."
            return (f"Nothing matched {pattern!r} as a whole. These lines hold some of its words ({', '.join(words)}):\n"
                    + "\n".join(p[1] for p in partial[:MAX_MATCHES]))
        trace.add("search", pattern=pattern, matches=len(matches), stopped=stopped)
        return "\n".join(matches) + (f"\nStopped after {MAX_MATCHES} matches; narrow the search to see more." if stopped else "")

    return Entry("search_files", SEARCH_FILES, "read", search_files)
