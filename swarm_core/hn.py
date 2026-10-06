"""Hacker News access through the public Firebase and Algolia APIs (no key needed)."""

import re
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

import requests

FIREBASE = "https://hacker-news.firebaseio.com/v0"
ALGOLIA = "https://hn.algolia.com/api/v1"
TIMEOUT = 15


def _get_json(url: str, params: dict | None = None):
    response = requests.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def story(item_id: int) -> dict:
    return _get_json(f"{FIREBASE}/item/{item_id}.json") or {}


def stories(list_name: str, limit: int) -> list[dict]:
    """Top, best, new or show stories, in HN order, skipping deleted or dead items."""
    ids = _get_json(f"{FIREBASE}/{list_name}.json")[:limit]
    with ThreadPoolExecutor(max_workers=8) as pool:
        items = list(pool.map(story, ids))
    return [s for s in items if s and not s.get("deleted") and not s.get("dead")]


def week_best(days: int = 7, limit: int = 40) -> list[dict]:
    """Most upvoted stories of the last `days` days, from Algolia."""
    since = int(time.time()) - days * 86_400
    data = _get_json(f"{ALGOLIA}/search", {
        "tags": "story",
        "numericFilters": f"created_at_i>{since},points>50",
        "hitsPerPage": 200,
    })
    hits = sorted(data.get("hits", []), key=lambda h: h.get("points") or 0, reverse=True)
    return [{"title": h.get("title"), "url": h.get("url"), "score": h.get("points"),
             "descendants": h.get("num_comments"), "id": int(h["objectID"])} for h in hits[:limit]]


def discussion_url(item_id: int) -> str:
    return f"https://news.ycombinator.com/item?id={item_id}"


class _TextExtractor(HTMLParser):
    """Keeps visible text, dropping scripts, styles and navigation."""

    SKIP = {"script", "style", "noscript", "nav", "footer", "header", "svg", "form"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skipping += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skipping:
            self._skipping -= 1

    def handle_data(self, data):
        if not self._skipping and data.strip():
            self.parts.append(data.strip())


def html_to_text(html: str, max_chars: int = 8000) -> str:
    """Plain text of an HTML page, whitespace collapsed and truncated."""
    parser = _TextExtractor()
    parser.feed(html)
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    return text[:max_chars]


def article_text(url: str, max_chars: int = 8000) -> str:
    """Best-effort text of a linked article; empty when the page can't be read."""
    try:
        response = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "hn-briefing-swarm/0.1"})
        if "html" not in response.headers.get("content-type", ""):
            return ""
        return html_to_text(response.text, max_chars)
    except requests.RequestException:
        return ""
