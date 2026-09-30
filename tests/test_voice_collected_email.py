"""A complete spoken email opens Gmail once before drafting and explicit send consent."""
import asyncio
from dataclasses import replace
import pytest

from app.agents.runtime_tools import register_runtime_tools
from app.agents.tools import ToolRegistry
from app.autonomy.mission import MissionStatus
from app.voice.models import VoiceTurn
from tests.test_external_browser_client import ForbiddenManagedBrowser
from tests.test_voice import FakeBrowserLlm
from tests.test_voice_permissions import build, wait_prompt


class Profiles:
    selected_profile = None

    def __init__(self):
        self.opened, self.sent = [], []

    @property
    def active(self):
        return self.selected_profile is not None

    def catalog(self):
        return [{"id": "chrome-work", "browser": "Chrome", "name": "Work", "label": "Chrome Work"}]

    async def select_profile(self, profile_id, profile_label):
        assert (profile_id, profile_label) == ("chrome-work", "Chrome Work")
        self.selected_profile = self.catalog()[0]
        return "Selected Work"

    async def open_gmail(self, profile_id, profile_label):
        self.opened.append((profile_id, profile_label))
        return "Opened Gmail in Work"

    async def send(self, profile_id, profile_label, recipient, subject, body):
        assert self.opened == [(profile_id, profile_label)]
        self.sent.append((recipient, subject, body))
        return "Email sent"


@pytest.mark.parametrize("send_reply", ["no", "yes continue"])
def test_split_email_request_opens_gmail_before_details_and_never_confuses_finish_with_send_permission(tmp_path, send_reply):
    async def scenario():
        profiles = Profiles()
        registry = ToolRegistry()
        register_runtime_tools(registry, ForbiddenManagedBrowser(), tmp_path,
                               gmail_profiles=profiles, external_browser=profiles)
        service, operator, approvals, dialog, _, shown = build(tmp_path, registry)
        service.config = replace(service.config, collect_tasks=True, task_pause_seconds=.01)
        assistant = service.router.assistant
        assistant.gmail_profiles = assistant.external_browser = profiles
        provider = FakeBrowserLlm([
            '{"action":"ask","question":"What recipient email address should I use?"}',
            '{"action":"send","goal":"Send a project update","to":"person@example.com",'
            '"subject":"Project update","body":"The report will be ready Friday."}',
        ])
        assistant.provider = provider
        await service.start()
        await service.process_turn(VoiceTurn("request", "Send an email about the project", .99, True))
        await service.process_turn(VoiceTurn("detail", "The report will be ready Friday", .97, True))
        assert not provider.prompts and not operator.store.all()
        await asyncio.sleep(.015)
        await service._check_request_pause()
        await service.process_turn(VoiceTurn("finish", "no", .99, True))
        assert "profile" in shown[-1].casefold()
        assert not provider.prompts and not operator.store.all() and not profiles.opened

        await service.process_turn(VoiceTurn("profile", "one", .99, True))
        opening_id = service.session.active_mission
        opening = asyncio.create_task(operator.run_once(opening_id))
        await wait_prompt(dialog)
        assert "gmail.open" in shown[-1] and not profiles.opened and not provider.prompts
        await service.process_turn(VoiceTurn("allow-open", "yes continue", .99, True))
        assert (await opening).status is MissionStatus.COMPLETED
        assert profiles.opened == [("chrome-work", "Chrome Work")]
        assert "recipient" in shown[-1].casefold()
        assert "Send an email about the project" in provider.prompts[-1]
        assert "The report will be ready Friday" in provider.prompts[-1]

        await service.process_turn(VoiceTurn("recipient", "person@example.com", .99, True))
        assert not service.snapshot()["request_collection"]["active"]
        send_id = service.session.active_mission
        sending = asyncio.create_task(operator.run_once(send_id))
        await wait_prompt(dialog)
        assert "gmail.send_email" in shown[-1] and not profiles.sent
        # A no to send permission is denial, never task completion; yes sends once.
        await service.process_turn(VoiceTurn("send-decision", send_reply, .99, True))
        result = await sending
        if send_reply == "no":
            assert result.status is not MissionStatus.COMPLETED and not profiles.sent
        else:
            assert result.status is MissionStatus.COMPLETED
            assert profiles.sent == [("person@example.com", "Project update", "The report will be ready Friday.")]
        assert not approvals.pending()
        assert sum("Which browser profile" in (question or "") for question in shown) == 1
        await service.stop()
    asyncio.run(scenario())


def test_gmail_draft_falls_back_to_local_extraction_when_provider_fails(tmp_path):
    async def scenario():
        profiles = Profiles()
        registry = ToolRegistry()
        register_runtime_tools(registry, ForbiddenManagedBrowser(), tmp_path,
                               gmail_profiles=profiles, external_browser=profiles)
        service, operator, approvals, dialog, _, shown = build(tmp_path, registry)
        assistant = service.router.assistant
        assistant.gmail_profiles = assistant.external_browser = profiles

        class FailingProvider:
            prompts = []
            def use_conversation_session(self, key): pass
            async def open(self): pass
            async def verify_page(self): pass
            async def start_conversation(self): pass
            async def send_prompt(self, prompt): self.prompts.append(prompt)
            async def wait_for_response(self, timeout): pass
            async def extract_response(self): raise RuntimeError("Provider unavailable")

        assistant.provider = FailingProvider()
        await service.start()
        await service.process_turn(VoiceTurn("request", "Send an email to partner@example.com about meeting saying we are ready", .99, True))
        assert "profile" in shown[-1].casefold()
        await service.process_turn(VoiceTurn("profile", "one", .99, True))
        opening_id = service.session.active_mission
        opening = asyncio.create_task(operator.run_once(opening_id))
        await wait_prompt(dialog)
        await service.process_turn(VoiceTurn("allow-open", "yes continue", .99, True))
        assert (await opening).status is MissionStatus.COMPLETED
        assert service.session.active_mission != opening_id

        # User says continue, provider still unavailable -> falls back to local extraction!
        # The fallback now happens automatically without requiring that extra turn.
        send_id = service.session.active_mission
        assert send_id is not None
        sending = asyncio.create_task(operator.run_once(send_id))
        await wait_prompt(dialog)
        assert "gmail.send_email" in shown[-1] and not profiles.sent
        await service.process_turn(VoiceTurn("send-decision", "yes continue", .99, True))
        result = await sending
        assert result.status is MissionStatus.COMPLETED
        assert len(profiles.sent) == 1
        assert profiles.sent[0][0] == "partner@example.com"
        assert "Meeting" in profiles.sent[0][1]
        assert "We are ready." in profiles.sent[0][2]
        await service.stop()
    asyncio.run(scenario())
