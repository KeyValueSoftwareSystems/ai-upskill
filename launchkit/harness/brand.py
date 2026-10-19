from pathlib import Path

from launchkit.harness.trace import Trace
from launchkit.harness.workspace import Workspace

BRAND_FILES = ("brand-book.md", "facts.md")


def brand_file(root: Path) -> Path | None:
    """The brand's own text: the brand book if it has one, else its facts."""
    return next((root / name for name in BRAND_FILES if (root / name).is_file()), None)


def make_get_brand_details(ws: Workspace, trace: Trace):
    """v1: the tool returns the whole brand file of the workspace the request resolved to.
    The workspace is bound here, by the harness, from the trusted request. The model never names it."""

    def get_brand_details() -> str:
        """Look up this brand's guide and product facts: what the products are and do, care and
        washing rules, sizes, warranty, launches, words to use and avoid. Call it before you state
        any product fact. Use only what it returns; if it does not say something, do not claim it."""
        path = brand_file(ws.root)
        if path is None:
            return "This brand has no brand guide or facts on file."
        trace.file(path)
        return path.read_text(encoding="utf-8")

    return get_brand_details
