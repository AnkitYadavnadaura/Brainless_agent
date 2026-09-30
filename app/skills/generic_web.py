"""Small generic page workflows without site-specific browser internals."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
import re
import time
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

from app.browser.actions import BrowserAction
from app.browser.client import BrowserClient


@dataclass(frozen=True, slots=True)
class CrawledPage:
    url: str
    title: str
    text: str
    depth: int


@dataclass(frozen=True, slots=True)
class CrawlResult:
    start_url: str
    pages: tuple[CrawledPage, ...]
    skipped_links: int
    truncated: bool


class GenericWebSkill:
    MAX_PAGES = 50
    MAX_DEPTH = 5
    MAX_PAGE_TEXT = 20_000
    MAX_TOTAL_TEXT = 250_000
    SENSITIVE_PATH = re.compile(
        r"(?:^|/)(?:logout|signout|sign-out|delete|unsubscribe|purchase|checkout|"
        r"remove|cancel-subscription)(?:/|$)", re.IGNORECASE)

    def __init__(self, browser: BrowserClient) -> None:
        self.browser = browser

    async def browse(self, url: str):
        await self.browser.execute(BrowserAction("navigate", url=url))
        return await self.browser.observe()

    async def extract_page(self) -> dict[str, str]:
        observation = await self.browser.observe()
        return {
            "url": observation.url, "title": observation.title,
            "text": observation.visible_text,
        }

    async def crawl(self, start_url: str, *, max_pages: int = 10,
                    max_depth: int = 2, delay_seconds: float = 0.2) -> CrawlResult:
        """Crawl visible links on one HTTPS origin using bounded browser navigation.

        Page text and links are extracted as data only. The crawler never clicks
        page controls and deliberately skips routes that look like mutations.
        """
        start_url = self.browser.policy.validate_url(start_url)
        if type(max_pages) is not int or not 1 <= max_pages <= self.MAX_PAGES:
            raise ValueError(f"max_pages must be between 1 and {self.MAX_PAGES}")
        if type(max_depth) is not int or not 0 <= max_depth <= self.MAX_DEPTH:
            raise ValueError(f"max_depth must be between 0 and {self.MAX_DEPTH}")
        if (type(delay_seconds) not in (int, float)
                or not 0 <= delay_seconds <= 2):
            raise ValueError("delay_seconds must be between 0 and 2")

        start_url = self._crawl_url(start_url)
        origin = self._origin(start_url)
        queue = deque([(start_url, 0)])
        scheduled = {start_url}
        pages: list[CrawledPage] = []
        skipped_links = 0
        total_text = 0
        truncated = False
        last_visit = 0.0

        while queue and len(pages) < max_pages and not truncated:
            url, depth = queue.popleft()
            if delay_seconds and last_visit:
                wait = delay_seconds - (time.monotonic() - last_visit)
                if wait > 0:
                    await asyncio.sleep(wait)
            await self.browser.execute(BrowserAction("navigate", url=url))
            observation = await self.browser.observe()
            last_visit = time.monotonic()
            if self._origin(observation.url) != origin:
                skipped_links += 1
                continue
            text = observation.visible_text[:self.MAX_PAGE_TEXT]
            remaining = self.MAX_TOTAL_TEXT - total_text
            if len(text) > remaining:
                text = text[:max(0, remaining)]
                truncated = True
            total_text += len(text)
            pages.append(CrawledPage(
                self._crawl_url(observation.url), observation.title[:500],
                text, depth))
            if depth >= max_depth:
                continue
            for element in observation.elements:
                if element.role not in {"a", "link"} or not element.href:
                    continue
                candidate = self._safe_link(observation.url, element.href, origin)
                if candidate is None:
                    skipped_links += 1
                    continue
                if candidate not in scheduled:
                    scheduled.add(candidate)
                    queue.append((candidate, depth + 1))
                    if len(scheduled) > max_pages * 20:
                        truncated = True
                        break

        if queue and len(pages) >= max_pages:
            truncated = True
        return CrawlResult(start_url, tuple(pages), skipped_links, truncated)

    def _safe_link(self, base_url: str, href: str, origin: tuple[str, str, int | None]) -> str | None:
        try:
            joined = urljoin(base_url, href)
            candidate = self._crawl_url(joined)
            self.browser.policy.validate_url(candidate)
        except ValueError:
            return None
        if self._origin(candidate) != origin:
            return None
        parsed = urlsplit(candidate)
        if self.SENSITIVE_PATH.search(parsed.path):
            return None
        query = parsed.query.casefold()
        if any(term in query for term in (
                "action=delete", "action=logout", "action=unsubscribe",
                "action=remove", "confirm=true")):
            return None
        return candidate

    @staticmethod
    def _crawl_url(url: str) -> str:
        parts = urlsplit(urldefrag(url).url)
        path = parts.path or "/"
        return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(),
                           path, parts.query, ""))

    @staticmethod
    def _origin(url: str) -> tuple[str, str, int | None]:
        parts = urlsplit(url)
        return parts.scheme.casefold(), (parts.hostname or "").casefold(), parts.port
