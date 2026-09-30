"""Playwright-backed persistent Chrome session manager."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit
from uuid import uuid4

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from app.config.settings import BrowserSettings

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.browser.client import BrowserClient


class BrowserManager:
    """Owns one persistent user-visible browser context; it never handles credentials."""

    def __init__(self, settings: BrowserSettings, repository_root: Path) -> None:
        self._settings = settings
        self._repository_root = repository_root
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._conversation_pages: dict[str, Page] = {}
        self._project_pages: dict[str, Page] = {}
        self._user_page: Page | None = None
        self._tab_ids: dict[Page, str] = {}
        self._conversation_file = repository_root / "data/conversation-urls.json"

    async def start(self) -> None:
        if self._context:
            return
        profile_dir = self._settings.profile_dir
        if not profile_dir.is_absolute():
            profile_dir = self._repository_root / profile_dir
        profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        try:
            self._context = await self._playwright.chromium.launch_persistent_context(
                str(profile_dir), channel=self._settings.channel,
                headless=self._settings.headless,
                viewport={"width": 1440, "height": 1000},
            )
        except Exception:
            await self._playwright.stop()
            self._playwright = None
            raise
        self._context.set_default_timeout(self._settings.navigation_timeout_seconds * 1000)
        LOGGER.info("Persistent Chrome session started: %s", profile_dir)

    def _is_conversation_page(self, page: Page) -> bool:
        return any(page is owned for owned in (
            *self._conversation_pages.values(), *self._project_pages.values()))

    def current_user_page(self) -> Page | None:
        """Return the live user tab without starting, navigating, or focusing Chrome."""
        page = self._user_page
        if (self._context is None or page is None or page.is_closed()
                or self._is_conversation_page(page)
                or not any(page is candidate for candidate in self._context.pages)):
            return None
        return page

    def tab_id_for(self, page: Page) -> str:
        """Identify one owned live user tab across URL changes within this session."""
        if (self._context is None or page.is_closed() or self._is_conversation_page(page)
                or not any(page is candidate for candidate in self._context.pages)):
            raise ValueError("Only a live user browser tab can be observed")
        if page not in self._tab_ids:
            self._tab_ids[page] = "user-tab-" + uuid4().hex
        return self._tab_ids[page]

    async def open_user_page(self) -> Page:
        """Show an owned browsing tab without navigating a reasoning conversation."""
        if self._context is None:
            await self.start()
        page = self._user_page
        if page is None or page.is_closed() or self._is_conversation_page(page):
            page = next((candidate for candidate in self._context.pages
                         if not candidate.is_closed() and candidate.url == "about:blank"
                         and not self._is_conversation_page(candidate)), None)
        if page is None:
            page = await self._context.new_page()
        self._user_page = page
        await page.bring_to_front()
        return page

    async def page_for(self, url: str, *, exact: bool = False) -> Page:
        """Open or focus a browsing page, starting Chrome on first use.

        Read/control callers can reuse a child URL such as a YouTube video.
        Explicit navigation requests use ``exact`` to visit the URL in the
        current user tab, keeping multi-turn browsing in the same tab.
        Provider conversation tabs are never reused for user browsing.
        """
        if self._context is None:
            await self.start()
        candidates = [page for page in self._context.pages
                      if not page.is_closed() and not self._is_conversation_page(page)]
        if self._user_page in candidates:
            candidates.remove(self._user_page)
            candidates.insert(0, self._user_page)
        page = self.current_user_page() if exact else None
        if page is None:
            page = next((candidate for candidate in candidates
                         if candidate.url.startswith(url) and self._same_origin(candidate.url, url)), None)
        if page is None and self._user_page in candidates and self._user_page.url == "about:blank":
            page = self._user_page
        if page is None:
            page = await self._context.new_page()
        self._user_page = page
        await page.bring_to_front()
        if (page.url != url if exact else not page.url.startswith(url)):
            await page.goto(url, wait_until="domcontentloaded")
        return page

    def browser_client(self, **options: Any) -> "BrowserClient":
        """Create a generic automation client on this owned browser context."""
        if not self._context:
            raise RuntimeError("BrowserManager.start() must be called first")
        from app.browser.client import BrowserClient
        from app.browser.sessions import BrowserSessionStore

        options.setdefault(
            "store",
            BrowserSessionStore(self._repository_root / "data/browser-sessions.sqlite3"))
        options.setdefault("browser_id", "browser-manager")
        return BrowserClient(self._context, **options)

    async def conversation_page(self, provider: str, prompt: str, base_url: str, *, reuse_provider_tab: bool = False) -> Page:
        """Return the dedicated, persistent tab for one provider/prompt pair.

        A prompt digest avoids writing prompt content to disk.  Saved URLs let a
        later run reopen the same provider conversation, while the in-memory map
        prevents two prompts from accidentally sharing a tab during this run.
        Project workflows pass a stable session key and reuse_provider_tab=True
        to keep successive prompts in one continuing chat and browser tab.
        """
        if not self._context:
            raise RuntimeError("BrowserManager.start() must be called first")
        key = self._conversation_key(provider, prompt)
        page = self._conversation_pages.get(key)
        if page is not None and not page.is_closed():
            if reuse_provider_tab:
                self._project_pages[provider] = page
            await page.bring_to_front()
            return page

        saved_url = self._load_conversation_urls().get(key, base_url)
        if not self._same_origin(saved_url, base_url):
            LOGGER.warning("Ignoring invalid saved %s conversation URL", provider)
            saved_url = base_url
        # Persistent Chrome can restore tabs itself. Reattach to an exact saved
        # conversation rather than opening a duplicate; never share a generic
        # provider landing page because each new prompt needs its own tab.
        project_page = self._project_pages.get(provider) if reuse_provider_tab else None
        if project_page is not None and (project_page.is_closed() or not self._same_origin(project_page.url, base_url)):
            project_page = None
        page = (project_page or next((candidate for candidate in self._context.pages
                      if saved_url != base_url and candidate.url == saved_url and not candidate.is_closed()), None)
                or (next((candidate for candidate in self._context.pages
                          if not candidate.is_closed() and candidate.url.rstrip('/') == base_url.rstrip('/')),None)
                    if reuse_provider_tab else None)
                or await self._context.new_page())
        if reuse_provider_tab:
            # One project owns this tab at a time. Keeping aliases would make a
            # later switch back to an earlier project silently use the wrong chat.
            self._conversation_pages = {old_key: old_page for old_key, old_page in self._conversation_pages.items()
                                        if old_page is not page}
            self._project_pages[provider] = page
        self._conversation_pages[key] = page
        await page.goto(saved_url, wait_until="domcontentloaded")
        await page.bring_to_front()
        return page

    async def rotate_conversation(self, provider: str, prompt: str, base_url: str) -> Page:
        """Replace only this project's owned tab with a fresh, empty chat.

        The provider must verify that no response is in flight before calling.
        Unrelated tabs, including other chats at the same provider, are untouched.
        The stable session key immediately points to the new chat on disk, so a
        restart cannot accidentally restore the conversation that was rotated out.
        """
        if not self._context:
            raise RuntimeError("BrowserManager.start() must be called first")
        key = self._conversation_key(provider, prompt)
        page = self._conversation_pages.get(key)
        if page is None or self._project_pages.get(provider) is not page:
            raise RuntimeError("Cannot rotate a conversation tab not owned by this project")
        if not page.is_closed() and not self._same_origin(page.url, base_url):
            raise RuntimeError("Cannot rotate a project tab navigated away from its provider")
        self.remember_conversation(provider, prompt, base_url, base_url)
        if not page.is_closed():
            await page.close()
        self._conversation_pages = {old_key: old_page for old_key, old_page in self._conversation_pages.items()
                                    if old_page is not page}
        self._project_pages.pop(provider, None)
        # Close before opening: the workflow never has two active project tabs.
        fresh = await self._context.new_page()
        self._conversation_pages[key] = fresh
        self._project_pages[provider] = fresh
        await fresh.goto(base_url, wait_until="domcontentloaded")
        await fresh.bring_to_front()
        return fresh

    async def reopen_conversation(self, provider: str, prompt: str, base_url: str) -> Page | None:
        """Reload this owned chat for response recovery; never start a new chat."""
        key = self._conversation_key(provider, prompt)
        page = self._conversation_pages.get(key)
        if page is not None and not page.is_closed():
            if self._project_pages.get(provider) is not page or not self._same_origin(page.url, base_url):
                return None
            self.remember_conversation(provider, prompt, page.url, base_url)
            await page.reload(wait_until="domcontentloaded")
            await page.bring_to_front()
            return page
        saved_url = self._load_conversation_urls().get(key, base_url)
        if saved_url.rstrip('/') == base_url.rstrip('/') or not self._same_origin(saved_url, base_url):
            return None
        return await self.conversation_page(provider, prompt, base_url, reuse_provider_tab=True)

    def remember_conversation(self, provider: str, prompt: str, url: str, base_url: str) -> None:
        """Persist a provider-owned chat URL without retaining the prompt text."""
        if not self._same_origin(url, base_url):
            LOGGER.warning("Refusing to save off-origin %s conversation URL", provider)
            return
        conversations = self._load_conversation_urls()
        conversations[self._conversation_key(provider, prompt)] = url
        self._conversation_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._conversation_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(conversations, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self._conversation_file)

    @staticmethod
    def _conversation_key(provider: str, prompt: str) -> str:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return f"{provider}:{digest}"

    def _load_conversation_urls(self) -> dict[str, str]:
        try:
            value = json.loads(self._conversation_file.read_text(encoding="utf-8"))
            return {str(key): str(url) for key, url in value.items()} if isinstance(value, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    async def restore_conversations(self) -> list[str]:
        """Reattach in-memory conversation pages to any matching restored URLs.

        This avoids creating duplicate tabs at startup when the persistent
        Chrome session already contains provider-owned conversation pages.
        Returns the list of URLs that were reattached.
        """
        if not self._context:
            raise RuntimeError("BrowserManager.start() must be called first")
        restored: list[str] = []
        conversations = self._load_conversation_urls()
        if not conversations:
            return restored
        # For each saved conversation key, try to find an existing page with the exact URL
        for key, url in conversations.items():
            try:
                candidate = next((p for p in self._context.pages if p.url == url and not p.is_closed()), None)
            except Exception:
                candidate = None
            if candidate is not None:
                self._conversation_pages[key] = candidate
                restored.append(url)
        return restored

    @staticmethod
    def _same_origin(candidate: str, base_url: str) -> bool:
        candidate_parts, base_parts = urlsplit(candidate), urlsplit(base_url)
        return (candidate_parts.scheme, candidate_parts.netloc) == (base_parts.scheme, base_parts.netloc)

    async def close(self) -> None:
        if self._context:
            await self._context.close()
            self._context = None
            self._conversation_pages.clear()
            self._project_pages.clear()
            self._user_page = None
            self._tab_ids.clear()
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        LOGGER.info("Browser session closed")
