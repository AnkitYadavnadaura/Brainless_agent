"""Installed-profile browser tools keep one owned window and never switch backends silently."""
import asyncio

import pytest

from app.agents.runtime_tools import register_runtime_tools
from app.agents.tools import RiskLevel, ToolRegistry
from app.browser.external_client import ExternalBrowserClient
from tests.test_external_gmail import _inventory


class Transport:
    def __init__(self):
        self.launches = []
        self.navigations = []
        self.observations = []
        self.actions = []
        self.alive = True
        self.focused = []
        self.url = "https://example.com/"
        self.snapshots = []

    async def launch(self, arguments, marker):
        self.launches.append((arguments, marker))
        return 42

    async def window_alive(self, hwnd):
        return hwnd == 42 and self.alive

    async def focus_window(self, hwnd):
        self.focused.append(hwnd)

    async def navigate_web(self, hwnd, url):
        self.navigations.append((hwnd, url))
        self.url = url

    async def observe_web(self, hwnd):
        self.observations.append(hwnd)
        if self.snapshots:
            return self.snapshots.pop(0)
        return {"available": True, "url": self.url, "elements": [], "ocr_text": "Visible page"}

    async def web_action(self, hwnd, action, **arguments):
        self.actions.append((hwnd, action, arguments))
        return {"ok": True}


def client_fixture(tmp_path):
    transport = Transport()
    client = ExternalBrowserClient(
        tmp_path, discover=lambda **_: _inventory(tmp_path), transport_factory=lambda: transport)
    return client, transport


def test_profile_selection_precedes_launch_and_navigation_reuses_owned_window(tmp_path):
    async def scenario():
        client, transport = client_fixture(tmp_path)
        with pytest.raises(ValueError, match="Choose an external"):
            await client.open()
        assert not transport.launches
        await client.select_profile("chrome-work", "Google Chrome — Work")
        assert client.active
        assert not transport.launches
        assert client.selected_profile["id"] == "chrome-work"
        await client.open()
        await client.navigate("https://mail.google.com/")
        await client.navigate("http://example.com/docs?q=voice")
        await client.open()
        assert transport.focused == [42, 42]
        assert len(transport.launches) == 1
        assert "--profile-directory=Profile 2" in transport.launches[0][0]
        assert transport.navigations == [
            (42, "https://mail.google.com/"), (42, "http://example.com/docs?q=voice")]

    asyncio.run(scenario())


@pytest.mark.parametrize("profile,label", [
    ("not-discovered", "Google Chrome — Work"),
    ("chrome-work", "Google Chrome — Other"),
    ("managed", "Unexpected label"),
])
def test_invalid_profile_or_label_cannot_select_or_launch(tmp_path, profile, label):
    async def scenario():
        client, transport = client_fixture(tmp_path)
        with pytest.raises(ValueError):
            await client.select_profile(profile, label)
        assert not client.active
        assert not transport.launches

    asyncio.run(scenario())


def test_managed_selection_clears_external_backend_without_launching(tmp_path):
    async def scenario():
        client, transport = client_fixture(tmp_path)
        await client.select_profile("chrome-work", "Google Chrome — Work")
        await client.select_profile("managed", "Managed browser")
        assert client.selected_profile is None
        assert not client.active
        assert not transport.launches

    asyncio.run(scenario())


@pytest.mark.parametrize("url", ["file:///C:/secret.txt", "ftp://example.com/", "https://user:pass@example.com/"])
def test_external_navigation_rejects_non_web_urls_before_launch(tmp_path, url):
    async def scenario():
        client, transport = client_fixture(tmp_path)
        await client.select_profile("chrome-work", "Google Chrome — Work")
        with pytest.raises(ValueError):
            await client.navigate(url)
        assert not transport.launches
        assert not transport.navigations

    asyncio.run(scenario())


def test_observation_never_launches_missing_or_closed_session(tmp_path):
    async def scenario():
        client, transport = client_fixture(tmp_path)
        assert (await client.observe())["available"] is False
        await client.select_profile("chrome-work", "Google Chrome — Work")
        assert (await client.observe())["available"] is False
        assert not transport.launches
        await client.open()
        snapshot = await client.observe()
        assert snapshot["backend"] == "native"
        assert snapshot["profile_id"] == "chrome-work"
        assert snapshot["ocr_text"] == "Visible page"
        transport.alive = False
        assert (await client.observe())["available"] is False
        assert len(transport.launches) == 1

    asyncio.run(scenario())


def test_generic_playback_uses_current_window_and_visible_play_control(tmp_path):
    async def scenario():
        client, transport = client_fixture(tmp_path)
        await client.select_profile("chrome-work", "Google Chrome — Work")
        await client.open()
        transport.snapshots = [
            {"url": "https://www.youtube.com/watch?v=current", "elements": [
                {"runtime_id": "play-button", "type": "button", "label": "Play (k)"}]},
            {"url": "https://www.youtube.com/watch?v=current", "elements": [
                {"runtime_id": "pause-button", "type": "button", "label": "Pause (k)"}]},
        ]
        assert "Playing" in await client.play_youtube("recommendation")
        assert len(transport.launches) == 1
        assert transport.navigations == []
        assert transport.actions[0][0:2] == (42, "click")
        assert transport.actions[0][2]["target"] == "play-button"

    asyncio.run(scenario())


def test_playback_waits_for_dynamic_controls_and_confirms_live_video_without_reopening(tmp_path):
    async def scenario():
        client, transport = client_fixture(tmp_path)
        choice = client.catalog()[0]
        await client.select_profile(choice["id"], choice["label"])
        await client.open()
        url = "https://www.youtube.com/live/current"
        def snapshot(label=None):
            return {"url": url, "elements": ([{
                "runtime_id": "4.4", "type": "button", "label": label}] if label else [])}
        transport.snapshots = [snapshot(), snapshot("Play (k)"), snapshot(), snapshot("Pause (k)")]
        assert "Playing" in await client.play_youtube("current")
        assert transport.navigations == []
        assert len(transport.actions) == 1
        assert len(transport.observations) == 4
    asyncio.run(scenario())


class ForbiddenManagedBrowser:
    def __getattr__(self, name):
        raise AssertionError(f"External action touched managed browser: {name}")


class ExternalAdapter:
    active = True

    def __init__(self):
        self.calls = []

    async def open(self):
        self.calls.append(("open",))
        return "opened"

    async def navigate(self, url):
        self.calls.append(("navigate", url))
        return url

    async def observe(self):
        self.calls.append(("observe",))
        return {"available": True, "title": "Current external page", "backend": "native"}

    async def search_youtube(self, query):
        self.calls.append(("search", query))
        return "results"

    async def play_youtube(self, query):
        self.calls.append(("play", query))
        return "playing"

    async def control_youtube(self, action, seconds):
        self.calls.append(("control", action, seconds))
        return "controlled"

    async def interact(self, action, **arguments):
        self.calls.append(("interact", action, arguments))
        return {"ok": True}


def test_registered_browser_and_youtube_tools_use_external_adapter_exclusively(tmp_path):
    async def scenario():
        external = ExternalAdapter()
        registry = ToolRegistry()
        register_runtime_tools(registry, ForbiddenManagedBrowser(), tmp_path, external_browser=external)
        for function, arguments in (
            ("browser.open", {}),
            ("browser.navigate", {"url": "example.com"}),
            ("browser.observe", {}),
            ("browser.read_title", {"url": "https://example.com"}),
            ("youtube.search", {"query": "Python lessons"}),
            ("youtube.play", {"query": "recommendation"}),
            ("youtube.control", {"action": "pause", "seconds": 0}),
        ):
            await registry.invoke(function, arguments)
        assert external.calls == [
            ("open",), ("navigate", "https://example.com"), ("observe",), ("observe",),
            ("search", "Python lessons"), ("play", "recommendation"), ("control", "pause", 0),
        ]

    asyncio.run(scenario())


def test_external_action_requires_complete_schema_and_forwards_observed_target(tmp_path):
    async def scenario():
        external = ExternalAdapter()
        registry = ToolRegistry()
        register_runtime_tools(registry, ForbiddenManagedBrowser(), tmp_path, external_browser=external)
        spec = registry.get("browser.external_action")
        assert spec.risk is RiskLevel.HIGH
        with pytest.raises(ValueError, match="Missing tool arguments"):
            await registry.invoke("browser.external_action", {"action": "click"})
        assert external.calls == []
        await registry.invoke("browser.external_action", {
            "action": "click", "target": "visible-control-7", "text": None,
            "key": None, "direction": None, "amount": None,
        })
        assert external.calls == [("interact", "click", {
            "target": "visible-control-7", "text": None, "key": None, "direction": None, "amount": 3,
        })]

    asyncio.run(scenario())
