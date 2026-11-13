"""Stage 2: the agent's search tool, capped from the start.

Finds which file says something and where, so the agent reads just that line instead of every file in the folder.
One match per line, as `path:line: snippet`. It stops after MAX_MATCHES and says so, skips anything that is not
text, and skips anything over a size limit, because a search that returns 5,000 lines has the same problem as
reading everything.

About fifteen lines of Python rather than a wrapper around ripgrep. `rg` is not installed by default on macOS,
Windows or most Linux images, and nobody should spend session time installing one. Most coding editors do bundle
their own copy for speed, which is worth saying in the room and is not what this needs to be.

Reference page 4, Finding a file, and page 5, What an index costs to keep true.
"""

from launchkit.files.paths import OutsideWorkspace, refuse, resolve_in_workspace
from launchkit.tools.catalogue import Entry

TEXT = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}
MAX_BYTES = 500_000
MAX_MATCHES = 10
SNIPPET = 160


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
                    matches.append(f"{file.relative_to(workspace.root.resolve()).as_posix()}:{number}: {line.strip()[:SNIPPET]}")
            if stopped:
                break
        trace.add("search", pattern=pattern, matches=len(matches), stopped=stopped)
        if not matches:
            return f"Nothing matched {pattern!r}."
        return "\n".join(matches) + (f"\nStopped after {MAX_MATCHES} matches; narrow the search to see more." if stopped else "")

    return Entry("search_files", "pick me to search the saved files, briefs and documents for a word or phrase and see which file and line says it, before reading any of them", "read", search_files)
