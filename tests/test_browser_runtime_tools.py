from unittest.mock import AsyncMock

import pytest

from app.agents.manager import AgentManager
from app.agents.runtime_tools import register_runtime_tools
from app.agents.tools import RiskLevel, ToolRegistry
from app.browser.browser_manager import BrowserManager
from app.config.settings import BrowserSettings
from app.safety.permissions import ApprovalMode, ApprovalRequired, Permission, PermissionPolicy


class FakePage:
    def __init__(self, url="about:blank"):
        self.url = url
        self.closed = False
        self.navigations = []
        self.foreground_count = 0

    def is_closed(self):
        return self.closed

    async def goto(self, url, **_):
        self.navigations.append(url)
        self.url = url

    async def bring_to_front(self):
        self.foreground_count += 1


class FakeContext:
    def __init__(self, *pages):
        self.pages = list(pages)

    async def new_page(self):
        page = FakePage()
        self.pages.append(page)
        return page


def runtime(tmp_path, *pages):
    browser = BrowserManager(BrowserSettings(), tmp_path)

    async def start_browser():
        if browser._context is None:
            browser._context = FakeContext(*pages)

    browser.start = AsyncMock(side_effect=start_browser)
    registry = ToolRegistry()
    register_runtime_tools(registry, browser, tmp_path)
    return browser, registry


@pytest.mark.asyncio
async def test_open_browser_lazily_foregrounds_and_reuses_an_owned_blank_tab(tmp_path):
    reasoning = FakePage("https://chatgpt.com/c/reasoning")
    browser, registry = runtime(tmp_path, reasoning)
    browser._conversation_pages["reasoning"] = reasoning
    browser._user_page = reasoning

    assert await registry.invoke("browser.open", {}) == "about:blank"
    browsing = browser._user_page
    assert browsing is not reasoning
    assert browsing.foreground_count == 1
    assert await registry.invoke("browser.open", {}) == "about:blank"
    assert browser._user_page is browsing
    assert browsing.foreground_count == 2
    assert len(browser._context.pages) == 2
    assert not reasoning.navigations

    assert await registry.invoke("browser.navigate", {"url": "gmail.com"}) == "https://gmail.com"
    assert browser._user_page is browsing
    assert browsing.navigations == ["https://gmail.com"]


@pytest.mark.asyncio
async def test_navigate_without_prior_start_normalizes_url_and_navigates_once(tmp_path):
    browser, registry = runtime(tmp_path)

    result = await registry.invoke("browser.navigate", {"url": "[Example](https://example.com/)"})

    assert result == "https://example.com/"
    browser.start.assert_awaited_once()
    assert browser._user_page.navigations == ["https://example.com/"]


@pytest.mark.asyncio
async def test_navigation_to_home_visits_home_and_never_reuses_reasoning_tab(tmp_path):
    reasoning = FakePage("https://chatgpt.com/c/reasoning")
    browser, registry = runtime(tmp_path, reasoning)
    browser._conversation_pages["reasoning"] = reasoning

    await registry.invoke("browser.navigate", {"url": "https://chatgpt.com/"})

    assert browser._user_page is not reasoning
    assert reasoning.url == "https://chatgpt.com/c/reasoning"
    assert not reasoning.navigations
    browser._user_page.url = "https://chatgpt.com/c/user-chat"
    await registry.invoke("browser.navigate", {"url": "https://chatgpt.com/"})
    assert browser._user_page.navigations == ["https://chatgpt.com/", "https://chatgpt.com/"]


@pytest.mark.asyncio
async def test_open_browser_replaces_closed_user_tab(tmp_path):
    browser, registry = runtime(tmp_path)
    await registry.invoke("browser.open", {})
    original = browser._user_page
    original.closed = True

    assert await registry.invoke("browser.open", {}) == "about:blank"
    assert browser._user_page is not original


@pytest.mark.asyncio
async def test_open_requires_browser_permission_before_starting_browser(tmp_path):
    browser, registry = runtime(tmp_path)
    spec = registry.get("browser.open")
    assert spec.input_schema == ()
    assert spec.risk == RiskLevel.MEDIUM
    assert spec.required_permissions == {Permission.BROWSER_NAVIGATE.value}
    policy = PermissionPolicy({Permission.BROWSER_NAVIGATE.value: ApprovalMode.REQUIRE_APPROVAL})
    manager = AgentManager(registry, policy=policy)
    root = manager.create_root("Root", "operator", "Browse", {Permission.BROWSER_NAVIGATE.value})
    agent = manager.create_agent(
        root.agent_id, "Browser", "browser", "Open browser",
        permissions={Permission.BROWSER_NAVIGATE.value}, tools={"browser.open"})

    async def execute(current_agent, supervisor):
        return await supervisor.execute_tool(current_agent.agent_id, "browser.open", {})

    with pytest.raises(ApprovalRequired):
        await manager.start_agent(root.agent_id, agent.agent_id, execute)
    browser.start.assert_not_awaited()


@pytest.mark.asyncio
async def test_youtube_search_opens_encoded_results_without_playback(tmp_path):
    browser, registry = runtime(tmp_path)

    result = await registry.invoke("youtube.search", {"query": "  cats & dogs  "})

    assert result == "https://www.youtube.com/results?search_query=cats+%26+dogs"
    assert browser._user_page.navigations == [result]
    assert registry.get("youtube.search").required_permissions == {
        Permission.BROWSER_READ.value, Permission.BROWSER_NAVIGATE.value}
    with pytest.raises(ValueError, match="search text"):
        await registry.invoke("youtube.search", {"query": "  "})


@pytest.mark.asyncio
async def test_invalid_navigation_url_never_starts_browser(tmp_path):
    browser, registry = runtime(tmp_path)

    with pytest.raises(ValueError, match="HTTP"):
        await registry.invoke("browser.navigate", {"url": "file:///private.txt"})

    browser.start.assert_not_awaited()


@pytest.mark.asyncio
async def test_navigation_and_search_keep_same_user_tab_identity(tmp_path):
    browser, registry = runtime(tmp_path)
    assert browser.current_user_page() is None
    browser.start.assert_not_awaited()
    await registry.invoke("browser.open", {})
    page = browser.current_user_page()
    tab_id = browser.tab_id_for(page)

    await registry.invoke("browser.navigate", {"url": "https://www.youtube.com/"})
    await registry.invoke("youtube.search", {"query": "nature"})
    await registry.invoke("browser.navigate", {"url": "https://mail.google.com/"})

    assert browser.current_user_page() is page
    assert browser.tab_id_for(page) == tab_id
    assert len(browser._context.pages) == 1
    assert page.navigations == [
        "https://www.youtube.com/", "https://www.youtube.com/results?search_query=nature",
        "https://mail.google.com/",
    ]


@pytest.mark.asyncio
async def test_current_page_observation_excludes_reasoning_and_closed_tabs(tmp_path):
    browser, registry = runtime(tmp_path)
    await registry.invoke("browser.open", {})
    page = browser.current_user_page()
    original_id = browser.tab_id_for(page)
    browser._conversation_pages["provider"] = page
    assert browser.current_user_page() is None
    with pytest.raises(ValueError, match="user browser tab"):
        browser.tab_id_for(page)
    browser._conversation_pages.clear()
    page.closed = True
    assert browser.current_user_page() is None
    await registry.invoke("browser.open", {})
    assert browser.tab_id_for(browser.current_user_page()) != original_id


def test_browser_observation_requires_read_and_screenshot_permissions(tmp_path):
    _browser, registry = runtime(tmp_path)
    observation = registry.get("browser.observe")
    assert observation.required_permissions == {
        Permission.BROWSER_READ.value, Permission.SCREEN_READ.value}
    assert observation.input_schema == ()
    assert observation.risk == RiskLevel.LOW
