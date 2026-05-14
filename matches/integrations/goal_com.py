"""
Best-effort fetch of Goal.com US home page for headlines.

Automated scraping can break when markup changes and may conflict with site terms or robots.txt.
Prefer official APIs or licensed feeds for production score updates; use admin for authoritative scores.
"""

from __future__ import annotations

from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

GOAL_US_HOME = "https://www.goal.com/en-us"
DEFAULT_UA = (
    "Mozilla/5.0 (compatible; GoalLine-AI/1.0; +https://github.com/) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_goal_us_html(*, timeout: float = 18.0) -> str:
    headers = {"User-Agent": DEFAULT_UA, "Accept-Language": "en-US,en;q=0.9"}
    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        r = client.get(GOAL_US_HOME)
        r.raise_for_status()
        return r.text


def parse_headlines_from_home(html: str, *, limit: int = 18) -> list[tuple[str, str]]:
    """
    Extract (title, absolute_url) pairs from anchor tags with plausible article paths.
    Heuristic only; returns fewer rows if the DOM changes.
    """
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        text = " ".join(a.get_text(" ", strip=True).split())
        if len(text) < 18 or len(text) > 300:
            continue
        if not href.startswith("/"):
            continue
        if not (href.startswith("/en-us/") or href.startswith("/en/")):
            continue
        skip = ("/betting", "/shop", "/newsletter", "/forum", "/video")
        if any(s in href.lower() for s in skip):
            continue
        full = urljoin(GOAL_US_HOME, href)
        if full in seen:
            continue
        seen.add(full)
        out.append((text, full))
        if len(out) >= limit:
            break
    return out
