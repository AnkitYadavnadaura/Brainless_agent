"""A dedicated Chromium leader using the same website/receipt protocol as peers.

Playwright controls only its isolated persistent profile. It evaluates the fixed
DOM program directly; neither clipboard console pasting nor a debugging port is
used. The integer transport handle identifies this context, not a Win32 HWND.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from app.providers.native_website import DOM_PROGRAM, NativeClientError, NativeSessionStore, NativeWebsiteClient


class ChromiumTransport:
    input_mode = 'playwright'

    def __init__(self, pages, *, timeout_seconds=30):
        self.pages = pages
        self.timeout_seconds = min(30, timeout_seconds)

    def _page(self, handle, tab_index):
        if handle != 1 or tab_index not in self.pages:
            raise NativeClientError('Unknown managed Chromium tab', submitted=False)
        page = self.pages[tab_index]
        if page.is_closed():
            raise NativeClientError('Managed Chromium tab was closed', submitted=False)
        return page

    @staticmethod
    def _host(tab_index):
        return {1: 'chatgpt.com', 2: 'gemini.google.com'}[tab_index]

    async def navigate(self, hwnd, url, *, tab_index):
        page = self._page(hwnd, tab_index)
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.hostname != self._host(tab_index)
                or parsed.username or parsed.password or parsed.port not in (None, 443)):
            raise ValueError('Leader navigation must stay on its assigned provider')
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout_seconds * 1000)
        except Exception as error:
            raise NativeClientError('Chromium navigation failed: ' + type(error).__name__, submitted=False) from error

    async def evaluate(self, hwnd, family, script, *, tab_index):
        page = self._page(hwnd, tab_index)
        prefix = '(' + DOM_PROGRAM + ')('
        if family != 'chromium' or not script.startswith(prefix) or not script.endswith(')'):
            raise ValueError('Leader accepts only the runtime-owned website program')
        payload = json.loads(script[len(prefix):-1])
        if (not isinstance(payload, dict) or payload.get('action') not in {'bind', 'observe', 'prepare', 'submit'}
                or payload.get('origin') != 'https://' + self._host(tab_index)):
            raise ValueError('Invalid leader website operation')
        # Authentication redirects are an owner action, never a selector repair.
        host = urlsplit(page.url).hostname
        if host in {'accounts.google.com', 'auth.openai.com', 'auth0.openai.com'}:
            return {'error': 'login'}
        try:
            return await asyncio.wait_for(page.evaluate(DOM_PROGRAM, payload), self.timeout_seconds)
        except Exception as error:
            raise NativeClientError('Chromium website operation failed: ' + type(error).__name__,
                                    submitted=payload['action'] == 'submit') from error


class ChromiumLeader:
    def __init__(self, root: Path, *, timeout_seconds=180, poll_interval=2,
                 rollover_after=20, progress=print, playwright_factory=None,
                 user_data_dir=None, channel=None, participant_prefix='chromium-leader', profile_directory=None):
        if channel not in (None, 'chrome'):
            raise ValueError('Leader channel must be bundled Chromium or installed Chrome')
        if not re.fullmatch(r'[a-z0-9-]{1,100}', participant_prefix):
            raise ValueError('Invalid leader participant identity')
        if profile_directory is not None and not re.fullmatch(r'Default|Profile \d+', profile_directory):
            raise ValueError('Invalid Chrome profile directory')
        self.root = Path(root)
        self.user_data_dir = Path(user_data_dir) if user_data_dir is not None else self.root / 'data/chromium-leader'
        self.channel, self.participant_prefix, self.profile_directory = channel, participant_prefix, profile_directory
        self.timeout_seconds, self.poll_interval = timeout_seconds, poll_interval
        self.rollover_after, self.progress = rollover_after, progress
        self.playwright_factory = playwright_factory
        self.driver = self.context = self.transport = None
        self.participants = []
        self.excluded_providers = set()
        self._lock = asyncio.Lock()

    async def start(self):
        async with self._lock:
            if self.participants:
                return self.participants
            if self.playwright_factory is None:
                from playwright.async_api import async_playwright
                self.playwright_factory = async_playwright
            # Finish launch even if cancellation arrives so its returned context
            # can be closed. No owned process is abandoned during cancellation.
            from app.browser.fleet import _finish_owned_operation
            try:
                pending, cancellation = await _finish_owned_operation(self.playwright_factory().start())
                self.driver = pending.result()
                if cancellation:
                    raise cancellation
                pending, cancellation = await _finish_owned_operation(
                    self.driver.chromium.launch_persistent_context(
                        user_data_dir=str(self.user_data_dir), headless=False,
                        chromium_sandbox=True, timeout=30000,
                        **({'channel': self.channel} if self.channel else {}),
                        **({'args': ['--profile-directory=' + self.profile_directory]} if self.profile_directory else {}),
                        ignore_default_args=['--unsafely-disable-devtools-self-xss-warnings']))
                self.context = pending.result()
                if cancellation:
                    raise cancellation
                pages = {}
                for index, name in enumerate(('chatgpt', 'gemini'), 1):
                    if name not in self.excluded_providers:
                        pages[index] = await self.context.new_page()
                self.transport = ChromiumTransport(pages, timeout_seconds=self.timeout_seconds)
                store = NativeSessionStore(self.root / 'data/browser-team/native-sessions.sqlite3')
                clients = []
                for index, provider in enumerate(('chatgpt', 'gemini'), 1):
                    if provider in self.excluded_providers:
                        continue
                    url = 'https://chatgpt.com/' if index == 1 else 'https://gemini.google.com/app'
                    # A failed site load must not discard the other leader tab.
                    try:
                        await self.transport.navigate(1, url, tab_index=index)
                    except NativeClientError as error:
                        self.progress(f'Chromium leader / {provider}: {error}; readiness will recheck.')
                    client = NativeWebsiteClient(
                        participant_id=self.participant_prefix + ':' + provider, provider_name=provider,
                        hwnd=1, family='chromium', tab_index=index, transport=self.transport, store=store,
                        timeout_seconds=self.timeout_seconds, poll_interval=self.poll_interval,
                        rollover_after=self.rollover_after, input_mode='console')
                    client.team_role = 'leader'
                    clients.append(client)
                self.participants = clients
                self.progress(f'Chromium leader opened: {len(clients)} provider tabs; readiness will check their sign-in.')
                return self.participants
            except BaseException:
                cleanup, _ = await _finish_owned_operation(self._close())
                cleanup.result()
                raise

    async def _close(self):
        try:
            if self.context is not None:
                await self.context.close()
        finally:
            self.context = None
            self.participants = []
            if self.driver is not None:
                await self.driver.stop()
                self.driver = None

    async def close(self):
        from app.browser.fleet import _finish_owned_operation
        async with self._lock:
            cleanup, cancellation = await _finish_owned_operation(self._close())
            try:
                cleanup.result()
            finally:
                if cancellation:
                    raise cancellation
