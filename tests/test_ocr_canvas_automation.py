import asyncio
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from PIL import Image, ImageDraw

from app.agents.tools import RiskLevel, ToolRegistry, ToolSpec
from app.autonomy.mission import Mission
from app.browser.native_console import NativeConsoleTransport
from app.browser.native_console import NativeTransportError
from app.browser.external_client import ExternalBrowserClient
from app.computer.ocr import OcrReader
from app.safety.permissions import Permission
from app.voice.conversation import BrowserVoiceAssistant


def test_ocr_reader_read_elements_parses_tsv():
    reader = OcrReader()
    tsv_output = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t20\t30\t50\t15\t85.0\tCreate\n"
        "5\t1\t1\t1\t1\t2\t75\t30\t10\t15\t80.0\ta\n"
        "5\t1\t1\t1\t1\t3\t90\t30\t60\t15\t90.0\tdesign\n"
        "5\t1\t1\t1\t2\t1\t200\t80\t100\t20\t92.0\tPresentations\n"
    )
    fake_completed = MagicMock(returncode=0, stdout=tsv_output.encode("utf-8"))
    buf = BytesIO()
    Image.new("RGB", (300, 150), color="white").save(buf, format="PNG")
    with patch("subprocess.run", return_value=fake_completed), patch.object(OcrReader, "_tesseract_command", return_value="tesseract"):
        elements = reader.read_elements(buf.getvalue())

    assert len(elements) >= 2
    phrases = [el["text"] for el in elements]
    assert "Create a design" in phrases
    assert "Presentations" in phrases

    cad = next(el for el in elements if el["text"] == "Create a design")
    assert cad["left"] == 20
    assert cad["top"] == 30
    assert cad["width"] == 130  # 90 + 60 - 20
    assert cad["height"] == 15


def test_native_console_observes_ocr_elements_when_uia_empty():
    ident = {"pid": 1234, "path": "chrome.exe", "user": "user"}
    backend = MagicMock()
    backend.identity.return_value = ident
    backend.foreground.return_value = 101
    backend.windows.return_value = {101: "Canva: Visual Suite"}
    backend.window_rect.return_value = (100, 200, 800, 600)
    backend.accessibility_snapshot.return_value = {
        "url": "https://www.canva.com/",
        "nodes": [
            {"id": "doc1", "type": "ControlType.Document", "name": "Canva", "rect": [100, 200, 800, 600]},
        ],
    }
    img = Image.new("RGB", (800, 600), color="white")
    backend.input = SimpleNamespace(screenshot=lambda region: img, scroll=lambda *_: None)

    console = NativeConsoleTransport(backend=backend)
    console._owned[101] = ident

    fake_ocr_elements = [
        {"text": "Presentations", "left": 50, "top": 80, "width": 120, "height": 30, "conf": 88.0},
        {"text": "Templates", "left": 200, "top": 80, "width": 90, "height": 30, "conf": 85.0},
    ]
    with patch("app.browser.native_console.OcrReader.read_bytes", return_value="Presentations Templates"), \
         patch("app.browser.native_console.OcrReader.read_elements", return_value=fake_ocr_elements):
        obs = console._observe_web(101)

    assert obs["available"] is True
    assert obs["dom_status"] == "ocr_fallback"
    assert len(obs["elements"]) == 2
    pres = next(el for el in obs["elements"] if el["label"] == "Presentations")
    assert pres["runtime_id"] == "ocr.50.80"
    assert pres["source"] == "ocr"
    assert pres["rect"] == [150, 280, 120, 30]


def test_native_console_clicks_ocr_element_via_coordinates():
    ident = {"pid": 1234, "path": "chrome.exe", "user": "user"}
    backend = MagicMock()
    backend.identity.return_value = ident
    backend.foreground.return_value = 101
    backend.windows.return_value = {101: "Canva"}
    backend.window_rect.return_value = (100, 200, 800, 600)
    backend.point_in_window.return_value = True
    backend.accessibility_snapshot.return_value = {
        "url": "https://www.canva.com/",
        "nodes": [{"id": "doc1", "type": "ControlType.Document", "rect": [100, 200, 800, 600]}],
    }
    img = Image.new("RGB", (800, 600), color="white")
    backend.input = SimpleNamespace(screenshot=lambda region: img, scroll=lambda *_: None)

    console = NativeConsoleTransport(backend=backend)
    console._owned[101] = ident

    fake_ocr_elements = [
        {"text": "Presentations", "left": 50, "top": 80, "width": 100, "height": 40, "conf": 90.0},
    ]
    with patch("app.browser.native_console.OcrReader.read_bytes", return_value="Presentations"), \
         patch("app.browser.native_console.OcrReader.read_elements", return_value=fake_ocr_elements):
        console._observe_web(101)

    # Click the observed OCR element
    asyncio.run(console.web_action(101, "click", target="ocr.50.80"))
    # Screen coord center: 100 + 50 + 100/2 = 200; 200 + 80 + 40/2 = 300
    backend.click.assert_called_once_with(200, 300)


def test_native_console_presses_navigation_keys_on_target():
    ident = {"pid": 1234, "path": "chrome.exe", "user": "user"}
    backend = MagicMock()
    backend.identity.return_value = ident
    backend.foreground.return_value = 101
    backend.windows.return_value = {101: "Canva"}
    backend.window_rect.return_value = (100, 200, 800, 600)
    backend.accessibility_snapshot.return_value = {
        "url": "https://www.canva.com/",
        "nodes": [{"id": "doc1", "type": "ControlType.Document", "rect": [100, 200, 800, 600]}],
    }
    img = Image.new("RGB", (800, 600), color="white")
    backend.input = SimpleNamespace(screenshot=lambda region: img, scroll=lambda *_: None)

    console = NativeConsoleTransport(backend=backend)
    console._owned[101] = ident

    fake_ocr_elements = [
        {"text": "Presentations", "left": 50, "top": 80, "width": 100, "height": 40, "conf": 90.0},
    ]
    with patch("app.browser.native_console.OcrReader.read_bytes", return_value="Presentations"), \
         patch("app.browser.native_console.OcrReader.read_elements", return_value=fake_ocr_elements):
        console._observe_web(101)

    res = asyncio.run(console.web_action(101, "press", target="ocr.50.80", key="tab"))
    assert res["performed"] is True
    assert res["action"] == "press"
    backend.hotkey.assert_called_with("tab")


def test_conversation_simple_decision_press_navigation_keys():
    registry = ToolRegistry()
    registry.register(ToolSpec(
        "browser.external_action", "ext", "ext", frozenset({Permission.BROWSER_NAVIGATE.value}),
        RiskLevel.MEDIUM, lambda _: None, ("action", "target", "text", "key", "direction", "amount"),
    ))
    assistant = BrowserVoiceAssistant(
        MagicMock(), lambda _: None, lambda _: None, lambda: None, registry)
    assistant._browser_observation = {
        "backend": "native",
        "url": "https://www.canva.com/",
        "focused_target": "ocr.50.80",
        "elements": [{"runtime_id": "ocr.50.80", "label": "Presentations", "focused": True}],
    }

    dec = assistant._simple_browser_decision("Press tab")
    assert dec is not None
    assert dec["goal"] == "Press tab"
    assert dec["sequence"][0]["arguments"]["action"] == "press"
    assert dec["sequence"][0]["arguments"]["target"] == "ocr.50.80"
    assert dec["sequence"][0]["arguments"]["key"] == "tab"

    dec_enter = assistant._simple_browser_decision("Hit enter")
    assert dec_enter is not None
    assert dec_enter["goal"] == "Press enter"
    assert dec_enter["sequence"][0]["arguments"]["target"] == "ocr.50.80"
    assert dec_enter["sequence"][0]["arguments"]["key"] == "enter"

    # When no target is present in observation, navigation keys safely do not emit an untargeted plan
    assistant._browser_observation = {"backend": "native", "url": "https://www.canva.com/"}
    assert assistant._simple_browser_decision("Press tab") is None


def test_conversation_button_guidance_recommends_and_clicks_ocr_element():
    async def scenario():
        class FakeProvider:
            def use_conversation_session(self, s): pass
            async def complete(self, prompt, **kwargs):
                return '{"action":"recommend","target":"ocr.150.200","label":"Presentations","reason":"start designing slides"}'
            async def complete_primary(self, prompt):
                return await self.complete(prompt)

        registry = ToolRegistry()
        registry.register(ToolSpec(
            "browser.observe", "obs", "obs", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, (),
        ))
        registry.register(ToolSpec(
            "browser.external_action", "ext", "ext", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, ("action", "target", "text", "key", "direction", "amount"),
        ))

        missions, questions = [], []
        async def submit(m):
            missions.append(m)

        assistant = BrowserVoiceAssistant(
            FakeProvider(), submit, questions.append, lambda: None, registry)

        # Observation with OCR fallback elements
        assistant._browser_observation = {
            "backend": "native", "url": "https://www.canva.com/", "title": "Canva",
            "dom_status": "ocr_fallback",
            "elements": [
                {"runtime_id": "ocr.150.200", "label": "Presentations", "type": "ControlType.Button", "enabled": True, "source": "ocr"},
            ],
        }
        assistant._browser_site = "canva.com"

        resp = await assistant.handle("Which button should I click to make a presentation?", _observation_ready=True)
        assert resp["status"] == "waiting"
        assert "recommend clicking 'Presentations'" in questions[-1]
        assert assistant._pending_button_recommendation == {"target": "ocr.150.200", "label": "Presentations"}

        confirm = await assistant.handle("Yes, please click it")
        assert confirm["status"] == "accepted"
        assert len(missions) == 1
        seq = missions[0].checkpoint["function_sequence"]
        assert seq[0]["arguments"]["action"] == "click"
        assert seq[0]["arguments"]["target"] == "ocr.150.200"

    asyncio.run(scenario())


def test_conversation_screen_region_selection_intent():
    async def scenario():
        registry = ToolRegistry()
        registry.register(ToolSpec(
            "browser.external_action", "ext", "ext", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, ("action", "target", "text", "key", "direction", "amount"),
        ))
        missions = []
        async def submit(m):
            missions.append(m)

        assistant = BrowserVoiceAssistant(
            MagicMock(), submit, lambda _: None, lambda: None, registry)
        assistant.external_browser = SimpleNamespace(
            register_user_region=AsyncMock(return_value="region.selected"))
        assistant._browser_observation = {"backend": "native", "window_id": 101,
                                          "url": "https://www.canva.com/", "elements": []}

        fake_region = MagicMock()
        fake_region.bounds = (250, 350, 80, 40)

        with patch("app.perception.user_guidance.DesktopRegionSelector.select", return_value=fake_region):
            resp = await assistant.handle("Please select area on screen")
            assert resp["status"] == "accepted"
            assert len(missions) == 1
            seq = missions[0].checkpoint["function_sequence"]
            assert seq[0]["function"] == "browser.external_action"
            assert seq[0]["arguments"]["action"] == "click"
            assert seq[0]["arguments"]["target"] == "region.selected"
            assistant.external_browser.register_user_region.assert_awaited_once_with(
                fake_region.bounds, window_id=101, url="https://www.canva.com/")

    asyncio.run(scenario())


def region_transport():
    ident = {"pid": 1234, "path": "chrome.exe", "user": "user"}
    backend = MagicMock()
    backend.identity.return_value = ident
    backend.foreground.return_value = 101
    backend.windows.return_value = {101: "Test page"}
    backend.window_rect.return_value = (100, 200, 800, 600)
    backend.point_in_window.return_value = True
    backend.accessibility_snapshot.return_value = {
        "url": "https://example.com/", "nodes": [
            {"id": "doc1", "type": "ControlType.Document", "rect": [100, 200, 800, 600]}]}
    console = NativeConsoleTransport(backend=backend)
    console._owned[101] = ident
    console._web_observations[101] = {"url": "https://example.com/", "targets": {}}
    return console, backend


def test_selected_region_reaches_real_native_action(tmp_path):
    async def scenario():
        console, backend = region_transport()
        client = ExternalBrowserClient(tmp_path)
        client._selection = {"id": "test", "label": "Test"}
        client._windows["test"] = 101
        client._get_transport = lambda: console
        target = await client.register_user_region(
            (250, 350, 80, 40), window_id=101, url="https://example.com/")
        assert target.startswith("region.")
        backend.click.assert_not_called()
        result = await client.interact("click", target=target)
        assert result["performed"]
        backend.click.assert_called_once_with(290, 370)
        with pytest.raises(NativeTransportError):
            await client.interact("click", target=target)
        assert backend.click.call_count == 1

    asyncio.run(scenario())


@pytest.mark.parametrize("bounds", [(90, 200, 80, 40), (250, 350, -1, 40),
                                    (250, 350, float("nan"), 40), (890, 350, 80, 40)])
def test_selected_region_rejects_invalid_or_outside_bounds(bounds):
    console, backend = region_transport()
    with pytest.raises(NativeTransportError):
        asyncio.run(console.register_user_region(101, bounds, "https://example.com/"))
    backend.click.assert_not_called()


@pytest.mark.parametrize("change", ["page", "window"])
def test_selected_region_rejects_changes_before_click(change):
    async def scenario():
        console, backend = region_transport()
        target = await console.register_user_region(101, (250, 350, 80, 40), "https://example.com/")
        if change == "page":
            backend.accessibility_snapshot.return_value["url"] = "https://example.com/other"
        else:
            backend.window_rect.return_value = (200, 200, 800, 600)
        with pytest.raises(NativeTransportError):
            await console.web_action(101, "click", target=target)
        backend.click.assert_not_called()

    asyncio.run(scenario())


def test_region_selection_after_stop_does_not_register_or_submit():
    async def scenario():
        registry = ToolRegistry()
        registry.register(ToolSpec(
            "browser.external_action", "ext", "ext", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, ("action", "target", "text", "key", "direction", "amount"),
        ))
        missions = []
        assistant = BrowserVoiceAssistant(
            MagicMock(), missions.append, lambda _: None, lambda: None, registry)
        assistant.external_browser = SimpleNamespace(register_user_region=AsyncMock())
        assistant._browser_observation = {"backend": "native", "window_id": 101,
                                          "url": "https://example.com/", "elements": []}

        async def selection_finishes_after_reset(func):
            assistant.reset()
            return SimpleNamespace(bounds=(250, 350, 80, 40))

        with patch("app.voice.conversation.asyncio.to_thread", selection_finishes_after_reset):
            result = await assistant.handle("select area")
        assert result["status"] == "cancelled"
        assert not missions
        assistant.external_browser.register_user_region.assert_not_awaited()

    asyncio.run(scenario())


def test_voice_navigation_key_executes_through_native_transport(tmp_path):
    async def scenario():
        console, backend = region_transport()
        client = ExternalBrowserClient(tmp_path)
        client._selection = {"id": "test", "label": "Test"}
        client._windows["test"] = 101
        client._get_transport = lambda: console

        doc_node = {
            "id": "doc1", "type": "ControlType.Document", "rect": [100, 200, 800, 600],
            "runtime_id": "doc1", "focused": True, "name": "Test Document",
        }
        backend.accessibility_snapshot.return_value = {
            "url": "https://example.com/", "nodes": [doc_node]}
        backend.focused_control.return_value = True

        img = Image.new("RGB", (800, 600), color="white")
        backend.input = SimpleNamespace(screenshot=lambda region: img, scroll=lambda *_: None)

        with patch("app.browser.native_console.OcrReader.read_bytes", return_value=""), \
             patch("app.browser.native_console.OcrReader.read_elements", return_value=[]):
            obs = await client.observe()

        assert obs["focused_target"] == "doc1"

        registry = ToolRegistry()
        registry.register(ToolSpec(
            "browser.external_action", "ext", "ext", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM,
            lambda action, target=None, text=None, key=None, direction=None, amount=None:
                client.interact(action, target=target, text=text, key=key, direction=direction, amount=amount),
            ("action", "target", "text", "key", "direction", "amount"),
        ))

        missions = []
        assistant = BrowserVoiceAssistant(
            MagicMock(), missions.append, lambda _: None, lambda: None, registry)
        assistant.external_browser = client
        assistant._browser_observation = obs

        dec = assistant._simple_browser_decision("Press tab")
        assert dec is not None
        call = dec["sequence"][0]
        assert call["arguments"]["action"] == "press"
        assert call["arguments"]["target"] == "doc1"
        assert call["arguments"]["key"] == "tab"

        # Execute the call through the registered tool / client interact
        tool = registry.get("browser.external_action")
        res = await tool.handler(**call["arguments"])
        assert res["performed"] is True
        backend.hotkey.assert_called_with("tab")

        # Verify safety: untargeted non-video key raises ValueError
        with pytest.raises(ValueError, match="observed focused target is required"):
            await client.interact("press", target=None, key="tab")

    asyncio.run(scenario())


def test_canva_open_and_ask_plan_parsing():
    llm_response = """I will open Canva and ask what kind of presentation you want.
```json
{
  "action": "open_and_ask",
  "platform": "Canva",
  "goal": "Open Canva and design a presentation",
  "question": "What kind of presentation would you like to design?",
  "sequence": [
    {
      "function": "browser.navigate",
      "description": "Navigate to Canva visual suite",
      "arguments": {
        "url": "https://www.canva.com/"
      }
    }
  ]
}
```
Feel free to tell me the topic.
"""
    inventory = {"browser.navigate": {"arguments": ["url"]}}
    decision = BrowserVoiceAssistant.parse(llm_response, inventory)
    assert decision["action"] == "open_and_ask"
    assert decision["platform"] == "Canva"
    assert decision["question"] == "What kind of presentation would you like to design?"
    assert len(decision["sequence"]) == 1
    assert decision["sequence"][0] == {
        "function": "browser.navigate",
        "arguments": {"url": "https://www.canva.com/"},
    }
