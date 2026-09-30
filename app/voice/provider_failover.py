"""Sequential failover across configured browser-based reasoning providers."""
from __future__ import annotations

import logging
from collections.abc import Sequence

from app.providers.base_provider import ChatbotProvider
from app.voice.conversation import VoiceConversationError


logger = logging.getLogger(__name__)


class BrowserProviderFailover:
    """Use configured browser LLMs in order, advancing after provider failures."""

    def __init__(self, providers: Sequence[ChatbotProvider]) -> None:
        if not providers:
            raise ValueError("At least one browser LLM provider must be configured")
        self._providers = tuple(providers)
        self._active_index = 0
        self._session_key: str | None = None
        self._prompt: str | None = None

    def use_conversation_session(self, key: str) -> None:
        self._session_key = key

    def prepare_conversation(self, prompt: str) -> None:
        self._prompt = prompt

    async def complete(self, prompt: str, *, exclude_active: bool = False) -> str:
        attempts = len(self._providers)
        if exclude_active and attempts > 1:
            start = (self._active_index + 1) % attempts
        else:
            start = self._active_index

        failures: list[str] = []
        for offset in range(attempts):
            index = (start + offset) % attempts
            provider = self._providers[index]
            try:
                if self._session_key:
                    provider.use_conversation_session(
                        f"{self._session_key}:{provider.name}")
                provider.prepare_conversation(prompt)
                await provider.open()
                await provider.verify_page()
                await provider.start_conversation()
                await provider.send_prompt(prompt)
                await provider.wait_for_response(180)
                response = await provider.extract_response()
                if not response.strip():
                    raise RuntimeError("Provider returned an empty response")
                self._active_index = index
                return response
            except Exception as error:
                failures.append(f"{provider.name}: {type(error).__name__}")
                logger.warning("Voice LLM provider %s failed (%s); trying next configured provider",
                               provider.name, type(error).__name__)

        raise VoiceConversationError(
            "All configured browser LLM providers failed: " + "; ".join(failures))

    async def complete_primary(self, prompt: str) -> str:
        """Use the active browser LLM once for a focused voice workflow turn."""
        provider = self._providers[self._active_index]
        if self._session_key:
            provider.use_conversation_session(
                f"{self._session_key}:{provider.name}")
        provider.prepare_conversation(prompt)
        await provider.open()
        await provider.verify_page()
        await provider.start_conversation()
        await provider.send_prompt(prompt)
        await provider.wait_for_response(180)
        response = await provider.extract_response()
        if not response.strip():
            raise VoiceConversationError(
                f"{provider.name} returned an empty response")
        return response
