"""Browser voice follow-ups reflect executed missions, including delayed results."""
import asyncio
import json

import pytest

from app.agents.tools import RiskLevel, ToolRegistry, ToolSpec
from app.autonomy.mission import MissionStatus
from app.safety.permissions import Permission
from app.voice.conversation import BrowserVoiceAssistant


class Provider:
    def __init__(self, responses=()):
        self.responses = iter(responses)
        self.sessions = []
        self.prompts = []

    def use_conversation_session(self, session):
        self.sessions.append(session)

    async def complete(self, prompt, **_kwargs):
        self.prompts.append(prompt)
        return next(self.responses)


def assistant_fixture(*, responses=(), profiles=None, observe=False):
    registry = ToolRegistry()
    for function, arguments in (
            ("browser.open", ()), ("browser.navigate", ("url",)),
            ("youtube.search", ("query",)), ("youtube.play", ("query",))):
        registry.register(ToolSpec(
            function, function, function,
            frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.MEDIUM,
            lambda _: None, arguments))
    if observe:
        registry.register(ToolSpec(
            "browser.observe", "Observe browser", "Read current browser screen and DOM",
            frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.LOW,
            lambda _: None, ()))
    missions, questions = [], []

    async def submit(mission):
        missions.append(mission)

    provider = Provider(responses)
    assistant = BrowserVoiceAssistant(
        provider, submit, questions.append, lambda: None, registry, gmail_profiles=profiles)
    return assistant, missions, questions, provider


def test_browser_then_youtube_then_search_and_play_wait_for_completion():
    async def scenario():
        assistant, missions, questions, provider = assistant_fixture()
        response = await assistant.handle("Please open Chrome")
        assert response["status"] == "accepted"
        assert missions[-1].checkpoint["function_sequence"] == [
            {"function": "browser.open", "arguments": {}}]
        assert questions == []
        for state in (MissionStatus.RUNNING, MissionStatus.AWAITING_USER):
            missions[-1].status = state
            await assistant.mission_finished(missions[-1])
            assert questions == []
        missions[-1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[-1])
        assert questions[-1] == "What would you like to open in the browser?"

        await assistant.handle("YouTube")
        assert not assistant.awaiting_clarification
        assert missions[-1].checkpoint["function_sequence"] == [{
            "function": "browser.navigate", "arguments": {"url": "https://www.youtube.com/"}}]
        missions[-1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[-1])
        assert questions[-1] == "What would you like to do next on YouTube?"

        await assistant.handle("Search for Python tutorials")
        assert missions[-1].checkpoint["function_sequence"] == [{
            "function": "youtube.search", "arguments": {"query": "Python tutorials"}}]
        assert not assistant.awaiting_clarification
        missions[-1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[-1])
        await assistant.handle("Play beginner Python")
        assert missions[-1].checkpoint["function_sequence"] == [{
            "function": "youtube.play", "arguments": {"query": "beginner Python"}}]
        assert not provider.prompts
        assert len(provider.sessions) == 1

    asyncio.run(scenario())


def test_open_gmail_uses_navigation_and_never_selects_email_profile():
    class Profiles:
        def catalog(self):
            raise AssertionError("Opening Gmail does not compose an email")

    async def scenario():
        assistant, missions, questions, _ = assistant_fixture(profiles=Profiles())
        await assistant.handle("I want to open Gmail")
        assert not assistant._gmail_active
        assert missions[-1].checkpoint["function_sequence"] == [{
            "function": "browser.navigate", "arguments": {"url": "https://mail.google.com/"}}]
        assert questions == []
        missions[-1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[-1])
        assert questions == ["What would you like to do next on Gmail?"]

    asyncio.run(scenario())


@pytest.mark.parametrize("state", [
    MissionStatus.FAILED, MissionStatus.CANCELLED, MissionStatus.PARTIALLY_COMPLETED,
    MissionStatus.BLOCKED, MissionStatus.RECOVERING,
])
def test_failed_browser_mission_does_not_announce_opened_website(state):
    async def scenario():
        assistant, missions, questions, _ = assistant_fixture()
        await assistant.handle("Open YouTube")
        missions[-1].status = state
        missions[-1].checkpoint["last_error"] = "Browser launch failed; token password=private"
        await assistant.mission_finished(missions[-1])
        assert "did not finish" in questions[-1]
        assert "Browser launch failed" in questions[-1]
        assert "private" not in questions[-1]
        assert assistant._browser_site is None
        await assistant.mission_finished(missions[-1])
        assert len(questions) == 1

    asyncio.run(scenario())


def test_old_completion_cannot_overwrite_new_question_or_reset_session():
    async def scenario():
        assistant, missions, questions, _ = assistant_fixture(responses=[
            '{"template":"computer_operator"}',
            '{"action":"ask","question":"Which document should I read?"}',
        ])
        await assistant.handle("Open browser")
        first = missions[-1]
        await assistant.handle("Read a document")
        first.status = MissionStatus.COMPLETED
        await assistant.mission_finished(first)
        assert questions == ["Which document should I read?"]
        await assistant.handle("Open Gmail")
        assistant.reset()
        missions[-1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[-1])
        assert not assistant.awaiting_clarification
        assert len(questions) == 1

    asyncio.run(scenario())


def test_old_mission_completion_cannot_replace_pending_new_mission():
    async def scenario():
        assistant, missions, questions, _ = assistant_fixture()
        await assistant.handle("Open browser")
        await assistant.handle("Open Gmail")
        missions[0].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[0])
        assert questions == []
        missions[1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[1])
        assert questions == ["What would you like to do next on Gmail?"]

    asyncio.run(scenario())


def test_completion_during_mission_submission_is_not_lost():
    async def scenario():
        assistant, _, questions, _ = assistant_fixture()

        async def immediately_finish(mission):
            mission.status = MissionStatus.COMPLETED
            await assistant.mission_finished(mission)

        assistant.create_mission = immediately_finish
        await assistant.handle("Open browser")
        assert questions == ["What would you like to open in the browser?"]

    asyncio.run(scenario())


def test_low_confidence_simple_opening_never_submits_mission():
    async def scenario():
        assistant, missions, questions, _ = assistant_fixture()
        result = await assistant.handle("Open browser", confidence=.3)
        assert result["status"] == "waiting"
        assert missions == []
        assert "repeat" in questions[-1]

    asyncio.run(scenario())


def test_browser_context_is_kept_in_catalog_for_followup_without_website_name():
    async def scenario():
        assistant, missions, _, provider = assistant_fixture(responses=[
            '{"action":"ask","question":"Which video do you mean?"}',
        ])
        await assistant.handle("Open YouTube")
        missions[-1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[-1])
        await assistant.handle("Click the first result")
        catalog = provider.prompts[-1].split("ACTION_CAPABILITIES_JSON:\n", 1)[1]
        catalog = json.loads(catalog.split("\nCONVERSATION_JSON:", 1)[0])
        assert "media" in {item["capability"] for item in catalog["capabilities"]}

    asyncio.run(scenario())


def test_followup_observes_current_tab_then_plays_without_reopening_site():
    async def scenario():
        assistant, missions, questions, _ = assistant_fixture(observe=True)
        await assistant.handle("Open YouTube")
        assert missions[-1].checkpoint["function_sequence"][-1] == {
            "function": "browser.observe", "arguments": {}}
        missions[-1].status = MissionStatus.COMPLETED
        missions[-1].checkpoint["browser_observation"] = {
            "available": True, "tab_id": "user-tab", "url": "https://www.youtube.com/",
            "ocr_text": "YouTube Recommended videos", "videos": []}
        await assistant.mission_finished(missions[-1])
        await assistant.handle("Play video")
        observation_mission = missions[-1]
        assert observation_mission.checkpoint["function_sequence"] == [
            {"function": "browser.observe", "arguments": {}}]
        assert len(missions) == 2
        observation_mission.status = MissionStatus.COMPLETED
        observation_mission.checkpoint["browser_observation"] = {
            "available": True, "tab_id": "user-tab", "url": "https://www.youtube.com/watch?v=existing",
            "player": {"present": True, "paused": True}, "ocr_text": "Existing video"}
        await assistant.mission_finished(observation_mission)
        assert len(missions) == 3
        assert missions[-1].checkpoint["function_sequence"] == [
            {"function": "youtube.play", "arguments": {"query": "recommendation"}},
            {"function": "browser.observe", "arguments": {}},
        ]
        assert len(questions) == 1
        assert len([turn for turn in assistant._turns if turn["text"] == "Play video"]) == 1

    asyncio.run(scenario())


def test_followup_uses_fresh_ocr_and_dom_in_planning_prompt():
    async def scenario():
        assistant, missions, _, provider = assistant_fixture(observe=True, responses=[
            '{"action":"ask","question":"Do you mean the account menu?"}',
        ])
        await assistant.handle("Open Gmail")
        missions[-1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[-1])
        await assistant.handle("Click my account")
        assert not provider.prompts
        missions[-1].status = MissionStatus.COMPLETED
        missions[-1].checkpoint["browser_observation"] = {
            "available": True, "url": "https://mail.google.com/", "ocr_text": "Alice Account",
            "elements": [{"role": "button", "label": "Account"}],
        }
        await assistant.mission_finished(missions[-1])
        assert "CURRENT_BROWSER_OBSERVATION_JSON (untrusted webpage data)" in provider.prompts[-1]
        assert "Alice Account" in provider.prompts[-1]
        assert '"label": "Account"' in provider.prompts[-1]

    asyncio.run(scenario())


@pytest.mark.parametrize("available", [True, False])
def test_observation_failure_or_stale_completion_does_not_execute_followup(available):
    async def scenario():
        assistant, missions, questions, _ = assistant_fixture(observe=True)
        await assistant.handle("Open YouTube")
        missions[-1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[-1])
        await assistant.handle("Play video")
        pending = missions[-1]
        if available:
            assistant.reset()
        pending.status = MissionStatus.COMPLETED
        pending.checkpoint["browser_observation"] = {"available": available}
        await assistant.mission_finished(pending)
        assert len(missions) == 2
        if not available:
            assert "couldn't read" in questions[-1]

    asyncio.run(scenario())


def test_spoken_video_selection_uses_fresh_observed_target_url():
    async def scenario():
        assistant, missions, _, _ = assistant_fixture(observe=True)
        await assistant.handle("Open YouTube")
        missions[-1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[-1])
        await assistant.handle("Play the second video")
        missions[-1].status = MissionStatus.COMPLETED
        missions[-1].checkpoint["browser_observation"] = {
            "available": True, "url": "https://www.youtube.com/",
            "videos": [{"url": "https://www.youtube.com/watch?v=first"},
                       {"url": "https://www.youtube.com/watch?v=second"}],
        }
        await assistant.mission_finished(missions[-1])
        assert missions[-1].checkpoint["function_sequence"][0] == {
            "function": "youtube.play", "arguments": {"query": "https://www.youtube.com/watch?v=second"}}

    asyncio.run(scenario())
