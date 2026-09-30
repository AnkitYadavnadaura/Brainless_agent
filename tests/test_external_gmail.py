import asyncio

import pytest

from app.browser.external_gmail import ExternalGmailProfiles
from app.browser.fleet_discovery import (
    BrowserInstallation,
    BrowserInventory,
    BrowserProfile,
)
from app.agents.runtime_tools import register_runtime_tools
from app.autonomy.mission import MissionStatus
from app.voice.conversation import BrowserVoiceAssistant, VoiceConversationError
from app.agents.tools import RiskLevel, ToolRegistry, ToolSpec
from app.safety.permissions import Permission


def _inventory(tmp_path):
    browser = BrowserInstallation(
        "chrome-id", "Google Chrome", "chromium", tmp_path / "chrome.exe",
        tmp_path / "Chrome User Data")
    profile = BrowserProfile(
        "chrome-work", browser.id, "Work", browser.user_data_dir / "Profile 2",
        "Profile 2")
    return BrowserInventory([browser], [profile], [])


class FakeTransport:
    def __init__(self):
        self.launch_arguments = None
        self.marker = None
        self.navigated = []
        self.focused = []

    async def launch(self, arguments, marker):
        self.launch_arguments, self.marker = arguments, marker
        return 42

    async def navigate_gmail(self, hwnd):
        self.navigated.append(hwnd)

    async def window_alive(self, hwnd):
        return hwnd == 42

    async def _serialized(self, operation, *arguments):
        return operation(*arguments)

    async def run_owned_operation(self, hwnd, operation, *arguments):
        self.focused.append(hwnd)
        return operation(hwnd, *arguments)


def test_external_gmail_uses_only_the_selected_owned_profile(tmp_path):
    async def scenario():
        transport = FakeTransport()
        driven = []
        sender = ExternalGmailProfiles(
            tmp_path, discover=lambda **_: _inventory(tmp_path),
            transport_factory=lambda: transport,
            ui_runner=lambda hwnd, payload: driven.append((hwnd, payload))
            or {"ok": True, "sent": True},
        )

        result = await sender.send(
            "chrome-work", "Google Chrome — Work", "person@example.com", "Update",
            "Ready for review.")

        assert result == "Email sent to person@example.com using Google Chrome / Work"
        assert transport.launch_arguments[0] == str(tmp_path / "chrome.exe")
        assert "--profile-directory=Profile 2" in transport.launch_arguments
        assert transport.navigated == [42]
        assert transport.focused == [42]
        assert driven == [(42, {
            "to": "person@example.com", "subject": "Update", "body": "Ready for review.",
        })]

    asyncio.run(scenario())


def test_external_gmail_refuses_unknown_profiles_without_launching(tmp_path):
    async def scenario():
        transport = FakeTransport()
        sender = ExternalGmailProfiles(
            tmp_path, discover=lambda **_: _inventory(tmp_path),
            transport_factory=lambda: transport,
            ui_runner=lambda *_: {"ok": True, "sent": True},
        )
        with pytest.raises(ValueError, match="no longer available"):
            await sender.send(
                "not-discovered", "Google Chrome — Missing", "person@example.com",
                "Update", "Body")
        assert transport.launch_arguments is None

    asyncio.run(scenario())


def test_registered_gmail_action_routes_to_selected_profile_and_keeps_approval_risk(tmp_path):
    async def scenario():
        class Sender:
            def __init__(self):
                self.calls = []

            async def send(self, *arguments):
                self.calls.append(arguments)
                return "confirmed"

        sender = Sender()
        registry = ToolRegistry()
        register_runtime_tools(registry, None, tmp_path, gmail_profiles=sender)
        action = registry.get("gmail.send_email")
        assert action.risk is RiskLevel.HIGH and action.destructive
        assert set(action.input_schema) == {
            "to", "subject", "body", "profile_id", "profile_label",
        }
        result = await registry.invoke("gmail.send_email", {
            "to": "person@example.com", "subject": "Update", "body": "Ready.",
            "profile_id": "edge-personal", "profile_label": "Microsoft Edge — Personal",
        })
        assert result == "confirmed"
        assert sender.calls == [(
            "edge-personal", "Microsoft Edge — Personal",
            "person@example.com", "Update", "Ready.",
        )]

    asyncio.run(scenario())


class FakeProvider:
    def __init__(self):
        self.responses = iter([
            '{"template":"computer_operator"}',
            '{"action":"execute","goal":"Send the project update",'
            '"sequence":[{"function":"gmail.send_email","arguments":'
            '{"to":"person@example.com","subject":"Update","body":"Ready."}}]}',
        ])
        self.prompts = []

    def use_conversation_session(self, _key):
        return None

    async def complete(self, prompt, *, exclude_active=False):
        self.prompts.append(prompt)
        return next(self.responses)


class FakeProfiles:
    def __init__(self, *, open_failures=0):
        self.opened = []
        self.open_failures = open_failures

    def catalog(self):
        return [
            {"id": "chrome-work", "browser": "Google Chrome", "name": "Work",
             "label": "Google Chrome — Work"},
            {"id": "chrome-personal", "browser": "Google Chrome", "name": "Personal",
             "label": "Google Chrome — Personal"},
            {"id": "edge-personal", "browser": "Microsoft Edge", "name": "Personal",
             "label": "Microsoft Edge — Personal"},
        ]

    async def open_gmail(self, profile_id, profile_label):
        self.opened.append((profile_id, profile_label))
        if self.open_failures:
            from app.browser.native_console import NativeTransportError
            self.open_failures -= 1
            raise NativeTransportError(
                "Browser focus changed; input stopped to protect the other window")


def register_gmail_open(registry):
    registry.register(ToolSpec(
        "gmail.open", "Open Gmail", "Open Gmail in the exact chosen profile",
        frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.MEDIUM,
        lambda _: None, ("profile_id", "profile_label"), category="email"))


def test_voice_selects_profile_before_planning_and_binds_it_to_email_call(tmp_path):
    async def scenario():
        registry = ToolRegistry()
        register_gmail_open(registry)
        registry.register(ToolSpec(
            "gmail.send_email", "Send Gmail email", "Send an email",
            frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.HIGH,
            lambda _: None,
            ("to", "subject", "body", "profile_id", "profile_label"),
            category="email", destructive=True,
        ))
        provider = FakeProvider()
        provider.responses = iter([
            '{"action":"send","goal":"Send the project update",'
            '"to":"person@example.com","subject":"Update","body":"Ready."}',
        ])
        missions, questions = [], []

        async def create_mission(mission):
            missions.append(mission)
            return mission

        profiles = FakeProfiles()
        assistant = BrowserVoiceAssistant(
            provider, create_mission, questions.append, lambda: None, registry,
            gmail_profiles=profiles)

        selected = await assistant.handle("Send an email with the project update")
        assert selected["status"] == "waiting"
        assert "profile" in selected["question"].casefold()
        assert not provider.prompts

        submitted = await assistant.handle("Microsoft Edge Personal")
        assert submitted["status"] == "accepted"
        assert missions[0].checkpoint["function_sequence"] == [{
            "function": "gmail.open", "arguments": {
                "profile_id": "edge-personal", "profile_label": "Microsoft Edge — Personal"}}]
        assert not provider.prompts
        missions[0].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[0])
        sequence = missions[1].checkpoint["function_sequence"]
        assert sequence == [{
            "function": "gmail.send_email",
            "arguments": {
                "to": "person@example.com", "subject": "Update", "body": "Ready.",
                "profile_id": "edge-personal",
                "profile_label": "Microsoft Edge — Personal",
            },
        }]
        assert profiles.opened == []
        assert len(provider.prompts) == 1
        assert "do not ask the user to write the subject or body" in provider.prompts[-1]

    asyncio.run(scenario())


def test_voice_profile_reply_is_confirmed_once_then_email_followup_executes(tmp_path):
    async def scenario():
        registry = ToolRegistry()
        register_gmail_open(registry)
        registry.register(ToolSpec(
            "gmail.send_email", "Send Gmail email", "Send an email",
            frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.HIGH,
            lambda _: None,
            ("to", "subject", "body", "profile_id", "profile_label"),
            category="email", destructive=True,
        ))
        provider = FakeProvider()
        provider.responses = iter([
            '{"action":"ask","question":"What recipient email address should I use?"}',
            '{"action":"send","goal":"Send the project update",'
            '"to":"person@example.com","subject":"Update","body":"Ready."}',
        ])
        missions, questions = [], []
        profiles = FakeProfiles()

        async def create_mission(mission):
            missions.append(mission)

        assistant = BrowserVoiceAssistant(
            provider, create_mission,
            questions.append, lambda: None, registry, gmail_profiles=profiles)

        await assistant.handle("Send an email with the project update")
        confirmed = await assistant.handle("Microsoft Edge Personal")
        assert confirmed["status"] == "accepted"
        assert not provider.prompts
        missions[0].status = MissionStatus.COMPLETED
        confirmed = await assistant.mission_finished(missions[0])
        assert confirmed["status"] == "waiting"
        assert "recipient" in confirmed["question"].casefold()
        assert profiles.opened == []

        submitted = await assistant.handle("person@example.com, subject Update, body Ready")
        assert submitted["status"] == "accepted"
        assert missions[1].checkpoint["function_sequence"][0]["arguments"] == {
            "to": "person@example.com", "subject": "Update", "body": "Ready.",
            "profile_id": "edge-personal",
            "profile_label": "Microsoft Edge — Personal",
        }

    asyncio.run(scenario())


def test_profile_directory_name_is_not_confused_with_menu_number(tmp_path):
    class Profiles:
        def catalog(self):
            return [
                {"id": "chrome-work", "browser": "Google Chrome", "name": "Work",
                 "label": "Google Chrome — Work"},
                {"id": "edge-work", "browser": "Microsoft Edge", "name": "Work",
                 "label": "Microsoft Edge — Work"},
                {"id": "chrome-profile-two", "browser": "Google Chrome", "name": "Profile 2",
                 "label": "Google Chrome — Profile 2"},
            ]

    registry = ToolRegistry()
    registry.register(ToolSpec(
        "gmail.send_email", "Send Gmail email", "Send an email",
        frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.HIGH,
        lambda _: None,
        ("to", "subject", "body", "profile_id", "profile_label"),
        category="email", destructive=True,
    ))
    assistant = BrowserVoiceAssistant(
        FakeProvider(), lambda _: None, lambda _: None, lambda: None,
        registry, gmail_profiles=Profiles())
    assert assistant._match_email_profile("Chrome Profile 2") == (
        "chrome-profile-two", "Google Chrome — Profile 2")


def test_gmail_draft_rejects_request_to_user_to_write_subject_or_body():
    with pytest.raises(VoiceConversationError, match="instead of generating a draft"):
        BrowserVoiceAssistant._parse_gmail_draft_decision(
            '{"action":"ask","question":"What should I write in the body?"}')


def test_profile_selection_opens_gmail_through_mission_before_draft_planning(tmp_path):
    async def scenario():
        registry = ToolRegistry()
        register_gmail_open(registry)
        registry.register(ToolSpec(
            "gmail.send_email", "Send Gmail email", "Send an email",
            frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.HIGH,
            lambda _: None,
            ("to", "subject", "body", "profile_id", "profile_label"),
            category="email", destructive=True,
        ))
        provider = FakeProvider()
        provider.responses = iter([
            '{"action":"ask","question":"What recipient email address should I use?"}',
        ])
        profiles = FakeProfiles(open_failures=1)
        questions, missions = [], []

        async def create(mission):
            missions.append(mission)

        assistant = BrowserVoiceAssistant(
            provider, create, questions.append, lambda: None,
            registry, gmail_profiles=profiles)

        result = await assistant.handle("Send an email to my colleague")
        assert result["status"] == "waiting"
        result = await assistant.handle("Chrome Work")
        assert result["status"] == "accepted"
        assert assistant._gmail_stage == "opening"
        assert not provider.prompts
        assert missions[0].checkpoint["function_sequence"][0]["function"] == "gmail.open"
        missions[0].status = MissionStatus.COMPLETED
        result = await assistant.mission_finished(missions[0])
        assert "recipient email" in result["question"]
        assert assistant._gmail_stage == "draft"
        assert profiles.opened == []
        assert len(provider.prompts) == 1

    asyncio.run(scenario())


def test_voice_reprompts_when_profile_name_is_ambiguous(tmp_path):
    async def scenario():
        registry = ToolRegistry()
        registry.register(ToolSpec(
            "gmail.send_email", "Send Gmail email", "Send an email",
            frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.HIGH,
            lambda _: None,
            ("to", "subject", "body", "profile_id", "profile_label"),
            category="email", destructive=True,
        ))
        provider = FakeProvider()
        provider.responses = iter([
            '{"action":"ask_profile","question":"Which profile should I use?"}',
            '{"action":"ask_profile","question":"Please say the browser and profile name."}',
        ])
        assistant = BrowserVoiceAssistant(
            provider, lambda _: None, lambda _: None, lambda: None,
            registry, gmail_profiles=FakeProfiles())
        await assistant.handle("Send an email")
        result = await assistant.handle("Chrome")
        assert result["status"] == "waiting"
        assert "browser profile" in result["question"].casefold()
        assert not provider.prompts

    asyncio.run(scenario())


def gmail_voice_fixture(responses, *, selected=None):
    registry = ToolRegistry()
    register_gmail_open(registry)
    registry.register(ToolSpec(
        "gmail.send_email", "Send email", "Send the selected email",
        frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.HIGH,
        lambda _: None, ("to", "subject", "body", "profile_id", "profile_label"),
        category="email", destructive=True))
    provider = FakeProvider()
    provider.responses = iter(responses)
    profiles = FakeProfiles()
    profiles.selected_profile = selected
    missions, questions = [], []

    async def create(mission):
        missions.append(mission)

    assistant = BrowserVoiceAssistant(
        provider, create, questions.append, lambda: None, registry,
        gmail_profiles=profiles, external_browser=profiles)
    return assistant, provider, missions, questions


def test_gmail_reuses_external_profile_and_retains_it_across_open_denial():
    async def scenario():
        selected = {"id": "edge-personal", "label": "Microsoft Edge — Personal"}
        assistant, provider, missions, questions = gmail_voice_fixture([
            '{"action":"ask","question":"What recipient email address should I use?"}',
        ], selected=selected)
        result = await assistant.handle("Send an email with a project update")
        assert result["status"] == "accepted"
        assert not questions and not provider.prompts
        first = missions[0]
        first.status = MissionStatus.BLOCKED
        first.checkpoint["last_error"] = "Permission denied"
        result = await assistant.mission_finished(first)
        assert "Permission denied" in result["question"]
        assert "continue" in result["question"]
        assert assistant._selected_email_profile_id == selected["id"]
        assert not assistant.accepting_new_task
        await assistant.handle("continue")
        assert missions[1].checkpoint["function_sequence"] == first.checkpoint["function_sequence"]
        assert not provider.prompts
        missions[1].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[1])
        assert "recipient" in questions[-1]
        assert assistant._gmail_stage == "draft"

    asyncio.run(scenario())


def test_gmail_number_selection_is_deterministic_and_low_confidence_does_not_open():
    async def scenario():
        assistant, provider, missions, _ = gmail_voice_fixture([])
        assert assistant.accepting_new_task
        await assistant.handle("Send an email")
        assert not assistant.accepting_new_task
        await assistant.handle("three", confidence=.3)
        assert not missions
        await assistant.handle("number three")
        assert missions[0].checkpoint["function_sequence"][0]["arguments"] == {
            "profile_id": "edge-personal", "profile_label": "Microsoft Edge — Personal"}
        assert not provider.prompts

    asyncio.run(scenario())


def test_gmail_open_completion_includes_details_spoken_while_opening():
    async def scenario():
        assistant, provider, missions, _ = gmail_voice_fixture([
            '{"action":"ask","question":"What recipient email address should I use?"}',
        ])
        await assistant.handle("Send an email with the project update")
        await assistant.handle("Chrome Work")
        response = await assistant.handle("Mention that the meeting is tomorrow")
        assert response["mission_id"] == missions[0].mission_id
        assert len(missions) == 1 and not provider.prompts
        missions[0].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[0])
        assert "meeting is tomorrow" in provider.prompts[-1]
        assert assistant._gmail_stage == "draft"

    asyncio.run(scenario())


def test_gmail_drafting_uses_current_email_scope_and_remembers_previous_profile():
    async def scenario():
        assistant, provider, missions, _ = gmail_voice_fixture([
            '{"action":"send","goal":"Send old update","to":"old@example.com","subject":"Old","body":"Old facts"}',
            '{"action":"ask","question":"What recipient email address should I use?"}',
        ])
        await assistant.handle("Send an email to old@example.com with old confidential project facts")
        await assistant.handle("Chrome Work")
        missions[0].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[0])
        assert missions[1].checkpoint["function_sequence"][0]["function"] == "gmail.send_email"
        await assistant.handle("Send a new email about tomorrow's lunch")
        assert missions[2].checkpoint["function_sequence"][0]["arguments"]["profile_id"] == "chrome-work"
        missions[2].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[2])
        assert "tomorrow's lunch" in provider.prompts[-1]
        assert "old@example.com" not in provider.prompts[-1]
        assert "old confidential project facts" not in provider.prompts[-1]

    asyncio.run(scenario())


def test_repeated_model_profile_questions_keep_gmail_draft_recoverable():
    async def scenario():
        assistant, provider, missions, questions = gmail_voice_fixture([
            '{"action":"ask","question":"Which browser profile should I use?"}',
            '{"action":"ask","question":"Which browser should I use?"}',
            '{"action":"ask","question":"What recipient email address should I use?"}',
        ])
        await assistant.handle("Send an email with the project update")
        await assistant.handle("Chrome Work")
        missions[0].status = MissionStatus.COMPLETED
        result = await assistant.mission_finished(missions[0])
        assert result["status"] == "waiting"
        assert "keep using" in questions[-1]
        assert assistant._selected_email_profile_id == "chrome-work"
        assert assistant._gmail_stage == "draft"
        await assistant.handle("continue")
        assert "recipient" in questions[-1]
        assert len(missions) == 1
        assert len(provider.prompts) == 3

    asyncio.run(scenario())


def test_gmail_open_completion_after_reset_cannot_restart_email_draft():
    async def scenario():
        assistant, provider, missions, _ = gmail_voice_fixture([])
        await assistant.handle("Send an email")
        await assistant.handle("Chrome Work")
        assistant.reset()
        missions[0].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[0])
        assert not provider.prompts
        assert not assistant._gmail_active
        assert assistant.accepting_new_task

    asyncio.run(scenario())


@pytest.mark.parametrize("failure", ["timeout", "invalid_json", "profile_correction"])
@pytest.mark.parametrize("after_clarification", [False, True])
def test_gmail_draft_failure_retries_without_reopening_or_losing_details(failure, after_clarification):
    async def scenario():
        assistant, provider, missions, questions = gmail_voice_fixture([])
        original = assistant._ask_email_provider

        async def failing(prompt):
            if failure == "timeout":
                raise TimeoutError("provider unavailable")
            return await original(prompt)

        await assistant.handle("Send an email about tomorrow's project meeting")
        await assistant.handle("Chrome Work")
        missions[0].status = MissionStatus.COMPLETED
        if after_clarification:
            provider.responses = iter(['{"action":"ask","question":"What recipient email address should I use?"}'])
            await assistant.mission_finished(missions[0])
        provider.responses = iter(
            ['{"action":"ask","question":"Which browser profile should I use?"}', 'invalid']
            if failure == "profile_correction" else ['invalid'])
        assistant._ask_email_provider = failing
        result = (await assistant.handle("person@example.com") if after_clarification
                  else await assistant.mission_finished(missions[0]))
        if after_clarification:
            assert result["status"] == "accepted"
            assert len(missions) == 2
            call = missions[-1].checkpoint["function_sequence"][0]
            assert call["function"] == "gmail.send_email"
            assert call["arguments"]["to"] == "person@example.com"
            assert "tomorrow's project meeting" in call["arguments"]["body"].casefold()
            assert "Chrome Work" not in call["arguments"]["body"]
            return
        assert result["status"] == "waiting"
        assert "continue" in questions[-1]
        assert assistant._selected_email_profile_id == "chrome-work"
        assert not assistant.accepting_new_task
        assistant._ask_email_provider = original
        provider.responses = iter([
            '{"action":"send","goal":"Send update","to":"person@example.com",'
            '"subject":"Meeting","body":"Tomorrow is the project meeting."}',
        ])
        await assistant.handle("continue with person@example.com")
        assert [m.checkpoint["function_sequence"][0]["function"] for m in missions] == [
            "gmail.open", "gmail.send_email"]
        assert "tomorrow's project meeting" in provider.prompts[-1]
        assert "person@example.com" in provider.prompts[-1]
        assert missions[-1].checkpoint["function_sequence"][0]["arguments"]["profile_id"] == "chrome-work"

    asyncio.run(scenario())


def test_gmail_draft_cancellation_does_not_show_retry_question():
    async def scenario():
        assistant, _, missions, questions = gmail_voice_fixture([])

        async def cancelled(prompt):
            raise asyncio.CancelledError()

        await assistant.handle("Send an email")
        await assistant.handle("Chrome Work")
        assistant._ask_email_provider = cancelled
        missions[0].status = MissionStatus.COMPLETED
        before = list(questions)
        with pytest.raises(asyncio.CancelledError):
            await assistant.mission_finished(missions[0])
        assert questions == before
        assert len(missions) == 1

    asyncio.run(scenario())
