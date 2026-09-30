"""Spoken browser profile selection remains inside governed tool execution."""
import asyncio
import pytest

from app.agents.tools import RiskLevel, ToolSpec
from app.autonomy.mission import MissionStatus
from app.safety.permissions import Permission
from tests.test_voice_browser_followup import assistant_fixture


class ExternalBrowser:
    selected_profile = None

    def catalog(self):
        return [
            {"id": "chrome-work", "browser": "Google Chrome", "name": "Work",
             "label": "Google Chrome — Work"},
            {"id": "chrome-profile-two", "browser": "Google Chrome", "name": "Profile 2",
             "label": "Google Chrome — Profile 2"},
            {"id": "edge-personal", "browser": "Microsoft Edge", "name": "Personal",
             "label": "Microsoft Edge — Personal"},
        ]


def external_assistant(*, responses=(), observe=False):
    assistant, missions, questions, provider = assistant_fixture(responses=responses, observe=observe)
    assistant.external_browser = ExternalBrowser()
    assistant._tool_registry.register(ToolSpec(
        "browser.select_profile", "Select browser profile", "Select a discovered browser profile",
        frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.MEDIUM,
        lambda _: None, ("profile_id", "profile_label")))
    assistant._functions = assistant._function_inventory(assistant._tool_registry)
    assistant._functions_by_id = {item["function"]: item for item in assistant._functions}
    return assistant, missions, questions, provider


def test_external_profile_selection_keeps_original_website_request_governed():
    async def scenario():
        assistant, missions, questions, provider = external_assistant()
        response = await assistant.handle("Open YouTube")
        assert response["status"] == "waiting"
        assert "Google Chrome — Work" in questions[-1]
        assert "Managed browser" in questions[-1]
        assert not missions
        selected = await assistant.handle("Chrome Profile 2")
        assert selected["status"] == "accepted"
        assert missions[-1].checkpoint["function_sequence"] == [
            {"function": "browser.select_profile", "arguments": {
                "profile_id": "chrome-profile-two", "profile_label": "Google Chrome — Profile 2"}},
            {"function": "browser.navigate", "arguments": {"url": "https://www.youtube.com/"}},
        ]
        assert assistant.external_browser.selected_profile is None
        assert assistant._browser_profile_confirmed is None
        missions[-1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[-1])
        assert assistant._browser_profile_confirmed == ("chrome-profile-two", "Google Chrome — Profile 2")
        assert questions[-1] == "What would you like to do next on YouTube?"
        await assistant.handle("Search for tutorial videos")
        assert missions[-1].checkpoint["function_sequence"] == [
            {"function": "youtube.search", "arguments": {"query": "tutorial videos"}}]
        assert not provider.prompts

    asyncio.run(scenario())


def test_ambiguous_browser_name_reprompts_and_managed_choice_is_explicit():
    async def scenario():
        assistant, missions, questions, _ = external_assistant()
        await assistant.handle("Open browser")
        response = await assistant.handle("Chrome")
        assert response["status"] == "waiting"
        assert not missions
        await assistant.handle("managed browser")
        assert missions[-1].checkpoint["function_sequence"] == [
            {"function": "browser.select_profile", "arguments": {
                "profile_id": "managed", "profile_label": "Managed browser"}},
            {"function": "browser.open", "arguments": {}},
        ]
        assert len(questions) == 2

    asyncio.run(scenario())


def test_low_confidence_profile_answer_never_selects_or_opens_browser():
    async def scenario():
        assistant, missions, _, _ = external_assistant()
        await assistant.handle("Open Gmail")
        response = await assistant.handle("one", confidence=.3)
        assert response["status"] == "waiting"
        assert not missions
        assert assistant._browser_profile_choice is None

    asyncio.run(scenario())


def test_spoken_number_uses_displayed_profile_order_when_discovery_changes():
    async def scenario():
        assistant, missions, _, _ = external_assistant()
        await assistant.handle("Open YouTube")
        original = assistant.external_browser.catalog()
        assistant.external_browser.catalog = lambda: list(reversed(original))
        await assistant.handle("one")
        assert missions[-1].checkpoint["function_sequence"][0]["arguments"]["profile_id"] == original[0]["id"]
    asyncio.run(scenario())


def test_explicit_switch_profile_submits_new_selection_before_opening():
    async def scenario():
        assistant, missions, _, _ = external_assistant()
        await assistant.handle("Open Gmail")
        await assistant.handle("one")
        missions[-1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[-1])
        response = await assistant.handle("Switch browser profile")
        assert response["status"] == "waiting"
        await assistant.handle("Edge Personal")
        assert missions[-1].checkpoint["function_sequence"][0] == {
            "function": "browser.select_profile", "arguments": {
                "profile_id": "edge-personal", "profile_label": "Microsoft Edge — Personal"}}

    asyncio.run(scenario())


@pytest.mark.parametrize("utterance,query", [("Play music on YouTube", "music"),
                                           ("Play a YouTube video", "recommendation")])
def test_music_request_after_profile_selection_launches_playback_before_observing(utterance, query):
    async def scenario():
        assistant, missions, questions, provider = external_assistant(observe=True)
        assert (await assistant.handle(utterance))["status"] == "waiting"
        await assistant.handle("one")
        assert [call["function"] for call in missions[-1].checkpoint["function_sequence"]] == [
            "browser.select_profile", "youtube.play", "browser.observe"]
        assert missions[-1].checkpoint["function_sequence"][1]["arguments"] == {"query": query}
        assert not provider.prompts
        assert len(missions) == 1

    asyncio.run(scenario())


def test_native_screen_evidence_guides_grounded_response_without_managed_navigation():
    async def scenario():
        assistant, missions, _, provider = external_assistant(observe=True, responses=[
            '{"action":"ask","question":"The current page shows your inbox. What would you like to do next?"}',
        ])
        assistant.external_browser.selected_profile = {"id": "chrome-work", "label": "Google Chrome — Work"}
        assistant._browser_site = "Gmail"
        assistant.last_template = "computer_operator"
        await assistant.handle("What is on the screen?")
        assert missions[-1].checkpoint["function_sequence"] == [
            {"function": "browser.observe", "arguments": {}}]
        missions[-1].status = MissionStatus.COMPLETED
        missions[-1].checkpoint["browser_observation"] = {
            "available": True, "backend": "native", "url": "https://mail.google.com/",
            "ocr_text": "Inbox", "elements": [{"runtime_id": "visible-button-1", "label": "Compose"}],
        }
        result = await assistant.mission_finished(missions[-1])
        assert result["status"] == "waiting"
        assert "browser.external_action" in provider.prompts[-1]
        assert "visible-button-1" in provider.prompts[-1]
        assert len(missions) == 1

    asyncio.run(scenario())
