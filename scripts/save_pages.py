"""Save two real web pages per competitor on the Tidal card into samples/pages, found with Tavily, as search_web
does live. The checks read these saved pages, so they stay offline and the same every run.
Refresh them with: uv run python scripts/save_pages.py"""

import os
import re

import httpx

from launchkit.adapters.fakes import COMPETITORS
from launchkit.harness.web import PAGE_CHARS, PAGES_DIR, TAVILY_URL
from launchkit.settings import settings


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


SKIP = ("youtube.com", "facebook.com", "mapquest.com", "cbinsights.com", "instagram.com", "tiktok.com")


def pages_about(name: str, keep: int = 2) -> list[dict]:
    """News pages first, then the wider web, until two pages that are about this brand."""
    found = []
    for topic in ("news", "general"):
        reply = httpx.post(
            TAVILY_URL,
            headers={"Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}"},
            json={"query": f"{name} bottle launch marketing campaign", "topic": topic, "max_results": 8, "include_raw_content": "text"},
            timeout=settings.timeout,
        )
        reply.raise_for_status()
        for r in reply.json()["results"]:
            if len(found) < keep and (r.get("raw_content") or "").count(name) >= 2 and not any(d in r["url"] for d in SKIP) and r["url"] not in {f["url"] for f in found}:
                found.append(r)
    return found


def main():
    for old in PAGES_DIR.glob("*.md"):
        old.unlink()
    for name in COMPETITORS[:5]:
        found = pages_about(name)
        for n, page in enumerate(found, 1):
            path = PAGES_DIR / f"{slug(name)}-{n}.md"
            path.write_text(f"# {page['title']}\nAddress: {page['url']}\n\n{page['raw_content'][:PAGE_CHARS].strip()}\n", encoding="utf-8")
            print(f"{path.name}  {page['url']}")
        if len(found) < 2:
            print(f"Only {len(found)} pages for {name}: run again, or change the query.")


if __name__ == "__main__":
    main()
