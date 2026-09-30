import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.runtime.agent_runtime import AgentRuntime, RECOVERY_CONTROL_ERRORS
from app.runtime.state_manager import RuntimeState
from app.tasks.task import Task


@pytest.fixture
def runtime():
    fallback = SimpleNamespace(extract_from_clipboard=AsyncMock(return_value="clipboard response"),
                               extract_from_ocr=Mock(return_value="OCR response"))
    return AgentRuntime(SimpleNamespace(start=AsyncMock()), Mock(), Mock(), Mock(),
                        max_retries=2, fallback_extractor=fallback)


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", RECOVERY_CONTROL_ERRORS)
async def test_response_control_signals_stop_without_reload_or_fallback(runtime, error_type):
    error = error_type("stop extraction")
    provider = SimpleNamespace(page=None, extract_response=AsyncMock(side_effect=error), recover=AsyncMock())
    with pytest.raises(error_type) as caught:
        await runtime._extract_response("chatgpt", provider, time.monotonic())
    assert caught.value is error
    provider.extract_response.assert_awaited_once()
    provider.recover.assert_not_awaited()
    runtime.fallback_extractor.extract_from_clipboard.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", RECOVERY_CONTROL_ERRORS)
async def test_reload_control_signals_stop_without_another_read(runtime, error_type):
    error = error_type("stop recovery")
    provider = SimpleNamespace(page=None, extract_response=AsyncMock(side_effect=RuntimeError("stale DOM")),
                               recover=AsyncMock(side_effect=error))
    with pytest.raises(error_type) as caught:
        await runtime._extract_response("chatgpt", provider, time.monotonic())
    assert caught.value is error
    provider.extract_response.assert_awaited_once()
    provider.recover.assert_awaited_once()
    runtime.fallback_extractor.extract_from_clipboard.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", RECOVERY_CONTROL_ERRORS)
async def test_clipboard_control_signals_propagate_without_ocr(runtime, error_type):
    error = error_type("stop fallback")
    provider = SimpleNamespace(page=None, extract_response=AsyncMock(side_effect=RuntimeError("DOM missing")),
                               recover=AsyncMock())
    runtime.fallback_extractor.extract_from_clipboard.side_effect = error
    runtime._capture = AsyncMock(return_value="screenshot.png")
    with pytest.raises(error_type) as caught:
        await runtime._extract_response("chatgpt", provider, time.monotonic())
    assert caught.value is error
    runtime._capture.assert_not_awaited()
    runtime.fallback_extractor.extract_from_ocr.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", RECOVERY_CONTROL_ERRORS)
async def test_optional_claude_provider_cannot_hide_control_signals(runtime, error_type):
    error = error_type("stop optional provider")
    runtime._run_provider = AsyncMock(side_effect=["first response", error])
    with pytest.raises(error_type) as caught:
        await runtime.run(Task("Research", providers=["chatgpt", "claude"]))
    assert caught.value is error
    assert runtime.state.state is RuntimeState.FAILED
