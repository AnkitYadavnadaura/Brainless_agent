"""Generic native browsing stays inside owned windows and observed UIA controls."""
import asyncio
from io import BytesIO
from types import SimpleNamespace
import re
from urllib.parse import unquote

import pytest

from app.browser.native_console import NativeTransportError
from app.browser.external_client import ExternalBrowserClient
from app.computer.ocr import OcrUnavailable
from tests.test_native_console import Desktop, owned, transport
from tests.test_external_gmail import _inventory


class WebDesktop(Desktop):
    def __init__(self):
        super().__init__()
        self.page_url = "https://www.youtube.com/watch?v=test"
        self.focused_id, self.address_value = "2.2", self.page_url
        self.covered = self.change_during_screenshot = self.truncated = False
        self.nodes = [
            dict(id=0, parent=-1, runtime_id="0.0", name="Browser", type="ControlType.Window", rect=[0, 0, 800, 600]),
            dict(id=1, parent=0, runtime_id="1.1", name="Address and search bar", type="ControlType.Edit",
                 rect=[100, 20, 600, 30], editable=True),
            dict(id=2, parent=0, runtime_id="2.2", name="YouTube", type="ControlType.Document", rect=[0, 60, 800, 540]),
            dict(id=3, parent=2, runtime_id="3.3", name="Funny cats", type="ControlType.Text", rect=[20, 70, 200, 20]),
            dict(id=4, parent=2, runtime_id="4.4", name="Play", type="ControlType.Button", rect=[300, 100, 80, 40]),
            dict(id=5, parent=2, runtime_id="5.5", name="Search", type="ControlType.Edit", rect=[20, 100, 200, 40], editable=True),
            dict(id=6, parent=2, runtime_id="6.6", name="Password", type="ControlType.Edit", rect=[20, 160, 200, 40], password=True),
            dict(id=7, parent=5, runtime_id="7.7", name="private typed draft", type="ControlType.Text", rect=[25, 105, 150, 20]),
        ]
        for node in self.nodes:
            node.setdefault("enabled", True)
            node.setdefault("offscreen", False)
        self.input = SimpleNamespace(screenshot=self.screenshot, scroll=self.scroll)

    def accessibility_snapshot(self, hwnd):
        self.trace.append(("snapshot", hwnd))
        return {"url": self.page_url, "truncated": self.truncated,
                "nodes": [dict(node, focused=node["runtime_id"] == self.focused_id) for node in self.nodes]}

    def window_rect(self, hwnd):
        return 0, 0, 800, 600

    def screenshot(self, *, region):
        from PIL import Image
        self.trace.append(("screenshot", region))
        if self.change_during_screenshot:
            self.page_url = "https://example.test/different"
        return Image.new("RGB", (region[2], region[3]), "white")

    def scroll(self, ticks, *, x, y):
        self.trace.append(("scroll", ticks, x, y))

    def control_at(self, hwnd, x, y, runtime_id):
        if self.covered:
            return False
        node = next((item for item in self.nodes if item["runtime_id"] == runtime_id), None)
        if node is None:
            return False
        left, top, width, height = node["rect"]
        return left <= x < left + width and top <= y < top + height

    def focused_control(self, hwnd, runtime_id):
        return self.current == hwnd and self.focused_id == runtime_id

    def click(self, x, y):
        super().click(x, y)
        self.focused_id = next((node["runtime_id"] for node in reversed(self.nodes)
                               if node["type"] != "ControlType.Text"
                               and self.control_at(self.current, x, y, node["runtime_id"])), None)

    def address_bar(self, hwnd):
        return {"owned": self.current == hwnd, "address_focused": self.focused_id == "1.1",
                "address_value": self.address_value}

    def hotkey(self, *keys):
        super().hotkey(*keys)
        if keys == ("ctrl", "l"):
            self.focused_id = "1.1"
        if keys == ("ctrl", "v"):
            if self.focused_id == "1.1":
                self.address_value = self.clipboard
            else:
                for node in self.nodes:
                    if node["runtime_id"] == self.focused_id:
                        node["value"] = self.clipboard
        if keys == ("enter",) and self.focused_id == "1.1":
            self.page_url, self.focused_id = self.address_value, "2.2"


@pytest.fixture(autouse=True)
def fake_ocr(monkeypatch):
    monkeypatch.setattr("app.browser.native_console.OcrReader.read_bytes", lambda self, data: "Visible screen text")


def test_generic_navigation_uses_owned_current_tab_and_preserves_provider_restrictions():
    async def scenario():
        backend = WebDesktop()
        t = transport(backend)
        hwnd = await owned(t)
        await t.navigate_web(hwnd, "https://www.youtube.com/")
        assert backend.page_url == "https://www.youtube.com/"
        assert backend.clipboard == "private previous clipboard"
        assert not any(row[:3] == ("keys", hwnd, ("ctrl", "t")) for row in backend.trace)
        with pytest.raises(ValueError, match="limited"):
            await t.navigate(hwnd, "https://www.youtube.com/")
        with pytest.raises(NativeTransportError, match="owned"):
            await t.navigate_web(7, "https://example.test")
        for url in ("javascript:alert(1)", "file:///secret", "https://user:password@example.test"):
            with pytest.raises(ValueError):
                await t.navigate_web(hwnd, url)
    asyncio.run(scenario())


def test_native_observation_masks_window_screenshot_and_keeps_ui_evidence_bounded(monkeypatch):
    async def scenario():
        seen = []
        def ocr(_reader, data):
            from PIL import Image
            with Image.open(BytesIO(data)) as image:
                seen.append(image.size)
                assert image.getpixel((30, 110)) == (0, 0, 0)
                assert image.getpixel((30, 170)) == (0, 0, 0)
                assert image.getpixel((200, 30)) == (0, 0, 0)
                assert image.getpixel((500, 300)) == (255, 255, 255)
            return "password is private " + "visible " * 1_000
        monkeypatch.setattr("app.browser.native_console.OcrReader.read_bytes", ocr)
        backend = WebDesktop()
        t = transport(backend)
        hwnd = await owned(t)
        result = await t.observe_web(hwnd)
        assert result["available"] and result["backend"] == "native"
        assert result["trust"] == "untrusted_observation_data"
        assert result["ocr_status"] == "captured" and len(result["ocr_text"]) <= 5_000
        assert result["visible_text"] == "Funny cats"
        assert "private" not in str(result) and "typed draft" not in str(result)
        assert {row["runtime_id"] for row in result["elements"]} == {"4.4", "5.5"}
        assert result["elements"][0]["parent"] == 2
        assert seen == [(800, 600)]
        assert ("screenshot", (0, 0, 800, 600)) in backend.trace
        assert not any(row[0] == "keys" for row in backend.trace)
    asyncio.run(scenario())


def test_native_observation_preserves_uia_when_ocr_unavailable(monkeypatch):
    async def scenario():
        def unavailable(*_):
            raise OcrUnavailable("Install local language data")
        monkeypatch.setattr("app.browser.native_console.OcrReader.read_bytes", unavailable)
        t = transport(WebDesktop())
        result = await t.observe_web(await owned(t))
        assert result["available"] and result["visible_text"] == "Funny cats"
        assert result["ocr_status"] == "unavailable" and result["ocr_text"] == ""
    asyncio.run(scenario())


def test_native_observation_refuses_incomplete_trees_or_page_changes():
    async def scenario():
        backend = WebDesktop()
        t = transport(backend)
        hwnd = await owned(t)
        backend.truncated = True
        with pytest.raises(NativeTransportError, match="incomplete"):
            await t.observe_web(hwnd)
        assert not any(row[0] == "screenshot" for row in backend.trace)
        backend.truncated = False
        backend.change_during_screenshot = True
        assert not (await t.observe_web(hwnd))["available"]
        with pytest.raises(NativeTransportError, match="Observe"):
            await t.web_action(hwnd, "click", target="4.4")
    asyncio.run(scenario())


def test_generic_click_and_type_require_fresh_observed_targets_and_restore_clipboard():
    async def scenario():
        backend = WebDesktop()
        t = transport(backend)
        hwnd = await owned(t)
        with pytest.raises(NativeTransportError, match="Observe"):
            await t.web_action(hwnd, "click", target="4.4")
        await t.observe_web(hwnd)
        result = await t.web_action(hwnd, "click", target="4.4")
        assert result["performed"] and ("click", hwnd, 340, 120) in backend.trace
        with pytest.raises(NativeTransportError, match="Observe"):
            await t.web_action(hwnd, "type", target="5.5", text="cats")
        await t.observe_web(hwnd)
        assert (await t.web_action(hwnd, "type", target="5.5", text="cats"))["performed"]
        assert backend.nodes[5]["value"] == "cats"
        assert backend.clipboard == "private previous clipboard"
    asyncio.run(scenario())


@pytest.mark.parametrize("changed", ["label", "covered", "password", "disabled", "url", "chrome"])
def test_native_web_input_fails_closed_on_changed_or_unauthorized_target(changed):
    async def scenario():
        backend = WebDesktop()
        t = transport(backend)
        hwnd = await owned(t)
        await t.observe_web(hwnd)
        target = "5.5"
        if changed == "label": backend.nodes[5]["name"] = "Different control"
        if changed == "covered": backend.covered = True
        if changed == "password": backend.nodes[5]["password"] = True
        if changed == "disabled": backend.nodes[5]["enabled"] = False
        if changed == "url": backend.page_url = "https://example.test/other"
        if changed == "chrome": target = "1.1"
        with pytest.raises(NativeTransportError):
            await t.web_action(hwnd, "type", target=target, text="must not type")
        assert not any(row[0] == "keys" for row in backend.trace)
        assert backend.clipboard == "private previous clipboard"
    asyncio.run(scenario())


def test_native_type_stops_if_focus_changes_after_selecting_text():
    async def scenario():
        backend = WebDesktop()
        t = transport(backend)
        hwnd = await owned(t)
        await t.observe_web(hwnd)
        original = backend.hotkey
        def steal(*keys):
            original(*keys)
            if keys == ("ctrl", "a"):
                backend.focused_id = "1.1"
        backend.hotkey = steal
        with pytest.raises(NativeTransportError, match="lost focus"):
            await t.web_action(hwnd, "type", target="5.5", text="secret draft")
        assert not any(row[:3] == ("keys", hwnd, ("ctrl", "v")) for row in backend.trace)
        assert backend.clipboard == "private previous clipboard"
    asyncio.run(scenario())


def test_video_keys_are_allowed_only_on_focused_youtube_video_without_edit_focus():
    async def scenario():
        backend = WebDesktop()
        t = transport(backend)
        hwnd = await owned(t)
        await t.observe_web(hwnd)
        assert (await t.web_action(hwnd, "press", key="k"))["performed"]
        assert ("keys", hwnd, ("k",)) in backend.trace
        backend.page_url = "https://example.test/video"
        await t.observe_web(hwnd)
        with pytest.raises(NativeTransportError, match="YouTube video"):
            await t.web_action(hwnd, "press", key="k")
        backend.page_url = "https://www.youtube.com/watch?v=test"
        backend.focused_id = "5.5"
        await t.observe_web(hwnd)
        with pytest.raises(NativeTransportError, match="non-editable"):
            await t.web_action(hwnd, "press", key="space")
        for key in ("f12", "ctrl+shift+j", "win", "enter"):
            with pytest.raises(ValueError):
                await t.web_action(hwnd, "press", key=key)
    asyncio.run(scenario())


@pytest.mark.parametrize("action,keys", [("back", ("alt", "left")), ("forward", ("alt", "right")), ("refresh", ("ctrl", "r"))])
def test_navigation_keys_and_scroll_are_runtime_owned_and_bounded(action, keys):
    async def scenario():
        backend = WebDesktop()
        t = transport(backend)
        hwnd = await owned(t)
        await t.observe_web(hwnd)
        assert (await t.web_action(hwnd, action))["performed"]
        assert ("keys", hwnd, keys) in backend.trace
        await t.observe_web(hwnd)
        assert (await t.web_action(hwnd, "scroll", direction="down", amount=2))["performed"]
        assert ("scroll", -2, 400, 300) in backend.trace
        for amount in (0, 11, -1, True, 1.5):
            with pytest.raises(ValueError):
                await t.web_action(hwnd, "scroll", direction="down", amount=amount)
    asyncio.run(scenario())


class ProfileWebDesktop(WebDesktop):
    """Drive the real owned-window transport while simulating browser UI changes."""
    def spawn(self, argv):
        self.trace.append(("spawn", tuple(argv)))
        marker = re.search(r"<title>([^<]+)</title>", unquote(argv[-1])).group(1)
        self.titles[self.next_hwnd] = marker + " - Google Chrome"
        self.next_hwnd += 1
        self.page_url = argv[-1]

    def click(self, x, y):
        super().click(x, y)
        if self.focused_id == "4.4":
            self.nodes[4]["name"] = "Pause (k)" if self.nodes[4]["name"] == "Play" else "Play"
        elif self.focused_id == "8.8":
            self.page_url = "https://www.youtube.com/watch?v=selected-cat"
            self.nodes[4]["name"] = "Play"
            self.nodes = [node for node in self.nodes if node["runtime_id"] != "8.8"]

    def hotkey(self, *keys):
        super().hotkey(*keys)
        if keys == ("enter",) and "/results?" in self.page_url:
            self.nodes.append(dict(id=8, parent=2, runtime_id="8.8", name="Funny cats 1000 views 2 minutes",
                type="ControlType.Hyperlink", rect=[20, 250, 250, 40], enabled=True, offscreen=False))


def test_external_client_uses_real_native_transport_one_profile_window_and_current_tab(tmp_path):
    async def scenario():
        backend = ProfileWebDesktop()
        t = transport(backend)
        client = ExternalBrowserClient(tmp_path, discover=lambda **_: _inventory(tmp_path),
                                       transport_factory=lambda: t)
        profile = client.catalog()[0]
        await client.select_profile(profile["id"], profile["label"])
        assert "Opened" in await client.open()
        assert not (await client.observe())["available"]
        assert not any(row[0] == "screenshot" for row in backend.trace)
        await client.navigate("https://www.youtube.com/watch?v=existing")
        snapshot = await client.observe()
        assert snapshot["profile_id"] == profile["id"] and snapshot["window_id"] == 100
        assert (await client.interact("click", target="4.4"))["performed"]
        assert "is playing" in await client.play_youtube("current")
        await client.control_youtube("pause")
        assert backend.nodes[4]["name"] == "Play"
        await client.search_youtube("funny cats")
        assert backend.page_url.endswith("search_query=funny+cats")
        assert "Playing" in await client.play_youtube("video")
        assert backend.page_url == "https://www.youtube.com/watch?v=selected-cat"
        assert backend.nodes[4]["name"] == "Pause (k)"
        assert len([row for row in backend.trace if row[0] == "spawn"]) == 1
        assert len(client._windows) == 1 and client._windows[profile["id"]] == 100
        assert set(t._owned) == {100} and 7 in backend.titles
        assert not any(row[:3] == ("keys", 100, ("ctrl", "t")) for row in backend.trace)
    asyncio.run(scenario())


def test_external_client_does_not_report_playback_when_native_click_did_not_play(tmp_path):
    async def scenario():
        backend = ProfileWebDesktop()
        backend.click = lambda x, y: WebDesktop.click(backend, x, y)
        t = transport(backend)
        client = ExternalBrowserClient(tmp_path, discover=lambda **_: _inventory(tmp_path),
                                       transport_factory=lambda: t)
        profile = client.catalog()[0]
        await client.select_profile(profile["id"], profile["label"])
        await client.navigate("https://www.youtube.com/watch?v=existing")
        with pytest.raises(RuntimeError, match="playback could not be verified"):
            await client.play_youtube("current")
        assert backend.nodes[4]["name"] == "Play"
        assert len([row for row in backend.trace if row[0] == "click"]) == 1
    asyncio.run(scenario())
