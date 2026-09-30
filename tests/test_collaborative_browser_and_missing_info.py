import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.agents.runtime_tools import register_runtime_tools
from app.agents.tools import RiskLevel, ToolRegistry, ToolSpec
from app.autonomy.mission import Mission, MissionStatus
from app.safety.permissions import Permission
from app.voice.conversation import BrowserVoiceAssistant, VoiceConversationError


class FakeProvider:
    def __init__(self, responses=()):
        self.responses = iter(responses)
        self.prompts = []
        self.sessions = []

    def use_conversation_session(self, session):
        self.sessions.append(session)

    async def complete(self, prompt, **_kwargs):
        self.prompts.append(prompt)
        return next(self.responses)

    async def complete_primary(self, prompt):
        return await self.complete(prompt)


class FakePage:
    def __init__(self, url="https://example.com/"):
        self.url = url
        self.closed = False
        self.clicked = []

    def locator(self, selector):
        page = self
        class Locator:
            async def count(self):
                return 1
            async def is_visible(self):
                return True
            async def wait_for(self, **_):
                pass
            async def click(self):
                page.clicked.append(selector)
            @property
            def first(self):
                return self
        return Locator()

    def get_by_role(self, role, **kwargs):
        return self.locator(f"{role}:{kwargs.get('name')}")

    def get_by_text(self, text, **kwargs):
        return self.locator(f"text:{text}")


class FakeBrowserManager:
    def __init__(self, page=None):
        self._user_page = page or FakePage()
        self._context = MagicMock()

    def current_user_page(self):
        return self._user_page

    async def open_user_page(self):
        return self._user_page

    async def page_for(self, url, **_):
        return self._user_page

    def browser_client(self, **_):
        class FakeClient:
            policy = MagicMock(validate_url=lambda u: u)
            async def execute(self, action):
                pass
            async def observe(self):
                from app.browser.observer import PageObservation
                return PageObservation(
                    tab_id="tab-1", generation=1,
                    url="https://example.com/", title="Example Domain",
                    visible_text="Example text", elements=(),
                )
        return FakeClient()


class FakeExternalBrowser:
    def __init__(self, active=True):
        self.active = active
        self._selection = {"id": "chrome-1", "label": "Google Chrome — Work"}
        self.actions = []

    def catalog(self):
        return [self._selection]

    @property
    def selected_profile(self):
        return self._selection if self.active else None

    async def observe(self):
        return {
            "available": True, "backend": "native",
            "url": "https://python.org/", "title": "Welcome to Python.org",
            "elements": [
                {"runtime_id": "42.101", "label": "Downloads", "type": "ControlType.Button", "enabled": True},
                {"runtime_id": "42.102", "label": "Documentation", "type": "ControlType.Hyperlink", "enabled": True},
            ],
        }

    async def interact(self, action, target=None, text=None, key=None, direction=None, amount=3):
        self.actions.append({"action": action, "target": target, "text": text})
        return {"status": "ok"}


def test_missing_email_info_directly_queries_recipient_and_topic():
    registry = ToolRegistry()
    registry.register(ToolSpec(
        "browser.open", "open", "open", frozenset({Permission.BROWSER_NAVIGATE.value}),
        RiskLevel.MEDIUM, lambda _: None, (),
    ))
    assistant = BrowserVoiceAssistant(
        FakeProvider(), lambda _: None, lambda _: None, lambda: None, registry)
    assistant._gmail_turns = [{"speaker": "user", "text": "Send an email"}]
    missing = assistant._detect_missing_email_info()
    assert "recipient" in missing.lower()
    assert "email address" in missing.lower()

    assistant._gmail_turns = [{"speaker": "user", "text": "Send an email to alex@example.com"}]
    missing = assistant._detect_missing_email_info()
    assert "what would you like the email to say" in missing.lower()

    assistant._gmail_turns = [{"speaker": "user", "text": "Send an email to alex@example.com about Friday's release"}]
    assert assistant._detect_missing_email_info() is None


def test_gmail_json_parser_handles_fenced_markdown_with_commentary():
    response_with_text = """Here is the draft response:
```json
{
    "action": "ask",
    "question": "Who would you like to send this email to?"
}
```
Let me know if you need anything else!"""
    data = BrowserVoiceAssistant._parse_gmail_json(response_with_text)
    assert data["action"] == "ask"
    assert data["question"] == "Who would you like to send this email to?"

    decision = BrowserVoiceAssistant._parse_gmail_draft_decision(response_with_text)
    assert decision["action"] == "ask"
    assert decision["question"] == "Who would you like to send this email to?"


def test_browser_click_tool_registered_and_executed(tmp_path):
    registry = ToolRegistry()
    page = FakePage()
    browser_manager = FakeBrowserManager(page)
    register_runtime_tools(registry, browser_manager, tmp_path)

    spec = registry.get("browser.click")
    assert spec is not None
    assert spec.risk == RiskLevel.MEDIUM
    assert Permission.BROWSER_CLICK.value in spec.required_permissions

    result = asyncio.run(registry.invoke("browser.click", {"selector": "button.submit"}))
    assert "Clicked control" in result
    assert "button.submit" in page.clicked


def test_browser_click_tool_resolves_external_browser_target(tmp_path):
    registry = ToolRegistry()
    browser_manager = FakeBrowserManager()
    external = FakeExternalBrowser(active=True)
    register_runtime_tools(registry, browser_manager, tmp_path, external_browser=external)

    result = asyncio.run(registry.invoke("browser.click", {"selector": "Downloads"}))
    assert "Clicked observed external browser control: 42.101" in result
    assert external.actions[-1] == {"action": "click", "target": "42.101", "text": None}


def test_browser_crawl_tool_registered_and_invoked(tmp_path):
    registry = ToolRegistry()
    browser_manager = FakeBrowserManager()
    register_runtime_tools(registry, browser_manager, tmp_path)

    spec = registry.get("browser.crawl")
    assert spec is not None
    assert spec.risk == RiskLevel.MEDIUM
    assert Permission.BROWSER_NAVIGATE.value in spec.required_permissions
    assert Permission.BROWSER_READ.value in spec.required_permissions

    result = asyncio.run(registry.invoke("browser.crawl", {"url": "example.com"}))
    assert result["start_url"] == "https://example.com/"
    assert "pages_crawled" in result


def test_collaborative_button_guidance_recommends_and_clicks_on_affirmation():
    async def scenario():
        provider = FakeProvider([
            '{"action":"recommend","target":"42.101","label":"Downloads","reason":"access the installation packages"}',
        ])
        registry = ToolRegistry()
        registry.register(ToolSpec(
            "browser.observe", "obs", "obs", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, (),
        ))
        registry.register(ToolSpec(
            "browser.external_action", "ext", "ext", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, ("action", "target", "text", "key", "direction", "amount"),
        ))
        registry.register(ToolSpec(
            "browser.click", "click", "click", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, ("selector",),
        ))
        registry.register(ToolSpec(
            "browser.crawl", "crawl", "crawl", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, ("url",),
        ))

        missions, questions = [], []
        async def submit(m):
            missions.append(m)
        assistant = BrowserVoiceAssistant(
            provider, submit, questions.append, lambda: None, registry)

        assistant._browser_observation = {
            "backend": "native", "url": "https://python.org/", "title": "Python.org",
            "elements": [
                {"runtime_id": "42.101", "label": "Downloads", "type": "ControlType.Button", "enabled": True},
                {"runtime_id": "42.102", "label": "Docs", "type": "ControlType.Hyperlink", "enabled": True},
            ],
        }
        assistant._browser_site = "python.org"

        # User asks which button to click
        resp = await assistant.handle("Which button should I click to download Python?", _observation_ready=True)
        assert resp["status"] == "waiting"
        assert "recommend clicking 'Downloads'" in questions[-1]
        assert assistant._pending_button_recommendation == {"target": "42.101", "label": "Downloads"}

        # User responds with affirmation
        confirm_resp = await assistant.handle("Yes, please click it")
        assert confirm_resp["status"] == "accepted"
        assert len(missions) == 1
        seq = missions[0].checkpoint["function_sequence"]
        assert seq[0]["function"] == "browser.external_action"
        assert seq[0]["arguments"]["action"] == "click"
        assert seq[0]["arguments"]["target"] == "42.101"

    asyncio.run(scenario())


def test_missing_crawl_url_directly_asks_user_for_url():
    async def scenario():
        registry = ToolRegistry()
        registry.register(ToolSpec(
            "browser.crawl", "crawl", "crawl", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, ("url",),
        ))
        questions = []
        async def submit(m):
            pass
        assistant = BrowserVoiceAssistant(
            FakeProvider(), submit, questions.append, lambda: None, registry)

        resp = await assistant.handle("Please crawl this website")
        assert resp["status"] == "waiting"
        assert "Which website would you like me to crawl? Please provide the URL." in questions[-1]

    asyncio.run(scenario())


def test_missing_search_query_directly_asks_user_for_query():
    async def scenario():
        registry = ToolRegistry()
        registry.register(ToolSpec(
            "youtube.search", "search", "search", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, ("query",),
        ))
        questions = []
        async def submit(m):
            pass
        assistant = BrowserVoiceAssistant(
            FakeProvider(), submit, questions.append, lambda: None, registry)

        resp = await assistant.handle("Search for")
        assert resp["status"] == "waiting"
        assert "What would you like me to search for?" in questions[-1]

    asyncio.run(scenario())


def test_direct_click_command_matches_observed_element():
    async def scenario():
        registry = ToolRegistry()
        registry.register(ToolSpec(
            "browser.observe", "obs", "obs", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, (),
        ))
        registry.register(ToolSpec(
            "browser.external_action", "ext", "ext", frozenset({Permission.BROWSER_NAVIGATE.value}),
            RiskLevel.MEDIUM, lambda _: None, ("action", "target", "text", "key", "direction", "amount"),
        ))
        missions = []
        async def submit(m):
            missions.append(m)
        assistant = BrowserVoiceAssistant(
            FakeProvider(), submit, lambda _: None, lambda: None, registry)

        assistant._browser_observation = {
            "backend": "native", "url": "https://example.com/", "title": "Example",
            "elements": [
                {"runtime_id": "99.123", "label": "Login", "type": "ControlType.Button", "enabled": True},
            ],
        }
        assistant._browser_site = "example.com"

        resp = await assistant.handle("Click Login", _observation_ready=True)
        assert resp["status"] == "accepted"
        assert len(missions) == 1
        seq = missions[0].checkpoint["function_sequence"]
        assert seq[0]["function"] == "browser.external_action"
        assert seq[0]["arguments"]["target"] == "99.123"

    asyncio.run(scenario())
