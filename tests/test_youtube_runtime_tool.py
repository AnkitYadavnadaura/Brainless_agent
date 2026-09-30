import asyncio

import pytest

from app.agents.manager import AgentManager
from app.agents.runtime_tools import register_runtime_tools
from app.agents.tools import ToolRegistry
from app.safety.permissions import Permission
from app.autonomy.executor import ActionRuntime
from app.autonomy.mission import Mission, MissionStatus
from app.autonomy.models import ComputerState
from app.autonomy.orchestrator import AutonomousRuntime
from app.autonomy.production_mission import RuntimeMissionComposer
from app.autonomy.task_engine import AutonomousTaskEngine
from app.browser.browser_manager import BrowserManager
from app.config.settings import BrowserSettings


class FakeController:
    async def observe(self):
        return ComputerState(active_application="browser")

    async def execute(self, action_type, arguments):
        raise AssertionError(f"Unexpected controller action: {action_type}")


class FakeLocator:
    def __init__(self, page, selector):
        self.page, self.selector = page, selector

    @property
    def first(self):
        return self

    def nth(self, index):
        assert index == 0
        return self

    async def is_visible(self):
        return True

    async def count(self):
        if self.selector == "video":
            return 1
        if "ytp-large-play-button" in self.selector:
            return 1
        if self.page.result_href and self.selector.startswith("ytd-"):
            return 1
        return 0

    async def get_attribute(self, name):
        assert name == "href"
        return self.page.result_href

    async def click(self):
        if self.selector.startswith("ytd-"):
            video_id = self.page.result_href.split("v=", 1)[-1]
            self.page.url = f"https://www.youtube.com/watch?v={video_id}"
            self.page.clicked_result = True
        elif "ytp-large-play-button" in self.selector:
            self.page.playing = True
        else:
            raise AssertionError(f"Unexpected click target: {self.selector}")

    async def wait_for(self, state, timeout):
        assert state == ("attached" if self.selector == "video" else "visible")
        assert timeout == 15_000

    async def evaluate(self, _script):
        if "getBoundingClientRect" in _script:
            return True
        return self.page.playing


class FakeYouTubePage:
    def __init__(self, *, result_href):
        self.url = ""
        self.result_href = result_href
        self.clicked_result = False
        self.playing = False
        self.navigations = []
        self.foreground_count = 0

    def is_closed(self):
        return False

    async def goto(self, url, **_):
        self.navigations.append(url)
        self.url = url

    async def bring_to_front(self):
        self.foreground_count += 1

    def locator(self, selector):
        return FakeLocator(self, selector)

    async def wait_for_url(self, pattern, timeout):
        assert pattern == "**/watch**"
        assert timeout == 15_000
        assert "/watch?" in self.url

    async def wait_for_function(self, _script, timeout):
        assert timeout == 15_000
        assert self.playing

    async def title(self):
        return "Selected YouTube video"


class FakeControlLocator:
    def __init__(self, page, selector):
        self.page, self.selector = page, selector

    @property
    def first(self):
        return self

    async def count(self):
        if self.selector == "video":
            return 1
        if "ytp-ad-skip-button" in self.selector:
            return int(self.page.skippable_ad)
        if "ytp-next-button" in self.selector:
            return int(self.page.has_next)
        return 0

    async def is_visible(self):
        return self.page.skippable_ad if "ytp-ad-skip-button" in self.selector else self.page.has_next

    async def click(self):
        if "ytp-ad-skip-button" in self.selector:
            self.page.skippable_ad = False
        elif "ytp-next-button" in self.selector:
            self.page.url = "https://www.youtube.com/watch?v=nextvideo"
        else:
            raise AssertionError(f"Unexpected click target: {self.selector}")

    async def wait_for(self, state, timeout):
        assert state == "attached"
        assert timeout == 15_000

    async def evaluate(self, script, argument=None):
        if "element.play()" in script:
            self.page.playing = True
            return None
        if "element.pause()" in script:
            self.page.playing = False
            return None
        if "element.currentTime" in script:
            self.page.position = max(0, min(500, self.page.position + argument))
            return self.page.position
        raise AssertionError(f"Unexpected video evaluation: {script}")


class FakeControlPage:
    def __init__(self, *, skippable_ad=False, has_next=True):
        self.url = "https://www.youtube.com/watch?v=currentvideo"
        self.skippable_ad = skippable_ad
        self.has_next = has_next
        self.playing = True
        self.position = 100

    async def bring_to_front(self):
        pass

    def locator(self, selector):
        return FakeControlLocator(self, selector)

    async def wait_for_function(self, _script, *_args, **_kwargs):
        return None

    async def title(self):
        return "Next video"


class FakeControlBrowser:
    def __init__(self, page):
        self.page = page

    async def page_for(self, _url):
        return self.page

    def current_user_page(self):
        return self.page


class FakeGmailLocator:
    def __init__(self, page, selector):
        self.page, self.selector = page, selector

    @property
    def first(self):
        return self

    async def wait_for(self, state, timeout):
        assert state == "visible"
        assert timeout == 15_000

    async def fill(self, value):
        if "name=\"to\"" in self.selector:
            self.page.recipient = value
        elif "subjectbox" in self.selector:
            self.page.subject = value
        elif "Message Body" in self.selector:
            self.page.body = value

    async def press(self, key):
        assert key == "Enter"
        self.page.recipient_confirmed = True

    async def click(self):
        if "gh=\"cm\"" in self.selector:
            self.page.composing = True
        elif "aria-label^=\"Send\"" in self.selector:
            self.page.sent = True
        else:
            raise AssertionError(f"Unexpected Gmail click: {self.selector}")

    async def count(self):
        if "div[email=" in self.selector:
            return int(self.page.recipient_confirmed and self.page.recipient in self.selector)
        return 1


class FakeGmailPage:
    url = "https://mail.google.com/mail/u/0/#inbox"

    def __init__(self):
        self.recipient = None
        self.subject = None
        self.body = None
        self.recipient_confirmed = False
        self.composing = False
        self.sent = False

    def locator(self, selector):
        return FakeGmailLocator(self, selector)

    def get_by_text(self, text, exact=False):
        assert text == "Message sent"
        assert exact is False
        locator = FakeGmailLocator(self, "message-sent-confirmation")

        async def wait_for(state, timeout):
            assert state == "visible"
            assert timeout == 15_000
            assert self.sent

        locator.wait_for = wait_for
        return locator


class FakeGmailBrowser:
    def __init__(self, page):
        self.page = page

    async def page_for(self, _url):
        return self.page


class FakeBrowser:
    def __init__(self, page):
        self.page = page
        self.opened_urls = []

    async def page_for(self, url, **_):
        self.opened_urls.append(url)
        self.page.url = url
        return self.page

    def current_user_page(self):
        return self.page if self.page.url else None


def build_youtube_tool(tmp_path, browser):
    registry = ToolRegistry()
    register_runtime_tools(registry, browser, tmp_path)
    return registry


def test_youtube_tool_executes_requested_result_through_agent_permissions(tmp_path):
    async def scenario():
        page = FakeYouTubePage(result_href="/watch?v=requested123")
        browser = FakeBrowser(page)
        registry = build_youtube_tool(tmp_path, browser)
        manager = AgentManager(registry)
        root = manager.create_root(
            "Root", "operator", "Play requested YouTube video",
            {Permission.BROWSER_NAVIGATE.value, Permission.SCREEN_READ.value})
        agent = manager.create_agent(
            root.agent_id, "YouTube", "media", "Play the selected result",
            task="Play GTA 6 trailer",
            permissions={Permission.BROWSER_NAVIGATE.value, Permission.SCREEN_READ.value},
            tools={"youtube.play"},
        )

        async def execute(current_agent, supervisor):
            return await supervisor.execute_tool(
                current_agent.agent_id, "youtube.play", {"query": "GTA 6 trailer"})

        result = await manager.start_agent(root.agent_id, agent.agent_id, execute)

        assert browser.opened_urls == [
            "https://www.youtube.com/results?search_query=GTA+6+trailer",
        ]
        assert page.clicked_result and page.playing
        assert result == "Playing YouTube video: Selected YouTube video"
        assert agent.execution_history[-1].success

    asyncio.run(scenario())


def test_youtube_tool_plays_first_home_recommendation_when_requested(tmp_path):
    async def scenario():
        page = FakeYouTubePage(result_href="/watch?v=recommend123")
        browser = FakeBrowser(page)
        registry = build_youtube_tool(tmp_path, browser)
        result = await registry.invoke("youtube.play", {"query": "recommendation"})

        assert browser.opened_urls == ["https://www.youtube.com/"]
        assert page.clicked_result and page.playing
        assert result == "Playing YouTube video: Selected YouTube video"

    asyncio.run(scenario())


class FakeManagedContext:
    def __init__(self):
        self.pages = []

    async def new_page(self):
        page = FakeYouTubePage(result_href="/watch?v=visible-choice")
        page.url = "about:blank"
        self.pages.append(page)
        return page


@pytest.mark.asyncio
async def test_open_youtube_then_play_and_search_continue_in_one_tab(tmp_path):
    browser = BrowserManager(BrowserSettings(), tmp_path)
    browser._context = FakeManagedContext()
    registry = build_youtube_tool(tmp_path, browser)
    await registry.invoke("browser.open", {})
    await registry.invoke("browser.navigate", {"url": "https://www.youtube.com/"})
    page = browser.current_user_page()
    tab_id = browser.tab_id_for(page)

    result = await registry.invoke("youtube.play", {"query": "recommendation"})

    assert result.startswith("Playing YouTube video")
    assert page.clicked_result and page.playing
    assert page.navigations == ["https://www.youtube.com/"]
    assert browser.tab_id_for(browser.current_user_page()) == tab_id
    await registry.invoke("youtube.search", {"query": "nature"})
    assert page.url == "https://www.youtube.com/results?search_query=nature"
    assert len(browser._context.pages) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["recommendation", "a video", "play video", "resume"])
async def test_generic_play_resumes_current_video_without_replacing_it(tmp_path, query):
    browser = BrowserManager(BrowserSettings(), tmp_path)
    browser._context = FakeManagedContext()
    registry = build_youtube_tool(tmp_path, browser)
    await registry.invoke("browser.open", {})
    page = browser.current_user_page()
    page.url = "https://www.youtube.com/watch?v=already-selected"

    await registry.invoke("youtube.play", {"query": query})

    assert page.url == "https://www.youtube.com/watch?v=already-selected"
    assert page.playing
    assert not page.clicked_result
    assert not page.navigations
    assert len(browser._context.pages) == 1


@pytest.mark.asyncio
async def test_generic_play_uses_visible_result_from_current_search(tmp_path):
    browser = BrowserManager(BrowserSettings(), tmp_path)
    browser._context = FakeManagedContext()
    registry = build_youtube_tool(tmp_path, browser)
    await registry.invoke("browser.open", {})
    page = browser.current_user_page()
    page.url = "https://www.youtube.com/results?search_query=nature"

    await registry.invoke("youtube.play", {"query": "any video"})

    assert page.url == "https://www.youtube.com/watch?v=visible-choice"
    assert page.clicked_result
    assert not page.navigations
    assert len(browser._context.pages) == 1


@pytest.mark.asyncio
async def test_generic_play_skips_offscreen_recommendations(tmp_path):
    class ViewportLocator(FakeLocator):
        def __init__(self, page, selector, index=0):
            super().__init__(page, selector)
            self.index = index

        async def count(self):
            return 2 if self.selector.startswith("ytd-") else await super().count()

        def nth(self, index):
            return ViewportLocator(self.page, self.selector, index)

        async def evaluate(self, script):
            if "getBoundingClientRect" in script:
                return self.index == 1
            return await super().evaluate(script)

        async def get_attribute(self, name):
            return "/watch?v=visible-choice" if self.index == 1 else "/watch?v=offscreen"

    page = FakeYouTubePage(result_href="/watch?v=visible-choice")
    page.url = "https://www.youtube.com/"
    page.locator = lambda selector: ViewportLocator(page, selector)
    browser = FakeBrowser(page)
    registry = build_youtube_tool(tmp_path, browser)

    await registry.invoke("youtube.play", {"query": "recommendation"})

    assert page.url == "https://www.youtube.com/watch?v=visible-choice"
    assert not browser.opened_urls


def test_youtube_tool_does_not_play_homepage_video_when_query_has_no_result(tmp_path):
    async def scenario():
        page = FakeYouTubePage(result_href=None)
        browser = FakeBrowser(page)
        registry = build_youtube_tool(tmp_path, browser)

        try:
            await registry.invoke("youtube.play", {"query": "specific missing song"})
        except RuntimeError as error:
            assert "No matching YouTube video" in str(error)
        else:
            raise AssertionError("A missing search result must not be reported as playback")
        assert not page.clicked_result
        assert not page.playing

    asyncio.run(scenario())


def test_youtube_control_handles_playback_skip_seek_and_next_video(tmp_path):
    async def scenario():
        page = FakeControlPage(skippable_ad=True)
        registry = build_youtube_tool(tmp_path, FakeControlBrowser(page))

        assert await registry.invoke(
            "youtube.control", {"action": "pause", "seconds": 0}) == "YouTube video paused"
        assert not page.playing
        assert await registry.invoke(
            "youtube.control", {"action": "play", "seconds": 0}) == "YouTube video playing"
        assert page.playing
        assert await registry.invoke(
            "youtube.control", {"action": "skip_ad", "seconds": 0}) == "Skipped the YouTube ad"
        assert await registry.invoke(
            "youtube.control", {"action": "forward", "seconds": 15}) == (
                "Moved YouTube playback to 115 seconds")
        assert await registry.invoke(
            "youtube.control", {"action": "backward", "seconds": 30}) == (
                "Moved YouTube playback to 85 seconds")
        assert await registry.invoke(
            "youtube.control", {"action": "next_video", "seconds": 0}) == (
                "Started the next YouTube video: Next video")

    asyncio.run(scenario())


def test_youtube_control_rejects_seek_out_of_bounds_and_no_active_video(tmp_path):
    async def scenario():
        page = FakeControlPage()
        registry = build_youtube_tool(tmp_path, FakeControlBrowser(page))
        try:
            await registry.invoke("youtube.control", {"action": "forward", "seconds": 121})
        except ValueError as error:
            assert "between 1 and 120" in str(error)
        else:
            raise AssertionError("Out-of-range YouTube seek should be rejected")

        page.url = "https://www.youtube.com/"
        try:
            await registry.invoke("youtube.control", {"action": "pause", "seconds": 0})
        except RuntimeError as error:
            assert "No active YouTube video" in str(error)
        else:
            raise AssertionError("YouTube controls must require an active video")

    asyncio.run(scenario())


def test_gmail_send_email_composes_and_verifies_send_confirmation(tmp_path):
    async def scenario():
        page = FakeGmailPage()
        registry = build_youtube_tool(tmp_path, FakeGmailBrowser(page))
        tool = registry.get("gmail.send_email")

        assert tool.risk.value == "high"
        assert tool.destructive
        assert await registry.invoke("gmail.send_email", {
            "to": "person@example.com",
            "subject": "Project update",
            "body": "The project is ready for review.",
        }) == "Email sent to person@example.com"
        assert page.recipient_confirmed and page.sent
        assert page.subject == "Project update"
        assert page.body == "The project is ready for review."

    asyncio.run(scenario())


def test_gmail_send_email_rejects_invalid_recipient_before_opening_gmail(tmp_path):
    async def scenario():
        class Browser:
            async def page_for(self, _url):
                raise AssertionError("Gmail must not open for an invalid address")

        registry = build_youtube_tool(tmp_path, Browser())
        try:
            await registry.invoke("gmail.send_email", {
                "to": "not-an-email", "subject": "Hello", "body": "Message",
            })
        except ValueError as error:
            assert "valid email recipient" in str(error)
        else:
            raise AssertionError("Invalid Gmail recipient should be rejected")

    asyncio.run(scenario())


def test_youtube_voice_mission_executes_and_verifies_selected_playback(tmp_path):
    async def scenario():
        page = FakeYouTubePage(result_href="/watch?v=missionvideo123")
        browser = FakeBrowser(page)
        registry = build_youtube_tool(tmp_path, browser)
        manager = AgentManager(registry)
        root = manager.create_root(
            "Root", "operator", "Execute voice missions",
            {permission.value for permission in Permission})
        actions = ActionRuntime(manager, FakeController())
        autonomous = AutonomousRuntime(manager, actions)
        engine = AutonomousTaskEngine(autonomous, actions)
        composer = RuntimeMissionComposer(autonomous, engine, root.agent_id)
        mission = Mission(
            "Play GTA 6 trailer on YouTube",
            "voice",
            checkpoint={"function_sequence": [{
                "function": "youtube.play", "arguments": {"query": "GTA 6 trailer"},
            }]},
        )

        status = await composer(mission)

        assert status is MissionStatus.COMPLETED
        assert mission.checkpoint["verified"]
        assert page.clicked_result and page.playing
        assert any(record.task_id.startswith(mission.mission_id) and record.error is None
                   for record in actions.audit)

    asyncio.run(scenario())
