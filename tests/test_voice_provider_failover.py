import asyncio

from app.voice.action_catalog import build_action_catalog, capability_summary
from app.voice.provider_failover import BrowserProviderFailover


class FakeProvider:
    def __init__(self, name, response=None, error=None):
        self.name = name
        self.response = response
        self.error = error
        self.sessions = []
        self.prompts = []

    def use_conversation_session(self, key):
        self.sessions.append(key)

    def prepare_conversation(self, _prompt):
        pass

    async def open(self):
        pass

    async def verify_page(self):
        pass

    async def start_conversation(self):
        pass

    async def send_prompt(self, prompt):
        self.prompts.append(prompt)

    async def wait_for_response(self, _timeout):
        if self.error:
            raise self.error

    async def extract_response(self):
        return self.response


def test_browser_llm_falls_back_to_next_configured_provider():
    async def scenario():
        primary = FakeProvider("chatgpt", error=TimeoutError())
        fallback = FakeProvider("gemini", response='{"action":"ask"}')
        provider = BrowserProviderFailover([primary, fallback])
        provider.use_conversation_session("voice-session")

        response = await provider.complete("task prompt")

        assert response == '{"action":"ask"}'
        assert primary.sessions == ["voice-session:chatgpt"]
        assert fallback.sessions == ["voice-session:gemini"]
        assert fallback.prompts == ["task prompt"]

    asyncio.run(scenario())


def test_browser_llm_prefers_working_provider_and_can_skip_it_for_correction():
    async def scenario():
        first = FakeProvider("chatgpt", response="first response")
        second = FakeProvider("claude", response="corrected response")
        provider = BrowserProviderFailover([first, second])

        assert await provider.complete("initial") == "first response"
        assert await provider.complete("correction", exclude_active=True) == "corrected response"
        assert second.prompts == ["correction"]

    asyncio.run(scenario())


def test_focused_email_turn_uses_only_the_active_provider_once():
    async def scenario():
        primary = FakeProvider("chatgpt", error=TimeoutError())
        fallback = FakeProvider("gemini", response='{"action":"ask_profile"}')
        provider = BrowserProviderFailover([primary, fallback])

        try:
            await provider.complete_primary("email profile decision")
        except TimeoutError:
            pass
        else:
            raise AssertionError("A failed focused request must be reported")
        assert primary.prompts == ["email profile decision"]
        assert fallback.prompts == []

    asyncio.run(scenario())


def test_browser_llm_failover_reports_providers_when_all_fail():
    async def scenario():
        provider = BrowserProviderFailover([
            FakeProvider("chatgpt", error=TimeoutError()),
            FakeProvider("gemini", error=ConnectionError()),
        ])

        try:
            await provider.complete("task prompt")
        except RuntimeError as error:
            assert "chatgpt: TimeoutError" in str(error)
            assert "gemini: ConnectionError" in str(error)
        else:
            raise AssertionError("All-provider failure should not produce a response")

    asyncio.run(scenario())


def test_action_catalog_scopes_functions_to_task_capabilities():
    tools = [
        {"function": "browser.navigate", "description": "Open a URL",
         "arguments": ["url"], "category": "browser"},
        {"function": "youtube.play", "description": "Play media",
         "arguments": ["query"], "category": "media"},
        {"function": "filesystem.read", "description": "Read a file",
         "arguments": ["path"], "category": "files"},
    ]

    catalog, allowed = build_action_catalog(
        tools, "Play Sayara on YouTube", "computer_operator")

    assert {entry["capability"] for entry in catalog["capabilities"]} == {"browser", "media"}
    assert set(allowed) == {"browser.navigate", "youtube.play"}
    assert "filesystem.read" not in allowed


def test_capability_summary_omits_individual_function_details():
    summary = capability_summary([
        {"function": "browser.navigate", "description": "Open a URL", "category": "browser"},
        {"function": "browser.type", "description": "Type into a page", "category": "browser"},
    ])

    assert '"capability": "browser"' in summary
    assert '"available_actions": 2' in summary
    assert "browser.navigate" not in summary


def test_youtube_task_keeps_video_action_in_scoped_media_capability():
    tools = [
        {"function": "youtube.play", "description": "Play YouTube video",
         "arguments": ["query"], "category": "media"},
        {"function": "youtube.control", "description": "Control current YouTube playback",
         "arguments": ["action", "seconds"], "category": "media"},
        {"function": "filesystem.read", "description": "Read a file",
         "arguments": ["path"], "category": "files"},
    ]

    catalog, allowed = build_action_catalog(
        tools, "Play a YouTube video", "computer_operator")

    assert set(allowed) == {"youtube.play", "youtube.control"}
    assert catalog["capabilities"][0]["capability"] == "media"


def test_blender_task_receives_registered_creative_action():
    tools = [
        {"function": "blender.scene", "description": "Create and open Blender scenes",
         "arguments": ["operation", "project", "visible", "live", "steps"],
         "category": "blender.scene"},
        {"function": "browser.navigate", "description": "Open a URL",
         "arguments": ["url"], "category": "browser"},
    ]

    catalog, allowed = build_action_catalog(
        tools, "Create a Blender scene", "creative_3d_operator")

    assert set(allowed) == {"blender.scene"}
    assert [entry["capability"] for entry in catalog["capabilities"]] == ["creative"]


def test_email_task_catalog_includes_only_registered_mail_and_browser_actions():
    tools = [
        {"function": "gmail.send_email", "description": "Send Gmail email",
         "arguments": ["to", "subject", "body"], "category": "email"},
        {"function": "browser.navigate", "description": "Open a URL",
         "arguments": ["url"], "category": "browser"},
        {"function": "youtube.play", "description": "Play YouTube",
         "arguments": ["query"], "category": "media"},
    ]

    catalog, allowed = build_action_catalog(
        tools, "Send an email to a colleague", "computer_operator")

    assert set(allowed) == {"gmail.send_email", "browser.navigate"}
    assert {entry["capability"] for entry in catalog["capabilities"]} == {
        "browser", "email",
    }
