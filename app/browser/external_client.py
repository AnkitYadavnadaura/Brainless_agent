"""General website interaction in an explicitly selected installed browser profile."""
from __future__ import annotations

import asyncio
import re
from urllib.parse import quote_plus, urlsplit

from app.browser.external_gmail import ExternalGmailProfiles
from app.browser.url_validation import normalize_web_url
from app.browser.methods import MethodUnavailable, run_methods
from app.browser.task_scripts import YOUTUBE_INSPECT, YOUTUBE_PLAY
from app.browser.native_console import NativeAccessibilityError


class ExternalBrowserClient(ExternalGmailProfiles):
    """Keep one owned window per profile and continue in its current tab."""

    def __init__(self, root, **kwargs):
        super().__init__(root, **kwargs)
        self._selection: dict[str, str] | None = None

    @property
    def selected_profile(self) -> dict[str, str] | None:
        return dict(self._selection) if self._selection else None

    @property
    def active(self) -> bool:
        return self._selection is not None

    async def select_profile(self, profile_id: str, profile_label: str) -> str:
        async with self._lock:
            if profile_id == "managed":
                if profile_label != "Managed browser":
                    raise ValueError("Managed browser selection label is invalid")
                self._selection = None
                return "Using the managed browser"
            self._selected_profile(profile_id, profile_label)
            choice = next((item for item in self.catalog() if item["id"] == profile_id), None)
            if choice is None:
                raise ValueError("The selected profile is no longer available")
            self._selection = dict(choice)
            return f"Using {profile_label}"

    async def _session(self):
        selected = self._selection
        if selected is None:
            raise ValueError("Choose an external browser profile first")
        browser, profile = self._selected_profile(selected["id"], selected["label"])
        return await self._get_owned_window(selected["id"], browser, profile)

    async def open(self) -> str:
        async with self._lock:
            transport, hwnd = await self._session()
            await transport.focus_window(hwnd)
            return f"Opened {self._selection['label']}"

    async def navigate(self, url: str) -> str:
        target = normalize_web_url(url)
        async with self._lock:
            transport, hwnd = await self._session()
            await transport.navigate_web(hwnd, target)
            return target

    async def observe(self) -> dict:
        async with self._lock:
            if not self._selection:
                return {"available": False, "reason": "Choose a browser profile first"}
            # Observation never starts a new window on a missing or closed session.
            hwnd = self._windows.get(self._selection["id"])
            transport = self._get_transport()
            if hwnd is None or not await transport.window_alive(hwnd):
                return {"available": False, "backend": "native",
                        "reason": "The selected browser window is closed. Open the browser again."}
            diagnostics = []
            for attempt in range(2):
                try:
                    result = await transport.observe_web(hwnd)
                    break
                except NativeAccessibilityError as error:
                    diagnostics.append({'method': 'accessibility', 'attempt': attempt + 1,
                                        'error': str(error)[:300]})
            else:
                browser, _ = self._selected_profile(self._selection['id'], self._selection['label'])
                result = await transport.observe_web_dom(hwnd, browser.family)
                diagnostics.append({'method': 'dom', 'status': 'observed' if result.get('available') else 'unavailable'})
            if diagnostics:
                result['diagnostics'] = diagnostics
            console_diagnostics = getattr(transport, 'console_diagnostics', {}).get(hwnd)
            if isinstance(console_diagnostics, dict):
                result['console_diagnostics'] = console_diagnostics
            return {**result, "profile": self._selection["label"],
                    "profile_id": self._selection["id"], "backend": "native"}

    async def extract_dom(self) -> dict:
        """Extract structured DOM elements from external browser console or UIA snapshot."""
        async with self._lock:
            if not self._selection:
                return {"available": False, "reason": "Choose an external browser profile first"}
            hwnd = self._windows.get(self._selection["id"])
            transport = self._get_transport()
            if hwnd is None or not await transport.window_alive(hwnd):
                return {"available": False, "reason": "The selected browser window is closed"}
            try:
                dom = await transport.extract_console_dom(hwnd)
                if dom and isinstance(dom, dict) and dom.get("elements"):
                    return {"available": True, "source": "console", **dom}
            except Exception:
                pass
            obs = await transport.observe_web(hwnd)
            elements = []
            for el in obs.get("elements", []):
                elements.append({
                    "tag": el.get("type", "").replace("ControlType.", "").lower(),
                    "role": el.get("type", "").replace("ControlType.", "").lower(),
                    "text": el.get("label", ""),
                    "rect": el.get("rect", []),
                    "selector": el.get("runtime_id", ""),
                    "visible": not el.get("offscreen", False),
                })
            return {
                "available": True,
                "source": "accessibility",
                "url": obs.get("url", ""),
                "title": obs.get("title", ""),
                "elements": elements,
            }

    async def register_user_region(self, bounds, *, window_id: int, url: str) -> str:
        """Register explicit user guidance only for the still-selected observed window."""
        async with self._lock:
            if not self._selection:
                raise ValueError("Choose an external browser profile first")
            hwnd = self._windows.get(self._selection["id"])
            transport = self._get_transport()
            if hwnd != window_id or hwnd is None or not await transport.window_alive(hwnd):
                raise RuntimeError("The selected browser window changed; observe and select again")
            return await transport.register_user_region(hwnd, bounds, url)

    async def interact(self, action: str, *, target=None, text=None, key=None,
                       direction=None, amount=3) -> dict:
        async with self._lock:
            if not self._selection:
                raise ValueError("Choose an external browser profile first")
            hwnd = self._windows.get(self._selection["id"])
            transport = self._get_transport()
            if hwnd is None or not await transport.window_alive(hwnd):
                raise RuntimeError("The selected browser window is closed; open it again")
            return await transport.web_action(hwnd, action, target=target, text=text,
                                               key=key, direction=direction, amount=amount)

    async def search_youtube(self, query: str) -> str:
        if not isinstance(query, str) or not query.strip() or len(query) > 2000:
            raise ValueError("YouTube search must contain 1-2000 characters")
        return await self.navigate("https://www.youtube.com/results?search_query=" + quote_plus(query.strip()))

    @staticmethod
    def _youtube(snapshot: dict) -> bool:
        return (urlsplit(snapshot.get("url", "")).hostname or "").casefold() in {
            "www.youtube.com", "youtube.com", "m.youtube.com", "music.youtube.com"}

    @staticmethod
    def _button(snapshot: dict, pattern: str):
        matches = [item for item in snapshot.get("elements", [])
                   if item.get("enabled", True) and item.get("type") in {"ControlType.Button", "button"}
                   and re.search(pattern, item.get("label", ""), re.IGNORECASE)]
        return matches[0] if len(matches) == 1 else None

    @classmethod
    def _video_page(cls, snapshot: dict) -> bool:
        path = urlsplit(snapshot.get("url", "")).path.rstrip("/")
        return cls._youtube(snapshot) and (path == "/watch" or path.startswith("/live/")
                                          or path.startswith("/shorts/"))

    @staticmethod
    def _video_links(snapshot: dict) -> list[dict]:
        return [item for item in snapshot.get("elements", [])
                if item.get("enabled", True) and item.get("type") in {"ControlType.Hyperlink", "link"}
                and re.search(r"\bviews?\b|\bago\b|\bminutes?\b|\bseconds?\b|\d+:\d+",
                              item.get("label", ""), re.IGNORECASE)]

    async def _wait_for(self, snapshot: dict, predicate) -> dict:
        # Dynamic sites can expose the URL before controls reach the UIA tree.
        # Refresh evidence without retrying clicks or opening another page.
        for _ in range(4):
            if predicate(snapshot):
                break
            await asyncio.sleep(.5)
            snapshot = await self.observe()
        return snapshot

    async def play_youtube(self, query: str) -> str:
        self.last_method_attempts = []
        return await run_methods([
            ("accessibility", lambda: self._play_youtube_accessibility(query)),
            ("dom", self._play_youtube_dom),
        ], attempts=self.last_method_attempts)

    async def _play_youtube_dom(self) -> str:
        async with self._lock:
            if not self._selection:
                raise ValueError("Choose an external browser profile first")
            hwnd = self._windows.get(self._selection["id"])
            transport = self._get_transport()
            if hwnd is None or not await transport.window_alive(hwnd):
                raise RuntimeError("The selected browser window is closed; open it again")
            if not callable(getattr(transport, "evaluate", None)):
                raise MethodUnavailable("This browser transport has no DOM playback method")
            browser, _ = self._selected_profile(self._selection["id"], self._selection["label"])
            result = await transport.evaluate(hwnd, browser.family, YOUTUBE_INSPECT)
            if result.get("ok") is not True:
                raise MethodUnavailable(str(result.get("error", "No visible video found")))
            if result.get("url"):
                target = normalize_web_url(result["url"])
                parsed = urlsplit(target)
                if (parsed.scheme != "https" or parsed.hostname not in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
                        or not re.match(r"^/(watch|live|shorts)(/|$)", parsed.path)):
                    raise MethodUnavailable("DOM result was not a supported YouTube video")
                await transport.navigate_web(hwnd, target)
            result = await transport.evaluate(hwnd, browser.family, YOUTUBE_PLAY)
            if result.get("ok") is not True or result.get("playing") is not True:
                raise MethodUnavailable(str(result.get("error", "Playback could not be verified")))
            return "Playing the current YouTube video in the selected profile (verified using DOM)"

    async def _play_youtube_accessibility(self, query: str) -> str:
        query = str(query).strip()
        if not query:
            raise ValueError("A video request is required")
        generic = query.casefold() in {"recommendation", "video", "a video", "any video", "any", "current",
                                      "resume", "continue", "play video", "play a video"}
        if not generic:
            parsed = urlsplit(query)
            if parsed.scheme:
                if parsed.scheme != "https" or parsed.hostname not in {
                        "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}:
                    raise ValueError("Use a supported HTTPS YouTube video URL")
                await self.navigate(query)
            else:
                await self.search_youtube(query)
        snapshot = await self.observe()
        if generic and not self._youtube(snapshot) and query.casefold() not in {"current", "resume", "continue"}:
            await self.navigate("https://www.youtube.com/")
            snapshot = await self._wait_for(await self.observe(), self._youtube)
        if not generic:
            snapshot = await self._wait_for(snapshot, self._youtube)
        if not self._youtube(snapshot):
            if generic:
                raise RuntimeError("Open YouTube in the selected profile before asking to play a video")
            raise RuntimeError("YouTube has not finished loading; repeat the request when it is visible")
        if not self._video_page(snapshot):
            # Select only a visible accessibility link with video-card evidence.
            snapshot = await self._wait_for(snapshot, lambda page: self._video_page(page) or self._video_links(page))
            if not self._video_page(snapshot):
                choices = self._video_links(snapshot) if self._youtube(snapshot) else []
                if not choices:
                    raise MethodUnavailable("No visible video link could be identified. Say which visible video to open.")
                await self.interact("click", target=choices[0]["runtime_id"])
                snapshot = await self._wait_for(await self.observe(), self._video_page)
                if not self._video_page(snapshot):
                    raise MethodUnavailable("The selected link did not open a verified YouTube video")
        snapshot = await self._wait_for(snapshot, lambda page: (
            self._button(page, r"^Pause(?:\s|$|\()") or self._button(page, r"^Play(?:\s*\(k\))?$")))
        if not self._video_page(snapshot):
            raise RuntimeError("The current YouTube video changed before playback")
        if self._button(snapshot, r"^Pause(?:\s|$|\()"):
            return "The current YouTube video is playing"
        play = self._button(snapshot, r"^Play(?:\s*\(k\))?$")
        if play is None:
            raise MethodUnavailable("The current video has no unique visible Play control")
        await self.interact("click", target=play["runtime_id"])
        video_url = snapshot.get("url")
        snapshot = await self._wait_for(await self.observe(),
            lambda page: self._button(page, r"^Pause(?:\s|$|\()"))
        if snapshot.get("url") != video_url or not self._button(snapshot, r"^Pause(?:\s|$|\()"):
            raise MethodUnavailable("Play was requested, but playback could not be verified")
        return "Playing the current YouTube video in the selected profile"

    async def control_youtube(self, action: str, seconds=0) -> str:
        snapshot = await self.observe()
        if not self._video_page(snapshot):
            raise RuntimeError("No current YouTube video is open in the selected profile")
        if action == "play":
            return await self.play_youtube("current")
        patterns = {"pause": r"^Pause(?:\s|$|\()", "skip_ad": r"^Skip(?: ad| ads)?$",
                    "next_video": r"^Next(?:\s|$|\()"}
        if action not in patterns or seconds != 0:
            raise ValueError("External playback supports play, pause, skip_ad and next_video with seconds=0")
        if action == "pause" and self._button(snapshot, r"^Play(?:\s*\(k\))?$"):
            return "The current YouTube video is paused"
        target = self._button(snapshot, patterns[action])
        if target is None:
            raise RuntimeError("The requested playback control is not uniquely visible")
        await self.interact("click", target=target["runtime_id"])
        if action == "pause":
            video_url = snapshot.get("url")
            snapshot = await self._wait_for(await self.observe(),
                lambda page: self._button(page, r"^Play(?:\s*\(k\))?$"))
            if snapshot.get("url") != video_url or not self._button(snapshot, r"^Play(?:\s*\(k\))?$"):
                raise RuntimeError("Pause was requested, but the paused state could not be verified")
            return "YouTube video paused"
        return "Requested YouTube " + action.replace("_", " ")
