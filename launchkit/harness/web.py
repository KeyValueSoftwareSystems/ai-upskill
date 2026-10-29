"""search_web over our saved pages: the same shape a real search tool returns, the same every run.
Competitor pages live in samples/pages, trend pages in samples/trends."""

import re
import time

from launchkit.harness.catalogue import Entry
from launchkit.settings import ROOT

PAGES_DIR = ROOT / "samples" / "pages"
TRENDS_DIR = ROOT / "samples" / "trends"
PAGE_KINDS = {"launch", "news", "blog", "post", "forum", "thread", "review", "press", "release", "campaign", "roundup", "reddit", "style"}


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 3}


def make_search_web(settings, pages_dir=PAGES_DIR, top: int = 2, extra_dirs=(TRENDS_DIR,)):
    pages = [(path.stem, path.read_text(encoding="utf-8")) for folder in (pages_dir, *extra_dirs) for path in sorted(folder.glob("*.md"))]

    def search_web(query: str) -> str:
        """Search the web. Returns the full text of the best matching pages, with their addresses."""
        time.sleep(settings.search_delay)
        asked = words(query)
        scored = sorted(((len(asked & (words(name.replace("-", " ")) - PAGE_KINDS)) * 5 + len(asked & words(text)), text) for name, text in pages), reverse=True)
        found = [text for score, text in scored[:top] if score > 0]
        return "\n\n---\n\n".join(found) if found else f"No pages found for {query}."

    return search_web


def search_entry(settings) -> Entry:
    return Entry("search_web", "search the web and read the pages that come back", "read", make_search_web(settings))
