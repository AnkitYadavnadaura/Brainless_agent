import json
from unittest.mock import AsyncMock

import pytest

from app.browser.browser_manager import BrowserManager
from app.config.settings import BrowserSettings
from app.providers.base_provider import ChatbotProvider, ProviderSelectors


class FakePage:
    def __init__(self):
        self.url = "about:blank"
        self.front_count = 0
        self.closed = False

    async def goto(self, url, **_):
        self.url = url

    async def bring_to_front(self):
        self.front_count += 1

    def is_closed(self):
        return self.closed


class FakeContext:
    def __init__(self):
        self.created = []

    @property
    def pages(self):
        return self.created

    async def new_page(self):
        page = FakePage()
        self.created.append(page)
        return page


def manager(tmp_path):
    instance = BrowserManager(BrowserSettings(), tmp_path)
    instance._context = FakeContext()
    return instance


@pytest.mark.asyncio
async def test_provider_open_starts_browser_manager_on_first_use(tmp_path):
    browser = BrowserManager(BrowserSettings(), tmp_path)

    async def start_browser():
        browser._context = FakeContext()

    browser.start = AsyncMock(side_effect=start_browser)
    provider = ChatbotProvider(
        browser, "https://chatgpt.com/",
        ProviderSelectors(input=(), response=(), stop=()),
    )

    await provider.open()

    browser.start.assert_awaited_once()
    assert provider.page.url == "https://chatgpt.com/"


@pytest.mark.asyncio
async def test_each_prompt_gets_a_dedicated_tab_and_is_reused_in_process(tmp_path):
    browser = manager(tmp_path)

    first = await browser.conversation_page("chatgpt", "first prompt", "https://chatgpt.com/")
    first_again = await browser.conversation_page("chatgpt", "first prompt", "https://chatgpt.com/")
    second = await browser.conversation_page("chatgpt", "second prompt", "https://chatgpt.com/")
    gemini = await browser.conversation_page("gemini", "first prompt", "https://gemini.google.com/")

    assert first_again is first
    assert len({id(first), id(second), id(gemini)}) == 3
    assert len(browser._context.created) == 3


@pytest.mark.asyncio
async def test_saved_chat_url_is_restored_without_storing_prompt(tmp_path):
    original = manager(tmp_path)
    original.remember_conversation(
        "chatgpt", "private prompt text", "https://chatgpt.com/c/abc", "https://chatgpt.com/"
    )

    saved_text = (tmp_path / "data/conversation-urls.json").read_text(encoding="utf-8")
    assert "private prompt text" not in saved_text

    restarted = manager(tmp_path)
    page = await restarted.conversation_page("chatgpt", "private prompt text", "https://chatgpt.com/")
    assert page.url == "https://chatgpt.com/c/abc"


@pytest.mark.asyncio
async def test_off_origin_saved_url_is_ignored(tmp_path):
    browser = manager(tmp_path)
    key = browser._conversation_key("chatgpt", "prompt")
    browser._conversation_file.parent.mkdir(parents=True)
    browser._conversation_file.write_text(json.dumps({key: "https://example.com/stolen"}), encoding="utf-8")

    page = await browser.conversation_page("chatgpt", "prompt", "https://chatgpt.com/")
    assert page.url == "https://chatgpt.com/"


@pytest.mark.asyncio
async def test_project_reasoning_and_retries_use_one_tab(tmp_path):
    from app.providers.base_provider import ChatbotProvider, ProviderSelectors
    browser=manager(tmp_path)
    existing=await browser._context.new_page()
    existing.url='https://chatgpt.com/'
    provider=ChatbotProvider(browser,'https://chatgpt.com/',ProviderSelectors(input=(),response=(),stop=()))
    provider.name='chatgpt'
    provider.use_conversation_session('persistent-3d-project')
    for prompt in ('plan','checkpoint review','repair failed action','user update'):
        provider.prepare_conversation(prompt)
        await provider.open()
        assert provider.page is existing
        existing.url='https://chatgpt.com/c/one-project'
        provider.remember_conversation()
    assert len(browser._context.created)==1
    restarted=manager(tmp_path)
    restored=ChatbotProvider(restarted,'https://chatgpt.com/',ProviderSelectors(input=(),response=(),stop=()))
    restored.name='chatgpt'
    restored.use_conversation_session('persistent-3d-project')
    restored.prepare_conversation('resume')
    await restored.open()
    assert restored.page.url=='https://chatgpt.com/c/one-project'
