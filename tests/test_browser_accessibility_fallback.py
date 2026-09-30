"""UIA failure changes observation method while preserving target identity and focus rules."""
import asyncio
import json
import re
from unittest.mock import AsyncMock

import pytest

from app.browser.external_client import ExternalBrowserClient
from app.browser.native_console import NativeAccessibilityError, NativeTransportError, NativeConsoleIntervention
from tests.test_external_browser_client import client_fixture
from tests.test_external_gmail import _inventory
from tests.test_native_console import Desktop, owned, transport


@pytest.mark.asyncio
async def test_transient_accessibility_failure_retries_a_fresh_snapshot(tmp_path):
    client, backend = client_fixture(tmp_path)
    await client.select_profile('chrome-work', 'Google Chrome — Work')
    await client.open()
    backend.observe_web = AsyncMock(side_effect=[NativeAccessibilityError('stale'), {'available': True, 'url': 'https://example.com'}])
    backend.observe_web_dom = AsyncMock()
    result = await client.observe()
    assert result['available']
    assert backend.observe_web.await_count == 2
    backend.observe_web_dom.assert_not_awaited()
    assert result['diagnostics'][0]['error'] == 'stale'


@pytest.mark.asyncio
async def test_persistent_accessibility_failure_uses_dom_in_same_owned_window(tmp_path):
    client, backend = client_fixture(tmp_path)
    await client.select_profile('chrome-work', 'Google Chrome — Work')
    await client.open()
    backend.observe_web = AsyncMock(side_effect=NativeAccessibilityError('unavailable'))
    backend.observe_web_dom = AsyncMock(return_value={'available': True, 'url': 'https://example.com', 'elements': []})
    result = await client.observe()
    backend.observe_web_dom.assert_awaited_once_with(42, 'chromium')
    assert result['available'] and len(backend.launches) == 1
    assert result['diagnostics'][-1]['method'] == 'dom'


@pytest.mark.asyncio
async def test_focus_loss_is_not_an_accessibility_fallback_trigger(tmp_path):
    client, backend = client_fixture(tmp_path)
    await client.select_profile('chrome-work', 'Google Chrome — Work')
    await client.open()
    backend.observe_web = AsyncMock(side_effect=NativeTransportError('focus lost'))
    backend.observe_web_dom = AsyncMock()
    with pytest.raises(NativeTransportError, match='focus lost'):
        await client.observe()
    backend.observe_web_dom.assert_not_awaited()


@pytest.mark.asyncio
async def test_dom_observation_target_reaches_native_action_without_uia():
    backend = Desktop()
    client = transport(backend)
    hwnd = await owned(client)
    calls = []
    def evaluate(window, family, script, tab, timeout_seconds=None):
        calls.append(script)
        if 'const token =' in script:
            token = re.search(r'const token = "([a-f0-9]+)"', script).group(1)
            return {'available': True, 'url': 'https://example.com/', 'elements': [
                {'runtime_id': 'dom.'+token+'.0', 'label': 'Play', 'type': 'ControlType.Button'}]}
        assert '"action": "click"' in script
        return {'performed': True, 'action': 'click'}
    client._evaluate = evaluate
    result = await client.observe_web_dom(hwnd, 'chromium')
    target = result['elements'][0]['runtime_id']
    assert (await client.web_action(hwnd, 'click', target=target))['performed']
    assert len(calls) == 2
    assert hwnd not in client._web_observations
