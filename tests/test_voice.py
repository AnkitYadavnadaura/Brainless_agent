import asyncio
from dataclasses import replace
from time import monotonic
from types import SimpleNamespace

from app.agents.manager import AgentManager
from app.autonomy.controllers import FilesystemComputerController
from app.autonomy.events import AutonomousEventBus, EventType
from app.autonomy.executor import ActionRuntime
from app.autonomy.mission import Mission, MissionStatus, MissionStore
from app.autonomy.operator import AutonomousOperator
from app.autonomy.perception_service import PerceptionService
from app.dashboard.service import DashboardRuntime, DashboardService
from app.voice.config import VoiceConfig, VoiceMode
from app.voice.conversation import BrowserVoiceAssistant
from app.voice.intent import VoiceIntentEngine, VoiceIntentType
from app.voice.models import VoiceSessionStatus, VoiceTurn
from app.voice.service import VoiceRuntimeRouter, VoiceService
from app.voice.store import VoiceMetadataStore


class FakeStreamingTransport:
    def __init__(self, failures=0):
        self.failures, self.connects, self.connected = failures, 0, False
        self.on_turn = None

    async def connect(self, on_turn, on_error):
        self.connects += 1
        if self.connects <= self.failures: raise ConnectionError("network")
        self.connected, self.on_turn = True, on_turn
        return "assembly-session"

    async def stream_microphone(self): return None
    async def disconnect(self): self.connected = False
    def health_check(self): return self.connected


class FakeBrowserLlm:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []
        self.session_keys = []

    def use_conversation_session(self, key):
        self.session_keys.append(key)

    def prepare_conversation(self, prompt):
        self.prompt = prompt

    async def open(self): pass
    async def verify_page(self): pass
    async def start_conversation(self): pass
    async def send_prompt(self, prompt): self.prompts.append(prompt)
    async def wait_for_response(self, _timeout): pass
    async def extract_response(self): return next(self.responses)


def runtime(tmp_path, *, confidence=.75, store_transcripts=False, failures=0,
            mode=VoiceMode.PUSH_TO_TALK, collect_tasks=False):
    manager = AgentManager(); manager.create_root("Operator", "root", "supervise", set())
    controller = FilesystemComputerController(tmp_path); actions = ActionRuntime(manager, controller)
    events = AutonomousEventBus(); missions = MissionStore(tmp_path / "missions.json")
    async def runner(_): return MissionStatus.COMPLETED
    operator = AutonomousOperator(missions, PerceptionService(controller, actions.world_state, events), events, runner)
    config = VoiceConfig("key", min_confidence=confidence, store_transcripts=store_transcripts,
                         reconnect_limit=3, mode=mode, collect_tasks=collect_tasks)
    transport = FakeStreamingTransport(failures)
    service = VoiceService(config, transport, VoiceRuntimeRouter(operator, missions), events,
                           VoiceMetadataStore(tmp_path / "voice.json"))
    return service, transport, missions, events, manager, actions, operator


def test_partial_turn_updates_ui_but_never_creates_mission(tmp_path):
    async def scenario():
        service, _, missions, events, *_ = runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("partial", "Open Chrome", .99, False))
        assert service.snapshot()["current_transcript"] == "Open Chrome"
        assert missions.all() == () and service.history == []
        assert events.replay()[-1].type is EventType.VOICE_PARTIAL
        assert "transcript" not in events.replay()[-1].detail
    asyncio.run(scenario())


def test_final_turn_creates_one_runtime_mission_and_dashboard_trace(tmp_path):
    async def scenario():
        service, _, missions, events, manager, actions, operator = runtime(tmp_path)
        await service.start()
        turn = VoiceTurn("final", "Open Chrome and search for AI news", .98, True)
        await service.process_turn(turn); await service.process_turn(turn)
        assert len(missions.all()) == 1 and missions.all()[0].owner == "voice"
        assert len(service.history) == 1
        dashboard = DashboardService(DashboardRuntime(missions, events, operator, manager, actions, voice=service)).snapshot()
        assert dashboard["voice"]["history"][0]["mission_id"] == missions.all()[0].mission_id
        assert events.replay()[-1].type is EventType.VOICE_COMMAND
    asyncio.run(scenario())


def test_restarted_voice_session_accepts_reused_assembly_turn_id(tmp_path):
    async def scenario():
        service, _, missions, _, manager, _, operator = runtime(tmp_path)
        browser_llm = FakeBrowserLlm([
            '{"template":"computer_operator"}',
            '{"action":"ask","question":"Which application should I open?"}',
            '{"action":"execute","goal":"Open Calculator","sequence":'
            '[{"function":"browser.navigate","arguments":{"url":"https://example.com"}}]}',
        ])
        service.router.assistant = BrowserVoiceAssistant(
            browser_llm, operator.create, lambda _: None, lambda: None,
            manager.tools,
        )
        await service.start()
        await service.process_turn(VoiceTurn("0", "Open it", .99, True))
        assert not missions.all()
        await service.stop()

        await service.start()
        await service.process_turn(VoiceTurn("0", "Calculator", .99, True))

        assert len(missions.all()) == 1
        assert missions.all()[0].goal == "Open Calculator"
        assert len(browser_llm.prompts) == 3
    asyncio.run(scenario())


def test_low_confidence_is_sent_for_clarification_and_sensitive_tasks_route_normally(tmp_path):
    async def scenario():
        service, _, missions, *_ = runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("low", "Open the drone", .4, True))
        assert missions.all() == () and service.history[-1]["status"] == "waiting"
        await service.process_turn(VoiceTurn("sensitive", "Delete the temporary test file", .99, True))
        assert len(missions.all()) == 1
        assert missions.all()[0].goal == "Delete the temporary test file"
    asyncio.run(scenario())


def test_connection_retries_cleanup_and_minimal_persistence(tmp_path):
    async def scenario():
        service, transport, *_ = runtime(tmp_path, failures=2)
        await service.start(); assert transport.connects == 3 and service.health_check()
        await service.process_turn(VoiceTurn("secret", "My password is hidden", .99, True))
        await service.stop(); assert not transport.connected
        stored = (tmp_path / "voice.json").read_text()
        assert "password" not in stored and "hidden" not in stored
    asyncio.run(scenario())


def test_every_finalized_transcript_routes_without_a_wake_phrase(tmp_path):
    async def scenario():
        service, _, missions, events, *_ = runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("no-wake", "Open Chrome", .99, True))
        assert len(missions.all()) == 1
        await service.process_turn(VoiceTurn("normal-task", "Open Calculator", .99, True))
        assert len(missions.all()) == 2
        assert service.snapshot()["activation"] == "all_finalized_transcripts"
        assert events.replay()[-1].type is EventType.VOICE_COMMAND
    asyncio.run(scenario())


def test_old_wake_phrase_is_now_ordinary_user_text(tmp_path):
    async def scenario():
        service, _, missions, *_ = runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("combined", "Hey Anant, open Chrome", .99, True))
        assert len(missions.all()) == 1
        assert missions.all()[0].goal == "Hey Anant, open Chrome"
    asyncio.run(scenario())


def test_partial_turn_is_ignored_and_low_confidence_final_is_processed_safely(tmp_path):
    async def scenario():
        service, _, missions, *_ = runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("partial", "Open Chrome", .99, False))
        assert service.history == []
        await service.process_turn(VoiceTurn("low", "Open Chrome", .4, True))
        assert missions.all() == ()
        assert service.history[-1]["status"] == "waiting"
    asyncio.run(scenario())


def test_hands_free_listener_survives_silence_until_session_limit(tmp_path):
    async def scenario():
        service, transport, *_ = runtime(tmp_path, mode=VoiceMode.SESSION)

        async def keep_microphone_open():
            await asyncio.Event().wait()

        transport.stream_microphone = keep_microphone_open
        await service.start()
        listener = asyncio.create_task(service.listen())
        await asyncio.sleep(service.config.idle_timeout + .05)
        assert transport.connected and not listener.done()
        listener.cancel()
        await asyncio.gather(listener, return_exceptions=True)
        await service.stop()
    asyncio.run(scenario())


def test_push_to_talk_listener_stays_connected_during_llm_processing(tmp_path):
    async def scenario():
        service, transport, *_ = runtime(tmp_path)

        async def keep_microphone_open():
            await asyncio.Event().wait()

        transport.stream_microphone = keep_microphone_open
        service.config = replace(service.config, idle_timeout=.01)
        await service.start()
        service.session.status = VoiceSessionStatus.PROCESSING
        service._last_activity = monotonic() - 1
        listener = asyncio.create_task(service.listen())
        await asyncio.sleep(.04)
        assert transport.connected and not listener.done()
        listener.cancel()
        await asyncio.gather(listener, return_exceptions=True)
        await service.stop()
    asyncio.run(scenario())


def test_push_to_talk_listener_keeps_clarification_reply_window_open(tmp_path):
    async def scenario():
        service, transport, *_ = runtime(tmp_path)

        async def keep_microphone_open():
            await asyncio.Event().wait()

        transport.stream_microphone = keep_microphone_open
        service.config = replace(service.config, idle_timeout=.01)
        service.router.assistant = SimpleNamespace(
            awaiting_clarification=True, clarification_timeout_seconds=.1)
        await service.start()
        service._last_activity = monotonic() - .04
        listener = asyncio.create_task(service.listen())
        await asyncio.sleep(.04)
        assert transport.connected and not listener.done()
        listener.cancel()
        await asyncio.gather(listener, return_exceptions=True)
        await service.stop()
    asyncio.run(scenario())


def test_interrupt_intents_have_deterministic_priority():
    engine = VoiceIntentEngine()
    assert engine.parse("Stop everything", 1).type is VoiceIntentType.EMERGENCY_STOP
    assert engine.parse("Pause", 1).type is VoiceIntentType.PAUSE
    assert engine.parse("What's running?", 1).type is VoiceIntentType.QUERY_STATUS


def test_voice_approval_fails_closed_without_independent_authorizer(tmp_path):
    async def scenario():
        service, *_ = runtime(tmp_path)
        result = await service.router.route(VoiceIntentEngine().parse("Approve", 1))
        assert result["status"] == "waiting"
        assert "authenticated dashboard" in result["result"]
    asyncio.run(scenario())


def test_voice_control_plane_reconnects_a_paused_session(tmp_path):
    from app.voice.controller import VoiceControlPlane
    async def scenario():
        service, transport, *_ = runtime(tmp_path)
        control = VoiceControlPlane(lambda _: service)
        control.configure("assembly-key-long-enough")
        await control.start()
        assert transport.connects == 1
        await service.pause()
        assert not control.health_check()
        await control.start()
        assert transport.connects == 2 and control.health_check()
        await control.stop()
    asyncio.run(scenario())


def test_voice_resume_transitions_paused_mission_and_emits_wakeup(tmp_path):
    async def scenario():
        service, _, missions, events, *_ = runtime(tmp_path)
        mission = Mission("continue safely", "voice", status=MissionStatus.PAUSED)
        missions.save(mission)
        result = await service.router.route(VoiceIntentEngine().parse("Resume", 1))
        assert result["status"] == "completed"
        assert missions.load(mission.mission_id).status is MissionStatus.WAITING
        assert events.replay()[-1].type is EventType.MISSION_TRIGGERED
    asyncio.run(scenario())


def test_browser_llm_clarifies_voice_request_and_accepts_spoken_replies(tmp_path):
    async def scenario():
        service, _, missions, events, manager, _, operator = runtime(tmp_path)
        overlay = []
        browser_llm = FakeBrowserLlm([
            '{"template":"computer_operator"}',
            '{"action":"ask","question":"Which platform should I use?"}',
            '{"action":"open_and_ask","platform":"Spotify","question":"What song or artist would you like?",'
            '"sequence":[{"function":"browser.navigate","arguments":{"url":"https://open.spotify.com"}}]}',
            '{"action":"execute","goal":"Play Take On Me by A-ha on Spotify","sequence":'
            '[{"function":"browser.navigate","arguments":{"url":"https://open.spotify.com/search/Take%20On%20Me"}}]}',
        ])
        assistant = BrowserVoiceAssistant(
            browser_llm, operator.create, overlay.append, lambda: overlay.append(None),
            manager.tools)
        service.router.assistant = assistant
        await service.start()

        await service.process_turn(VoiceTurn("request", "Play music", .99, True))
        assert not missions.all()
        assert assistant.current_question == "Which platform should I use?"
        assert service.snapshot()["assistant_question"] == "Which platform should I use?"
        assert events.replay()[-1].detail["result"] == "Which platform should I use?"
        assert "AVAILABLE_TEMPLATES" in browser_llm.prompts[0]
        assert "AVAILABLE_ACTION_CAPABILITIES" in browser_llm.prompts[0]
        assert "ACTION_CAPABILITIES_JSON" in browser_llm.prompts[1]
        assert "one short question" in browser_llm.prompts[1]
        assert '"function": "browser.navigate"' in browser_llm.prompts[1]
        assert "EXECUTION_CONFIDENCE_THRESHOLD: 0.750" in browser_llm.prompts[1]

        await service.process_turn(VoiceTurn("platform", "Spotify", .99, True))
        assert "AVAILABLE_TEMPLATES" not in browser_llm.prompts[2]
        assert '"text": "Spotify"' in browser_llm.prompts[2]
        assert len(missions.all()) == 1
        assert "Open Spotify in the browser" in missions.all()[0].goal
        assert "do not start playback" in missions.all()[0].goal
        assert missions.all()[0].checkpoint["function_sequence"] == [{
            "function": "browser.navigate",
            "arguments": {"url": "https://open.spotify.com"},
        }]
        assert missions.all()[0].checkpoint["prompt_template"] == "computer_operator"
        assert assistant.current_question is None
        opening_mission = missions.all()[0]
        opening_mission.status = MissionStatus.COMPLETED
        await assistant.mission_finished(opening_mission)
        assert assistant.current_question == "What song or artist would you like?"

        await service.process_turn(VoiceTurn("song", "Take On Me by A-ha", .99, True))
        assert len(missions.all()) == 2
        playback_mission = next(mission for mission in missions.all()
                                if mission.goal == "Play Take On Me by A-ha on Spotify")
        assert playback_mission.checkpoint["function_sequence"] == [{
            "function": "browser.navigate",
            "arguments": {"url": "https://open.spotify.com/search/Take%20On%20Me"},
        }]
        assert assistant.current_question is None
        assert service.snapshot()["assistant_question"] is None
        assert overlay == [
            "Which platform should I use?", None,
            "What song or artist would you like?", None,
        ]
        assert len(browser_llm.prompts) == 4
        assert len(browser_llm.session_keys) == 1
    asyncio.run(scenario())


def test_voice_assistant_keeps_followup_context_across_accepted_tasks(tmp_path):
    async def scenario():
        service, _, missions, _, manager, _, operator = runtime(tmp_path)
        from app.agents.tools import RiskLevel, ToolSpec
        from app.safety.permissions import Permission

        if not manager.tools.contains("browser.navigate"):
            manager.tools.register(ToolSpec(
                "browser.navigate", "Navigate browser", "Open a URL",
                frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.MEDIUM,
                lambda _: "opened", ("url",),
            ))
        manager.tools.register(ToolSpec(
            "youtube.control", "Control YouTube", "Control current playback",
            frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.MEDIUM,
            lambda _: "controlled", ("action", "seconds"), category="media",
        ))
        if not manager.tools.contains("youtube.play"):
            manager.tools.register(ToolSpec(
                "youtube.play", "Play YouTube", "Search and play a video",
                frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.MEDIUM,
                lambda _: "playing", ("query",), category="media",
            ))
        browser_llm = FakeBrowserLlm([
            '{"template":"computer_operator"}',
            '{"action":"execute","goal":"Pause the current YouTube video","sequence":'
            '[{"function":"youtube.control","arguments":{"action":"pause","seconds":0}}]}',
            '{"template":"computer_operator"}',
            '{"action":"execute","goal":"Play a different video","sequence":'
            '[{"function":"youtube.play","arguments":{"query":"requested song"}}]}',
        ])
        assistant = BrowserVoiceAssistant(
            browser_llm, operator.create, lambda _: None, lambda: None, manager.tools,
        )
        service.router.assistant = assistant
        await service.start()

        for transcript_id, command in (
            ("gmail", "Open Gmail"),
            ("pause", "Pause the YouTube video"),
            ("different-video", "Play another video"),
        ):
            await service.process_turn(VoiceTurn(transcript_id, command, .99, True))

        assert len(missions.all()) == 3
        assert len(browser_llm.session_keys) == 1
        assert '"text": "Open Gmail"' in browser_llm.prompts[3]
        assert "Mission " in browser_llm.prompts[3] and "submitted:" in browser_llm.prompts[3]
        assert '"function": "youtube.control"' in browser_llm.prompts[3]
        different_video = next(
            mission for mission in missions.all()
            if mission.goal == "Play a different video"
        )
        assert different_video.checkpoint["function_sequence"] == [{
            "function": "youtube.play", "arguments": {"query": "requested song"},
        }]
        assert assistant._turns[-1]["speaker"] == "assistant"
        assert "not yet been verified" in assistant._turns[-1]["text"]
        assert service.session.status.value == "listening"

    asyncio.run(scenario())


def test_voice_followup_history_rolls_over_without_ending_the_conversation(tmp_path):
    async def scenario():
        from app.agents.tools import RiskLevel, ToolRegistry, ToolSpec
        from app.safety.permissions import Permission

        registry = ToolRegistry()
        registry.register(ToolSpec(
            "browser.navigate", "Navigate browser", "Open a URL",
            frozenset({Permission.BROWSER_NAVIGATE.value}), RiskLevel.MEDIUM,
            lambda _: "opened", ("url",),
        ))
        responses = []
        for index in range(7):
            responses.extend([
                '{"template":"computer_operator"}',
                '{"action":"execute","goal":"Open page %d","sequence":'
                '[{"function":"browser.navigate","arguments":{"url":"https://example.com/%d"}}]}'
                % (index, index),
            ])
        browser_llm = FakeBrowserLlm(responses)
        submitted = []

        async def create_mission(mission):
            submitted.append(mission)

        assistant = BrowserVoiceAssistant(
            browser_llm, create_mission, lambda _: None, lambda: None, registry,
        )
        for index in range(7):
            result = await assistant.handle(f"Open page {index}")
            assert result["status"] == "accepted"

        assert len(submitted) == 7
        assert len(browser_llm.session_keys) == 2
        assert len(assistant._turns) <= assistant._MAX_TURNS
        assert "Open page 0" not in browser_llm.prompts[-1]
        assert "Open page 6" in browser_llm.prompts[-1]

    asyncio.run(scenario())


def test_browser_voice_response_parser_rejects_non_data_actions():
    from app.voice.conversation import VoiceConversationError
    import pytest

    with pytest.raises(VoiceConversationError, match="unsupported action"):
        BrowserVoiceAssistant.parse('{"action":"run_code","code":"unsafe"}')
    with pytest.raises(VoiceConversationError, match="valid JSON"):
        BrowserVoiceAssistant.parse("I will play music now")
    inventory = {"browser.navigate": {"arguments": ["url"]}}
    with pytest.raises(VoiceConversationError, match="unregistered function"):
        BrowserVoiceAssistant.parse(
            '{"action":"execute","goal":"browse","sequence":'
            '[{"function":"process.execute","arguments":{"command":["cmd"]}}]}',
            inventory,
        )
    with pytest.raises(VoiceConversationError, match="registered schema"):
        BrowserVoiceAssistant.parse(
            '{"action":"execute","goal":"browse","sequence":'
            '[{"function":"browser.navigate","arguments":{"url":"https://example.com","extra":true}}]}',
            inventory,
        )
    with pytest.raises(VoiceConversationError, match="must not contain secrets"):
        BrowserVoiceAssistant.parse(
            '{"action":"execute","goal":"browse","sequence":'
            '[{"function":"browser.navigate","arguments":{"url":"password=private"}}]}',
            inventory,
        )


    with pytest.raises(VoiceConversationError, match="unsupported control"):
        BrowserVoiceAssistant.parse('{"action":"control","command":"delete_everything"}')
    with pytest.raises(VoiceConversationError, match="duplicate JSON fields"):
        BrowserVoiceAssistant.parse(
            '{"action":"ask","question":"first","question":"second"}')


def test_malformed_browser_llm_plan_is_corrected_before_mission_creation(tmp_path):
    async def scenario():
        service, _, missions, _, manager, _, operator = runtime(tmp_path)
        from app.agents.tools import ToolRegistry
        from app.agents.runtime_tools import register_runtime_tools

        runtime_tools = ToolRegistry()
        register_runtime_tools(runtime_tools, None, tmp_path)
        manager.tools.register(runtime_tools.get("youtube.play"))
        browser_llm = FakeBrowserLlm([
            '{"template":"computer_operator"}',
            '{"action":"execute","goal":"Play Sayara\non YouTube","sequence":'
            '[{"function":"youtube.play","arguments":{"url":"[https://www.youtube.com",'
            '"query":"Sayara](https://www.youtube.com","query":%22Sayara/)"}}]}',
            '{"action":"execute","goal":"Play Sayara on YouTube","sequence":'
            '[{"function":"youtube.play","arguments":{"query":"Sayara"}}]}',
        ])
        service.router.assistant = BrowserVoiceAssistant(
            browser_llm, operator.create, lambda _: None, lambda: None,
            manager.tools,
        )
        await service.start()

        await service.process_turn(VoiceTurn(
            "youtube-request", "Find the song Sayara and start it on YouTube", .99, True))

        assert len(browser_llm.prompts) == 3
        assert "VALIDATION_ERROR:" in browser_llm.prompts[2]
        assert "INVALID_RESPONSE_JSON:" in browser_llm.prompts[2]
        assert service.history[-1]["status"] == "accepted"
        assert len(missions.all()) == 1
        assert missions.all()[0].checkpoint["function_sequence"] == [{
            "function": "youtube.play",
            "arguments": {"query": "Sayara"},
        }]

    asyncio.run(scenario())


def test_unrepairable_browser_llm_response_asks_user_without_executing(tmp_path):
    async def scenario():
        service, _, missions, _, manager, _, operator = runtime(tmp_path)
        browser_llm = FakeBrowserLlm([
            '{"template":"computer_operator"}',
            "not JSON",
            "still not JSON",
        ])
        service.router.assistant = BrowserVoiceAssistant(
            browser_llm, operator.create, lambda _: None, lambda: None,
            manager.tools,
        )
        await service.start()

        await service.process_turn(VoiceTurn(
            "unrepairable-request", "Play Sayara on YouTube", .99, True))

        assert not missions.all()
        assert service.history[-1]["status"] == "waiting"
        assert service.history[-1]["result"] == (
            "I couldn't safely read the task plan. Please repeat your request.")
        assert service.snapshot()["assistant_question"] == service.history[-1]["result"]

    asyncio.run(scenario())


def test_youtube_voice_function_uses_one_registered_query_argument(tmp_path):
    import pytest

    from app.agents.tools import ToolRegistry
    from app.agents.runtime_tools import register_runtime_tools

    async def scenario():
        registry = ToolRegistry()
        register_runtime_tools(registry, None, tmp_path)
        youtube = registry.get("youtube.play")

        assert youtube.input_schema == ("query",)
        with pytest.raises(ValueError, match="supported YouTube host"):
            await youtube.handler({"query": "https://example.com/video"})

    asyncio.run(scenario())


def test_unspecified_youtube_video_uses_recommendation_without_clarifying(tmp_path):
    async def scenario():
        service, _, missions, _, manager, _, operator = runtime(tmp_path)
        from app.agents.tools import ToolRegistry
        from app.agents.runtime_tools import register_runtime_tools

        registry = ToolRegistry()
        register_runtime_tools(registry, None, tmp_path)
        manager.tools.register(registry.get("youtube.play"))
        browser_llm = FakeBrowserLlm([
            '{"template":"computer_operator"}',
            '{"action":"ask","question":"Which YouTube video would you like to play?"}',
        ])
        service.router.assistant = BrowserVoiceAssistant(
            browser_llm, operator.create, lambda _: None, lambda: None, manager.tools)
        await service.start()

        await service.process_turn(VoiceTurn(
            "generic-youtube", "Play a YouTube video", .99, True))

        assert len(missions.all()) == 1
        assert len(browser_llm.prompts) == 0
        assert missions.all()[0].checkpoint["function_sequence"] == [{
            "function": "youtube.play", "arguments": {"query": "recommendation"},
        }]

    asyncio.run(scenario())


def test_generic_video_followup_uses_youtube_context_and_plays_recommendation(tmp_path):
    async def scenario():
        service, _, missions, _, manager, _, operator = runtime(tmp_path)
        from app.agents.tools import ToolRegistry
        from app.agents.runtime_tools import register_runtime_tools

        registry = ToolRegistry()
        register_runtime_tools(registry, None, tmp_path)
        manager.tools.register(registry.get("youtube.play"))
        browser_llm = FakeBrowserLlm([
            '{"template":"computer_operator"}',
            '{"action":"ask","question":"What would you like me to do with YouTube?"}',
            '{"action":"ask","question":"Which video should I play?"}',
        ])
        service.router.assistant = BrowserVoiceAssistant(
            browser_llm, operator.create, lambda _: None, lambda: None,
            manager.tools,
        )
        await service.start()

        await service.process_turn(VoiceTurn(
            "youtube-open", "Open YouTube in a browser", .99, True))
        opening_mission = missions.all()[0]
        assert opening_mission.checkpoint["function_sequence"] == [{
            "function": "browser.navigate", "arguments": {"url": "https://www.youtube.com/"},
        }]
        opening_mission.status = MissionStatus.COMPLETED
        await service.router.assistant.mission_finished(opening_mission)
        await service.process_turn(VoiceTurn(
            "youtube-followup", "Play any video", .99, True))

        assert service.history[-1]["status"] == "accepted"
        assert len(missions.all()) == 2
        playback_mission = next(mission for mission in missions.all()
                                if mission.mission_id != opening_mission.mission_id)
        assert playback_mission.checkpoint["function_sequence"] == [{
            "function": "youtube.play", "arguments": {"query": "recommendation"},
        }]

    asyncio.run(scenario())


def test_prompt_leader_routes_blender_work_to_creative_template(tmp_path):
    async def scenario():
        service, _, _, _, manager, _, operator = runtime(tmp_path)
        browser_llm = FakeBrowserLlm([
            '{"template":"creative_3d_operator"}',
            '{"action":"ask","question":"Should I build this as a Blender scene?"}',
        ])
        assistant = BrowserVoiceAssistant(
            browser_llm, operator.create, lambda _: None, lambda: None,
            manager.tools,
        )

        result = await assistant.handle("Create a low-poly spaceship in Blender")

        assert result["status"] == "waiting"
        assert result["prompt_template"] == "creative_3d_operator"
        assert "3D and game-engine task planner" in browser_llm.prompts[1]
        assert "ACTION_CAPABILITIES_JSON" in browser_llm.prompts[1]
        assert not service.router.missions.all()

    asyncio.run(scenario())


def test_pause_request_reaches_browser_llm_before_allowlisted_control(tmp_path):
    async def scenario():
        service, _, _, _, manager, _, operator = runtime(tmp_path)
        browser_llm = FakeBrowserLlm([
            '{"template":"computer_operator"}',
            '{"action":"control","command":"pause"}',
        ])
        service.router.assistant = BrowserVoiceAssistant(
            browser_llm, operator.create, lambda _: None, lambda: None,
            manager.tools,
        )
        await service.start()

        await service.process_turn(VoiceTurn("pause", "Pause", .99, True))

        assert len(browser_llm.prompts) == 2
        assert service.history[-1]["status"] == "completed"
        assert service.history[-1]["result"] == "Autonomous work paused"
        assert operator.takeover.mode.value == "takeover"

    asyncio.run(scenario())


def test_low_confidence_transcript_reaches_browser_llm_but_cannot_execute(tmp_path):
    async def scenario():
        service, _, missions, _, manager, _, operator = runtime(tmp_path)
        browser_llm = FakeBrowserLlm([
            '{"template":"computer_operator"}',
            '{"action":"execute","goal":"Open the calculator","sequence":'
            '[{"function":"browser.navigate","arguments":{"url":"https://example.com"}}]}',
        ])
        assistant = BrowserVoiceAssistant(
            browser_llm, operator.create, lambda _: None, lambda: None,
            manager.tools,
        )
        service.router.assistant = assistant
        await service.start()

        await service.process_turn(VoiceTurn("uncertain", "Open the calculator", .4, True))

        assert not missions.all()
        assert service.history[-1]["status"] == "waiting"
        assert "repeat" in service.history[-1]["result"].lower()
        assert len(browser_llm.prompts) == 2
        assert "ASR_CONFIDENCE: 0.400" in browser_llm.prompts[1]
        assert "EXECUTION_CONFIDENCE_THRESHOLD: 0.750" in browser_llm.prompts[1]

    asyncio.run(scenario())


def test_voice_tasks_fail_closed_when_browser_llm_is_not_configured(tmp_path):
    async def scenario():
        service, _, missions, *_ = runtime(tmp_path)
        service.router.require_assistant = True
        await service.start()
        await service.process_turn(VoiceTurn("wake-task", "Play music", .99, True))
        assert missions.all() == ()
        assert service.history[-1]["status"] == "failed"
        assert "browser LLM provider" in service.history[-1]["result"]
    asyncio.run(scenario())


def test_voice_service_suppresses_listening_while_working_on_task_and_accepts_controls_and_answers(tmp_path):
    async def scenario():
        service, _, missions, events, manager, _, operator = runtime(tmp_path)
        await service.start()

        mission = Mission("generate presentation", "voice", status=MissionStatus.RUNNING)
        missions.save(mission)
        service.session.active_mission = mission.mission_id

        assert service.is_working_on_task is True
        assert service.snapshot()["status"] == "executing"

        # Non-finalized turn is ignored while working on task
        await service.process_turn(VoiceTurn("part-1", "background chatter", .99, False))
        assert service.session.status is VoiceSessionStatus.EXECUTING
        assert not service._speech_in_progress

        # Non-control finalized utterance is ignored/suppressed
        initial_history_len = len(service.history)
        await service.process_turn(VoiceTurn("chat-1", "open calculator and do math", .99, True))
        assert len(service.history) == initial_history_len
        assert len(missions.all()) == 1

        # Immediate controls (e.g. pause / stop) are accepted immediately
        await service.process_turn(VoiceTurn("ctrl-pause", "pause", .99, True))
        assert missions.load(mission.mission_id).status is MissionStatus.PAUSED

        # Re-set to running
        mission.status = MissionStatus.RUNNING
        missions.save(mission)
        service.session.active_mission = mission.mission_id
        assert service.is_working_on_task is True

        # When a question is prompted / awaiting clarification, turns are listened to and processed
        async def mock_handle(text, **options):
            return {"status": "completed", "mission_id": None, "result": "Answer recorded"}

        service.router.assistant = SimpleNamespace(
            awaiting_clarification=True, clarification_timeout_seconds=120,
            current_question="Which slide?", handle=mock_handle, reset=lambda: None)
        service.session.status = VoiceSessionStatus.WAITING
        assert service.is_working_on_task is False
        assert service.snapshot()["status"] == "waiting"

        # Turn sent while awaiting clarification is processed, not ignored
        answer_turn = VoiceTurn("answer", "first slide", .99, True)
        await service.process_turn(answer_turn)
        assert service.session.last_final_transcript == "first slide"
        assert service.history[-1]["transcript"] == "first slide"

        await service.stop()

    asyncio.run(scenario())
