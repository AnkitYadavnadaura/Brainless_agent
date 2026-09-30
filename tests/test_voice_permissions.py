import asyncio
import json

from app.agents.manager import AgentManager
from app.agents.tools import RiskLevel, ToolRegistry, ToolSpec
from app.autonomy.approvals import ApprovalStore, ApprovalSystem, ApprovalStatus
from app.autonomy.events import AutonomousEventBus
from app.autonomy.executor import ActionRuntime
from app.autonomy.mission import MissionStatus, MissionStore
from app.autonomy.mode_policy import ModePolicy
from app.autonomy.models import ComputerAction, ComputerState
from app.autonomy.operator import AutonomousOperator, AutonomyMode
from app.autonomy.orchestrator import AutonomousRuntime
from app.autonomy.perception_service import PerceptionService
from app.autonomy.production_mission import RuntimeMissionComposer
from app.autonomy.task_engine import AutonomousTaskEngine
from app.dashboard.service import DashboardRuntime, RuntimeCommandGateway
from app.safety.permissions import Permission, PermissionGrantStore, PermissionPolicy
from app.voice.config import VoiceConfig
from app.voice.conversation import BrowserVoiceAssistant
from app.voice.models import VoiceTurn
from app.voice.permissions import VoicePermissionDialog
from app.voice.service import VoiceRuntimeRouter, VoiceService
from app.voice.store import VoiceMetadataStore
from tests.test_voice import FakeBrowserLlm, FakeStreamingTransport


class Controller:
    async def observe(self):
        return ComputerState(active_application="test")


def build(tmp_path, registry=None):
    calls, shown = [], []
    if registry is None:
        registry = ToolRegistry()
        for name, schema in (("browser.open", ()), ("browser.navigate", ("url",)),
                             ("youtube.search", ("query",))):
            registry.register(ToolSpec(name, name, "Browser action",
                frozenset({"browser.navigate"}), RiskLevel.MEDIUM,
                lambda arguments, name=name: calls.append((name, arguments)) or "opened",
                schema))
    policy = PermissionPolicy(grant_store=PermissionGrantStore(tmp_path / "grants.json"),
                              require_first_use=True)
    manager = AgentManager(registry, policy=policy)
    root = manager.create_root("Operator", "root", "supervise", {item.value for item in Permission})
    approvals = ApprovalSystem(ApprovalStore(tmp_path / "approvals.json"), manager, timeout_seconds=2)
    dialog = VoicePermissionDialog(approvals, shown.append, lambda: shown.append(None))
    actions = ActionRuntime(manager, Controller(), approval_handler=approvals.request,
                            mode_policy=ModePolicy(AutonomyMode.SUPERVISED))
    autonomous = AutonomousRuntime(manager, actions)
    composer = RuntimeMissionComposer(autonomous, AutonomousTaskEngine(autonomous, actions), root.agent_id)
    missions = MissionStore(tmp_path / "missions.json")
    events = AutonomousEventBus()
    operator = AutonomousOperator(missions, PerceptionService(Controller(), actions.world_state, events),
                                  events, composer)
    assistant = BrowserVoiceAssistant(FakeBrowserLlm([]), operator.create,
        dialog.show_conversation, dialog.dismiss_conversation, registry)
    router = VoiceRuntimeRouter(operator, missions, approvals, assistant=assistant,
                                permission_dialog=dialog)
    service = VoiceService(VoiceConfig("key", collect_tasks=False), FakeStreamingTransport(), router, events,
                           VoiceMetadataStore(tmp_path / "voice.json"))
    operator.on_mission_finished = service.mission_finished
    return service, operator, approvals, dialog, calls, shown


async def wait_prompt(dialog):
    async with asyncio.timeout(2):
        while not dialog.pending:
            await asyncio.sleep(.005)


def test_voice_browser_permission_and_followup_flow(tmp_path):
    async def scenario():
        service, operator, approvals, dialog, calls, shown = build(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("open", "open browser", .99, True))
        first = service.history[-1]["mission_id"]
        task = asyncio.create_task(operator.run_once(first))
        await wait_prompt(dialog)
        assert calls == [] and "browser.open" in shown[-1]
        assert service.snapshot()["assistant_question"] == shown[-1]
        await service.process_turn(VoiceTurn("partial", "yes continue", .99, False))
        await service.process_turn(VoiceTurn("unclear", "yes continue", .1, True))
        assert calls == [] and approvals.pending()
        approval = VoiceTurn("consent", "Yeah, continue!", .99, True)
        await service.process_turn(approval)
        await service.process_turn(approval)
        assert (await task).status is MissionStatus.COMPLETED
        assert len(calls) == 1 and "open in the browser" in shown[-1]
        assert PermissionGrantStore(tmp_path / "grants.json").allows("browser.open", "browser.navigate")
        assert not PermissionGrantStore(tmp_path / "grants.json").allows("browser.navigate", "browser.navigate")

        await service.process_turn(VoiceTurn("site", "YouTube", .99, True))
        task = asyncio.create_task(operator.run_once(service.history[-1]["mission_id"]))
        await wait_prompt(dialog)
        await service.process_turn(VoiceTurn("site-consent", "yes", .99, True))
        assert (await task).status is MissionStatus.COMPLETED
        assert "YouTube" in shown[-1] and len(calls) == 2
        await service.process_turn(VoiceTurn("search", "search for cats", .99, True))
        task = asyncio.create_task(operator.run_once(service.history[-1]["mission_id"]))
        await wait_prompt(dialog)
        await service.process_turn(VoiceTurn("search-consent", "allow once", .99, True))
        assert (await task).status is MissionStatus.COMPLETED
        assert calls[-1] == ("youtube.search", {"query": "cats"})
        assert not PermissionGrantStore(tmp_path / "grants.json").allows("youtube.search", "browser.navigate")

        await service.process_turn(VoiceTurn("again", "open browser", .99, True))
        assert (await operator.run_once(service.history[-1]["mission_id"])).status is MissionStatus.COMPLETED
        assert not approvals.pending() and len(calls) == 4
        await service.stop()
    asyncio.run(scenario())


def test_external_voice_profile_permissions_playback_and_native_form_continue_in_one_window(tmp_path, monkeypatch):
    from app.agents.runtime_tools import register_runtime_tools
    from app.browser.external_client import ExternalBrowserClient
    from app.computer.ocr import OcrReader
    from tests.test_external_browser_client import ForbiddenManagedBrowser
    from tests.test_external_gmail import _inventory
    from tests.test_native_web import ProfileWebDesktop, transport

    monkeypatch.setattr(OcrReader, "read_bytes", lambda *_: "Visible YouTube screen text")

    async def scenario():
        desktop = ProfileWebDesktop()
        native = transport(desktop)
        client = ExternalBrowserClient(tmp_path, discover=lambda **_: _inventory(tmp_path),
                                       transport_factory=lambda: native)
        registry = ToolRegistry()
        register_runtime_tools(registry, ForbiddenManagedBrowser(), tmp_path, external_browser=client)
        service, operator, approvals, dialog, _, shown = build(tmp_path, registry)
        service.router.assistant.external_browser = client
        await service.start()
        consent_count = 0

        async def finish(mission_id):
            nonlocal consent_count
            task = asyncio.create_task(operator.run_once(mission_id))
            async with asyncio.timeout(10):
                while not task.done():
                    if dialog.pending:
                        consent_count += 1
                        await service.process_turn(VoiceTurn(
                            f"native-consent-{consent_count}", "yes continue", .99, True))
                    await asyncio.sleep(.005)
                result = await task
                assert result.status is MissionStatus.COMPLETED, result.checkpoint
                return result

        await service.process_turn(VoiceTurn("open-native", "open YouTube", .99, True))
        assert "Which browser profile" in shown[-1]
        assert not any(row[0] == "spawn" for row in desktop.trace)
        await service.process_turn(VoiceTurn("choose-native", "one", .99, True))
        opened = await finish(service.history[-1]["mission_id"])
        assert opened.checkpoint["browser_observation"]["backend"] == "native"
        assert consent_count == 3  # Profile, navigation, and browser/screen reading.
        desktop.nodes.append(dict(id=8, parent=2, runtime_id="8.8", name="Funny cats 1000 views 2 minutes",
            type="ControlType.Hyperlink", rect=[20, 250, 250, 40], enabled=True, offscreen=False))

        await service.process_turn(VoiceTurn("native-play", "play video", .99, True))
        await finish(service.history[-1]["mission_id"])
        played = await finish(service.session.active_mission)
        assert played.checkpoint["browser_observation"]["url"].endswith("watch?v=selected-cat")
        assert desktop.nodes[4]["name"] == "Pause (k)"
        assert consent_count == 4

        fields = {"target": "5.5", "text": None, "key": None, "direction": None, "amount": None}
        service.router.assistant.provider = FakeBrowserLlm([json.dumps({
            "action": "execute", "goal": "Type cats in the visible search field and submit",
            "sequence": [
                {"function": "browser.external_action", "arguments": {**fields, "action": "type", "text": "cats"}},
                {"function": "browser.external_action", "arguments": {**fields, "action": "press", "key": "enter"}},
            ],
        })])
        await service.process_turn(VoiceTurn("native-form", "Type cats into the search field and submit", .99, True))
        await finish(service.history[-1]["mission_id"])
        form = await finish(service.session.active_mission)
        assert desktop.nodes[5]["value"] == "cats"
        assert ("keys", 100, ("enter",)) in desktop.trace
        assert [step["function"] for step in form.checkpoint["function_sequence"]] == [
            "browser.external_action", "browser.observe", "browser.external_action", "browser.observe"]
        assert consent_count == 6  # General native input remains approved per action.
        assert len([row for row in desktop.trace if row[0] == "spawn"]) == 1
        assert not any(row[:3] == ("keys", 100, ("ctrl", "t")) for row in desktop.trace)
        assert len(client._windows) == 1 and not approvals.pending()
        assert "YouTube" in shown[-1]
        await service.stop()

    asyncio.run(scenario())


def test_no_or_voice_stop_never_runs_waiting_action(tmp_path):
    async def scenario():
        service, operator, approvals, dialog, calls, _ = build(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("open", "open browser", .99, True))
        task = asyncio.create_task(operator.run_once(service.history[-1]["mission_id"]))
        await wait_prompt(dialog)
        await service.process_turn(VoiceTurn("no", "no", .99, True))
        assert (await task).status is not MissionStatus.COMPLETED
        assert not calls and not dialog.pending
        await service.process_turn(VoiceTurn("again", "open browser", .99, True))
        task = asyncio.create_task(operator.run_once(service.history[-1]["mission_id"]))
        await wait_prompt(dialog)
        await service.stop()
        await service.process_turn(VoiceTurn("late", "yes continue", .99, True))
        await task
        assert not calls and not approvals.pending()
    asyncio.run(scenario())


def test_queued_reply_cannot_approve_a_different_request_and_timeout_clears_overlay(tmp_path):
    async def scenario():
        service, _, approvals, dialog, _, _ = build(tmp_path)
        await service.start()
        approvals.timeout_seconds = .15
        first = ComputerAction("browser.open", {}, "a", "mission:one", "Open browser", "browser.navigate")
        second = ComputerAction("browser.navigate", {"url": "https://www.youtube.com"}, "b", "mission:two",
                                "Open YouTube", "browser.navigate")
        tasks = [asyncio.create_task(approvals.request(item)) for item in (first, second)]
        await wait_prompt(dialog)
        first_id = dialog.request_id
        dialog.respond("yes", allow_execution=True, confidence=1, minimum_confidence=.75, request_id=first_id)
        await wait_prompt(dialog)
        dialog.respond("yes", allow_execution=True, confidence=1, minimum_confidence=.75, request_id=first_id)
        assert approvals.store.get(second.action_id).status is ApprovalStatus.PENDING
        assert await asyncio.gather(*tasks) == [True, False]
        assert not dialog.pending and service.snapshot()["assistant_question"] is None
        await service.stop()
    asyncio.run(scenario())


def test_spoken_stop_cancels_permission_without_reopening_followup(tmp_path):
    async def scenario():
        service, operator, approvals, dialog, calls, _ = build(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("open", "open browser", .99, True))
        mission_id = service.history[-1]["mission_id"]
        task = asyncio.create_task(operator.run_once(mission_id))
        await wait_prompt(dialog)
        await service.process_turn(VoiceTurn("stop", "stop everything", .99, True))
        assert (await task).status is MissionStatus.PAUSED
        assert operator.store.load(mission_id).status is MissionStatus.PAUSED
        assert not calls and not approvals.pending() and not service.router.current_question
        await service.stop()
    asyncio.run(scenario())


def test_saved_voice_permission_is_reused_after_restart(tmp_path):
    async def scenario():
        service, operator, _, dialog, _, _ = build(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("open", "open browser", .99, True))
        task = asyncio.create_task(operator.run_once(service.history[-1]["mission_id"]))
        await wait_prompt(dialog)
        await service.process_turn(VoiceTurn("yes", "yes continue", .99, True))
        await task
        await service.stop()
        service, operator, approvals, _, calls, shown = build(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("open-new-session", "open browser", .99, True))
        assert (await operator.run_once(service.history[-1]["mission_id"])).status is MissionStatus.COMPLETED
        assert len(calls) == 1 and not approvals.pending()
        assert not any("Allow browser.open" in question for question in shown if question)
        await service.stop()
    asyncio.run(scenario())


def test_dashboard_cancel_expires_displayed_request_and_preserves_cancelled_mission(tmp_path):
    async def scenario():
        service, operator, approvals, dialog, calls, _ = build(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("open", "open browser", .99, True))
        mission_id = service.history[-1]["mission_id"]
        task = asyncio.create_task(operator.run_once(mission_id))
        await wait_prompt(dialog)
        request_id = dialog.request_id
        runtime = DashboardRuntime(operator.store, operator.events, operator,
            approvals.manager, operator.runner.actions, approval_system=approvals, voice=service)
        gateway = RuntimeCommandGateway(runtime, "local-test-dashboard-token")
        await gateway.execute("local-test-dashboard-token", "cancel_mission", {"mission_id": mission_id})
        assert (await task).status is MissionStatus.CANCELLED
        assert approvals.store.get(request_id).status is ApprovalStatus.EXPIRED
        assert not calls and not dialog.pending
        await service.stop()
    asyncio.run(scenario())


def test_real_voice_mission_pipeline_observes_ocr_then_plays_in_same_youtube_tab(tmp_path, monkeypatch):
    from app.agents.runtime_tools import register_runtime_tools
    from app.browser.browser_manager import BrowserManager
    from app.computer.ocr import OcrReader
    from app.config.settings import BrowserSettings
    from tests.test_youtube_runtime_tool import FakeYouTubePage

    captured = []

    class ObservedPage(FakeYouTubePage):
        async def evaluate(self, _script):
            return {"visible_text": "Visible nature video", "elements": [],
                    "videos": [{"title": "Visible nature video", "url": "https://www.youtube.com/watch?v=visible-choice"}],
                    "player": {"present": "/watch" in self.url, "paused": not self.playing}}

        async def screenshot(self, **kwargs):
            assert kwargs["mask"]
            captured.append((self.url, self.playing))
            return b"viewport-image"

    class Context:
        def __init__(self):
            self.pages = []

        async def new_page(self):
            page = ObservedPage(result_href="/watch?v=visible-choice")
            page.url = "about:blank"
            self.pages.append(page)
            return page

    monkeypatch.setattr(OcrReader, "read_bytes", lambda self, image: "Visible nature video Play")

    async def scenario():
        browser = BrowserManager(BrowserSettings(), tmp_path)
        browser._context = Context()
        registry = ToolRegistry()
        register_runtime_tools(registry, browser, tmp_path)
        service, operator, approvals, dialog, _, shown = build(tmp_path, registry)
        await service.start()
        consent_count = 0

        async def finish(mission_id):
            nonlocal consent_count
            task = asyncio.create_task(operator.run_once(mission_id))
            async with asyncio.timeout(5):
                while not task.done():
                    if dialog.pending:
                        consent_count += 1
                        await service.process_turn(VoiceTurn(
                            f"approval-{consent_count}", "yes continue", .99, True))
                    await asyncio.sleep(.005)
                completed = await task
                assert completed.status is MissionStatus.COMPLETED, completed.checkpoint
                return completed

        await service.process_turn(VoiceTurn("open", "open YouTube", .99, True))
        opened = await finish(service.history[-1]["mission_id"])
        page = browser.current_user_page()
        tab_id = browser.tab_id_for(page)
        assert len(browser._context.pages) == 1
        assert opened.checkpoint["browser_observation"]["ocr_text"] == "Visible nature video Play"
        assert "YouTube" in shown[-1]
        assert len(captured) == 1

        await service.process_turn(VoiceTurn("play", "play video", .99, True))
        observing_id = service.history[-1]["mission_id"]
        observing = await finish(observing_id)
        assert observing.checkpoint["function_sequence"] == [{"function": "browser.observe", "arguments": {}}]
        assert not page.playing and len(captured) == 2
        action_id = service.session.active_mission
        assert action_id != observing_id
        played = await finish(action_id)
        assert page.playing and page.clicked_result
        assert len(browser._context.pages) == 1 and browser.current_user_page() is page
        assert browser.tab_id_for(page) == tab_id
        assert page.navigations == ["https://www.youtube.com/"]
        assert len(captured) == 3 and captured[-1][1] is True
        assert played.checkpoint["browser_observation"]["tab_id"] == tab_id
        assert consent_count == 3  # Navigate, screen observation, playback: one prompt each.
        assert not approvals.pending()
        await service.stop()

    asyncio.run(scenario())
