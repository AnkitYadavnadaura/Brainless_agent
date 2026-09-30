"""YouTube workflows implemented using observed browser controls."""
from __future__ import annotations

from urllib.parse import quote_plus

from app.browser.actions import BrowserAction
from app.browser.client import BrowserClient
from app.browser.observer import PageObservation


class YouTubeSkill:
    HOME = "https://www.youtube.com/"

    def __init__(self, browser: BrowserClient) -> None:
        self.browser = browser

    async def search(self, query: str) -> PageObservation:
        if not query.strip():
            raise ValueError("YouTube search query is required")
        await self.browser.execute(BrowserAction(
            "navigate", url=self.HOME + "results?search_query=" + quote_plus(query)))
        return await self.browser.observe()

    async def open_recommendation(self) -> PageObservation:
        await self.browser.execute(BrowserAction("navigate", url=self.HOME))
        observation = await self.browser.observe()
        video = next((item for item in observation.elements
                      if item.role == "a" and item.href
                      and "/watch" in item.href and item.name), None)
        if video is None:
            raise RuntimeError("No visible YouTube recommendation is available")
        await self.browser.execute(BrowserAction("click", target=video.target_id))
        return await self.browser.observe()

    async def play(self) -> PageObservation:
        observation = await self.browser.observe()
        play_button = next((item for item in observation.elements
                            if item.role == "button"
                            and "play" in item.name.casefold()), None)
        if play_button is not None:
            await self.browser.execute(BrowserAction("click", target=play_button.target_id))
            observation = await self.browser.observe()
        return observation

    async def pause(self) -> PageObservation:
        observation = await self.browser.observe()
        pause_button = next((item for item in observation.elements
                             if "pause" in item.name.casefold()), None)
        if pause_button is None:
            raise RuntimeError("No visible YouTube pause control is available")
        await self.browser.execute(BrowserAction("click", target=pause_button.target_id))
        return await self.browser.observe()

    async def get_current_video(self) -> dict[str, str]:
        observation = await self.browser.observe()
        return {"url": observation.url, "title": observation.title}

    async def get_title(self) -> str:
        return (await self.browser.observe()).title
