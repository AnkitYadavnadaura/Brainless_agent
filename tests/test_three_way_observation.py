import asyncio
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from PIL import Image

from app.agents.tools import RiskLevel, ToolRegistry, ToolSpec
from app.browser.external_client import ExternalBrowserClient
from app.browser.native_console import NativeConsoleTransport
from app.browser.visual_cache import VisualElementCache, analyze_screenshot_with_llm
from app.computer.ocr import OcrReader
from app.safety.permissions import Permission
from app.voice.conversation import BrowserVoiceAssistant


def test_visual_element_cache_put_get_and_find(tmp_path):
    cache_file = tmp_path / "test_cache.json"
    cache = VisualElementCache(cache_file=cache_file)
    url = "https://example.com/editor"
    bounds = (0, 0, 1024, 768)
    elements = [
        {"label": "Download", "type": "ControlType.Button", "rect": [800, 20, 100, 40], "runtime_id": "visual.800.20"},
        {"label": "Share", "type": "ControlType.Button", "rect": [910, 20, 80, 40], "runtime_id": "visual.910.20"},
    ]

    cache.put(url, bounds, elements, screenshot_hash="abc123hash")
    retrieved = cache.get(url, bounds)
    assert retrieved is not None
    assert len(retrieved) == 2
    assert retrieved[0]["label"] == "Download"
    assert retrieved[0]["runtime_id"] == "visual.800.20"

    found = cache.find_by_label(url, "Share")
    assert found is not None
    assert found["runtime_id"] == "visual.910.20"

    assert cache.find_by_label(url, "Nonexistent") is None

    # Test disk persistence
    cache2 = VisualElementCache(cache_file=cache_file)
    assert len(cache2.get(url, bounds)) == 2

    # Invalidate
    cache.invalidate(url)
    assert cache.get(url, bounds) is None


def test_analyze_screenshot_with_llm_and_caching(tmp_path):
    async def scenario():
        cache_file = tmp_path / "test_cache.json"
        cache = VisualElementCache(cache_file=cache_file)
        url = "https://www.canva.com/design"
        bounds = (100, 200, 800, 600)

        img = Image.new("RGB", (800, 600), "white")
        buf = BytesIO()
        img.save(buf, format="PNG")

        fake_provider = MagicMock()
        fake_provider.complete = AsyncMock(return_value="""
```json
[
  {"label": "Presentations", "type": "button", "rect": [50, 80, 120, 35], "confidence": 0.95, "purpose": "Open presentation templates"},
  {"label": "Templates", "type": "button", "rect": [200, 80, 100, 35], "confidence": 0.90, "purpose": "Browse templates"}
]
```
""")

        analyzed = await analyze_screenshot_with_llm(
            fake_provider, buf.getvalue(), url, window_bounds=bounds, cache=cache
        )
        assert len(analyzed) == 2
        pres = analyzed[0]
        assert pres["label"] == "Presentations"
        assert pres["runtime_id"] == "visual.50.80"
        # Window bounds applied: 100 + 50 = 150, 200 + 80 = 280
        assert pres["rect"] == [150, 280, 120, 35]

        # Verify saved in cache
        cached = cache.get(url, bounds)
        assert cached is not None
        assert len(cached) == 2

    asyncio.run(scenario())


def test_ocr_reader_read_elements_partitioned():
    reader = OcrReader()
    img = Image.new("RGB", (800, 600), "white")
    buf = BytesIO()
    img.save(buf, format="PNG")

    tile_results = [
        [{"text": "File", "left": 10, "top": 10, "width": 40, "height": 20, "conf": 90.0}],
        [{"text": "Help", "left": 20, "top": 10, "width": 40, "height": 20, "conf": 88.0}],
        [{"text": "Canvas Slide", "left": 50, "top": 50, "width": 120, "height": 30, "conf": 92.0}],
        [{"text": "Zoom", "left": 20, "top": 50, "width": 50, "height": 25, "conf": 85.0}],
        [],  # full scan
    ]

    with patch.object(OcrReader, "read_elements", side_effect=tile_results):
        partitioned = reader.read_elements_partitioned(buf.getvalue(), grid=(2, 2))

    assert len(partitioned) == 4
    texts = [item["text"] for item in partitioned]
    assert "File" in texts
    assert "Help" in texts
    assert "Canvas Slide" in texts
    assert "Zoom" in texts

    # Help should have horizontal offset from tile column 1
    help_elem = next(item for item in partitioned if item["text"] == "Help")
    assert help_elem["left"] > 200


def test_native_console_extract_console_dom():
    async def scenario():
        backend = MagicMock()
        console = NativeConsoleTransport(backend=backend)
        fake_dom = {
            "url": "https://example.com/",
            "title": "Example Page",
            "elements": [
                {"tag": "button", "role": "button", "text": "Submit", "rect": [10, 20, 80, 30], "selector": "#submit-btn"},
            ],
        }
        console.evaluate = AsyncMock(return_value=fake_dom)

        result = await console.extract_console_dom(101)
        assert result is not None
        assert result["url"] == "https://example.com/"
        assert len(result["elements"]) == 1
        assert result["elements"][0]["text"] == "Submit"

    asyncio.run(scenario())


def test_external_client_extract_dom_falls_back_to_accessibility(tmp_path):
    async def scenario():
        console = MagicMock()
        console.window_alive = AsyncMock(return_value=True)
        console.extract_console_dom = AsyncMock(return_value=None)
        console.observe_web = AsyncMock(return_value={
            "url": "https://example.com/",
            "title": "Example",
            "elements": [
                {"label": "Login", "type": "ControlType.Button", "rect": [100, 200, 80, 30], "runtime_id": "1.2"},
            ],
        })

        client = ExternalBrowserClient(tmp_path)
        client._selection = {"id": "test", "label": "Test Profile"}
        client._windows["test"] = 101
        client._get_transport = lambda: console

        dom = await client.extract_dom()
        assert dom["available"] is True
        assert dom["source"] == "accessibility"
        assert len(dom["elements"]) == 1
        assert dom["elements"][0]["text"] == "Login"
        assert dom["elements"][0]["selector"] == "1.2"

    asyncio.run(scenario())


def test_conversation_button_guidance_connects_console_dom_and_visual_cache(tmp_path):
    async def scenario():
        cache_file = tmp_path / "test_cache.json"
        cache = VisualElementCache(cache_file=cache_file)
        url = "https://example.com/dashboard"
        cache.put(url, (0, 0, 800, 600), [
            {"label": "Export Data", "type": "ControlType.Button", "rect": [500, 50, 100, 35], "runtime_id": "visual.500.50"}
        ])

        client = MagicMock()
        client.extract_dom = AsyncMock(return_value={
            "available": True, "source": "console",
            "elements": [
                {"tag": "button", "role": "button", "text": "Import Project", "rect": [620, 50, 100, 35], "selector": "#import"}
            ]
        })

        registry = ToolRegistry()
        registry.register(ToolSpec(
            "browser.external_action", "ext", "ext", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, ("action", "target", "text", "key", "direction", "amount"),
        ))

        provider = MagicMock()
        provider.complete = AsyncMock(return_value='{"action":"recommend","label":"Export Data","target":"visual.500.50","reason":"export report"}')
        provider.complete_primary = provider.complete

        assistant = BrowserVoiceAssistant(
            provider, lambda _: None, lambda _: None, lambda: None, registry)
        assistant.external_browser = client
        assistant._browser_observation = {
            "backend": "native", "url": url, "title": "Dashboard",
            "elements": [{"label": "Settings", "type": "ControlType.Button", "runtime_id": "42.1"}]
        }

        with patch("app.browser.visual_cache.get_visual_cache", return_value=cache):
            res = await assistant._ask_browser_button_guidance("Which button should I click?")

        assert res["status"] == "waiting"
        assert "Export Data" in res["question"]
        assert assistant._pending_button_recommendation == {"label": "Export Data", "target": "visual.500.50"}

    asyncio.run(scenario())


def test_conversation_click_finds_target_in_visual_cache(tmp_path):
    cache_file = tmp_path / "test_cache.json"
    cache = VisualElementCache(cache_file=cache_file)
    url = "https://example.com/app"
    cache.put(url, (0, 0, 800, 600), [
        {"label": "Download Report", "type": "ControlType.Button", "rect": [700, 100, 90, 30], "runtime_id": "visual.700.100"}
    ])

    registry = ToolRegistry()
    registry.register(ToolSpec(
        "browser.external_action", "ext", "ext", frozenset({Permission.BROWSER_NAVIGATE.value}),
        RiskLevel.MEDIUM, lambda _: None, ("action", "target", "text", "key", "direction", "amount"),
    ))

    assistant = BrowserVoiceAssistant(
        MagicMock(), lambda _: None, lambda _: None, lambda: None, registry)
    assistant._browser_observation = {
        "backend": "native", "url": url,
        "elements": [{"label": "Help", "type": "ControlType.Button", "runtime_id": "42.10"}],
    }

    with patch("app.browser.visual_cache.get_visual_cache", return_value=cache):
        dec = assistant._simple_browser_decision("Click Download Report")

    assert dec is not None
    assert dec["goal"] == "Click Download Report"
    assert dec["sequence"][0]["arguments"]["action"] == "click"
    assert dec["sequence"][0]["arguments"]["target"] == "visual.700.100"
