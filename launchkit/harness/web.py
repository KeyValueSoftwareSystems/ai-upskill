"""search_web: the real web through Tavily, or our saved pages when LAUNCHKIT_SEARCH=saved. Both return the same
shape: each page's address and text. The checks use the saved pages, the same every run.
Competitor pages live in samples/pages, trend pages in samples/trends."""

import os
import re
import time

import httpx

from launchkit.harness.catalogue import Entry
from launchkit.settings import ROOT

PAGES_DIR = ROOT / "samples" / "pages"
TRENDS_DIR = ROOT / "samples" / "trends"
TAVILY_URL = "https://api.tavily.com/search"
PAGE_CHARS = 4000
# Words in a page's file name that say what kind of page it is, or when, not whose: they earn no extra score.
PAGE_KINDS = {"this", "season", "launch", "news", "blog", "post", "forum", "thread", "review", "press", "release", "campaign", "roundup", "reddit", "style"}


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 3}


def make_search_web(settings, pages_dir=PAGES_DIR, top: int = 2, extra_dirs=(TRENDS_DIR,)):
    if settings.search == "saved":
        return make_saved_search(settings, pages_dir, top, extra_dirs)
    return make_tavily_search(settings, top)


def make_tavily_search(settings, top: int = 2):
    def search_web(query: str) -> str:
        """Search the web. Returns the full text of the best matching pages, with their addresses."""
        key = os.getenv("TAVILY_API_KEY")
        if not key:
            return "Search is not set up: add TAVILY_API_KEY to .env, or set LAUNCHKIT_SEARCH=saved for the saved pages."
        try:
            reply = httpx.post(
                os.getenv("TAVILY_URL", TAVILY_URL),
                headers={"Authorization": f"Bearer {key}"},
                json={"query": query, "max_results": top, "include_raw_content": "text"},
                timeout=settings.timeout,
            )
            reply.raise_for_status()
        except httpx.HTTPError as error:
            return f"Search failed for {query}: {error}"
        pages = [f"# {r['title']}\nAddress: {r['url']}\n\n{(r.get('raw_content') or r['content'])[:PAGE_CHARS]}" for r in reply.json()["results"]]
        return "\n\n---\n\n".join(pages) if pages else f"No pages found for {query}."

    return search_web


def make_saved_search(settings, pages_dir=PAGES_DIR, top: int = 2, extra_dirs=(TRENDS_DIR,)):
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
