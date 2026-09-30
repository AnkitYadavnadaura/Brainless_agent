"""Collect one spoken request across ASR turns before requesting execution."""
import asyncio
from dataclasses import replace
import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.autonomy.models import ComputerAction
from app.voice.config import VoiceConfig
from app.voice.models import VoiceTurn
from app.voice.service import AssemblyAIStreamingTransport
from tests.test_voice import runtime
from tests.test_voice_permissions import build as permission_runtime


def collecting_runtime(tmp_path):
    service, transport, missions, events, manager, actions, operator = runtime(tmp_path)
    service.config = replace(service.config, collect_tasks=True, task_pause_seconds=.01)
    return service, transport, missions, events, manager, actions, operator


async def finish_question(service):
    await asyncio.sleep(.015)
    await service._check_request_pause()
    state = service.snapshot()
    assert state["request_collection"]["awaiting_finish"]
    assert "anything else" in state["assistant_question"].casefold()


class Assistant:
    accepting_new_task = True
    awaiting_clarification = False
    current_question = None
    clarification_timeout_seconds = 120

    def __init__(self):
        self.calls, self.questions = [], []

    def show_question(self, question):
        self.questions.append(question)

    def dismiss_question(self):
        self.questions.append(None)

    def reset(self):
        self.current_question, self.awaiting_clarification = None, False
        self.accepting_new_task = True

    async def handle(self, text, **options):
        self.calls.append((text, options))
        return {"status": "completed" if options.get("allow_execution", True) else "waiting",
                "mission_id": None, "result": "Handled combined request"}


def test_separate_final_turns_form_one_request_only_after_spoken_completion(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("one", "Open the browser", .98, True))
        await service.process_turn(VoiceTurn("two", "and search YouTube for piano lessons", .96, True))
        assert not missions.all() and service.history == []
        assert service.snapshot()["request_collection"]["part_count"] == 2
        await finish_question(service)
        assert not missions.all()
        await service.process_turn(VoiceTurn("finish", "no", .99, True))
        assert len(missions.all()) == len(service.history) == 1
        goal = missions.all()[0].goal
        assert "Open the browser" in goal and "search YouTube for piano lessons" in goal
        assert goal.index("Open the browser") < goal.index("search YouTube")
        assert not goal.casefold().rstrip().endswith("no")
        assert not service.snapshot()["request_collection"]["active"]
        await service.stop()
    asyncio.run(scenario())


def test_partial_and_duplicate_asr_turns_do_not_duplicate_collected_text(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("one", "Open", .99, False))
        assert not service.snapshot()["request_collection"]["active"]
        final = VoiceTurn("one", "Open Gmail", .98, True)
        await service.process_turn(final)
        await service.process_turn(final)
        await service.process_turn(VoiceTurn("two", "and then", .99, False))
        await service._check_request_pause()
        assert not service.snapshot()["request_collection"]["awaiting_finish"]
        assert not missions.all() and not service.history
        await service.process_turn(VoiceTurn("two", "read the subject lines", .97, True))
        await finish_question(service)
        finish = VoiceTurn("finish", "no", .99, True)
        await asyncio.gather(service.process_turn(finish), service.process_turn(finish))
        assert len(missions.all()) == 1
        assert missions.all()[0].goal.count("Open Gmail") == 1
        assert "and then" not in missions.all()[0].goal
        assert missions.all()[0].goal.count("read the subject lines") == 1
        await service.stop()
    asyncio.run(scenario())


def test_yes_and_more_details_extend_request_without_becoming_commands(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("one", "Open YouTube", .99, True))
        await finish_question(service)
        await service.process_turn(VoiceTurn("yes", "yes", .99, True))
        assert not missions.all()
        await service.process_turn(VoiceTurn("two", "search for quiet jazz", .99, True))
        await finish_question(service)
        await service.process_turn(VoiceTurn("three", "and choose a video under ten minutes", .99, True))
        await finish_question(service)
        await service.process_turn(VoiceTurn("done", "no", .99, True))
        assert len(missions.all()) == 1
        goal = missions.all()[0].goal
        assert "Open YouTube" in goal and "quiet jazz" in goal and "under ten minutes" in goal
        assert "yes" not in goal.casefold()
        await service.stop()
    asyncio.run(scenario())


@pytest.mark.parametrize("phrase", ["No.", "No thanks", "That's all", "Nothing else", "No, go ahead"])
def test_explicit_completion_phrases_commit_only_the_collected_request(tmp_path, phrase):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("one", "Open Calculator", .99, True))
        await finish_question(service)
        await service.process_turn(VoiceTurn("finish", phrase, .99, True))
        assert len(missions.all()) == 1 and missions.all()[0].goal.strip() == "Open Calculator"
        await service.stop()
    asyncio.run(scenario())


def test_negative_word_inside_additional_instruction_does_not_commit_early(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("one", "Open YouTube", .99, True))
        await finish_question(service)
        await service.process_turn(VoiceTurn("detail", "No ads if possible, choose a short video", .99, True))
        assert not missions.all() and service.snapshot()["request_collection"]["part_count"] == 2
        await finish_question(service)
        await service.process_turn(VoiceTurn("finish", "no", .99, True))
        assert "choose a short video" in missions.all()[0].goal
        await service.stop()
    asyncio.run(scenario())


def test_low_confidence_or_partial_completion_cannot_submit_a_request(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("one", "Open browser", .99, True))
        await finish_question(service)
        await service.process_turn(VoiceTurn("partial-finish", "no", .99, False))
        await service.process_turn(VoiceTurn("uncertain-finish", "no", .1, True))
        assert not missions.all()
        assert service.snapshot()["request_collection"]["active"]
        await finish_question(service)
        await service.process_turn(VoiceTurn("finish", "no", .99, True))
        assert len(missions.all()) == 1
        await service.stop()
    asyncio.run(scenario())


def test_uncertain_task_part_requires_a_clear_repeat_before_completion(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        assistant = Assistant()
        service.router.assistant = assistant
        await service.start()
        await service.process_turn(VoiceTurn("good", "Open the browser", .99, True))
        await service.process_turn(VoiceTurn("low", "an unclear destination", .3, True))
        await service.process_turn(VoiceTurn("finish", "no", .99, True))
        assert not missions.all() and not assistant.calls
        assert "repeat" in service.snapshot()["assistant_question"].casefold()
        await service.process_turn(VoiceTurn("repeat", "and open Gmail", .99, True))
        await finish_question(service)
        await service.process_turn(VoiceTurn("finish-again", "no", .99, True))
        assert len(assistant.calls) == 1
        combined, options = assistant.calls[0]
        assert "Open the browser" in combined and "and open Gmail" in combined
        assert "unclear destination" not in combined and options["allow_execution"] is True
        await service.stop()
    asyncio.run(scenario())


def test_next_request_excludes_previously_submitted_parts(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        for index, task in enumerate(("Open YouTube", "Open Gmail")):
            await service.process_turn(VoiceTurn(f"task-{index}", task, .99, True))
            await finish_question(service)
            await service.process_turn(VoiceTurn(f"finish-{index}", "no", .99, True))
        goals = [mission.goal for mission in missions.all()]
        assert len(goals) == 2 and set(goals) == {"Open YouTube", "Open Gmail"}
        await service.stop()
    asyncio.run(scenario())


def test_completion_before_pause_prompt_requires_contextual_confirmation(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("task", "Open Gmail", .99, True))
        await service.process_turn(VoiceTurn("early", "no", .99, True))
        assert not missions.all()
        assert "anything else" in service.snapshot()["assistant_question"].casefold()
        await service.process_turn(VoiceTurn("confirmed", "no", .99, True))
        assert len(missions.all()) == 1 and missions.all()[0].goal == "Open Gmail"
        await service.stop()
    asyncio.run(scenario())


def test_concurrent_completion_replies_cannot_submit_consumed_request_twice(tmp_path):
    async def scenario():
        service, _, _, *_ = collecting_runtime(tmp_path)
        entered, release = asyncio.Event(), asyncio.Event()

        class SlowAssistant(Assistant):
            async def handle(self, text, **options):
                entered.set()
                await release.wait()
                return await super().handle(text, **options)

        assistant = SlowAssistant()
        service.router.assistant = assistant
        await service.start()
        await service.process_turn(VoiceTurn("task", "Open Gmail", .99, True))
        await finish_question(service)
        first = asyncio.create_task(service.process_turn(VoiceTurn("done-1", "no", .99, True)))
        async with asyncio.timeout(1):
            await entered.wait()
        second = asyncio.create_task(service.process_turn(VoiceTurn("done-2", "no", .99, True)))
        await asyncio.sleep(0)
        release.set()
        await asyncio.gather(first, second)
        assert len(assistant.calls) == 1 and assistant.calls[0][0] == "Open Gmail"
        assert not service.snapshot()["request_collection"]["active"]
        await service.stop()
    asyncio.run(scenario())


@pytest.mark.parametrize("phrase", ["stop", "pause", "what is running"])
def test_deterministic_controls_bypass_request_collection(tmp_path, phrase):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("control", phrase, .99, True))
        assert not missions.all() and not service.snapshot()["request_collection"]["active"]
        assert len(service.history) == 1
        assert service.history[0]["intent"] != "execute_task"
        await service.stop()
    asyncio.run(scenario())


def test_assistant_clarification_replies_bypass_request_collection(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        assistant = Assistant()
        assistant.accepting_new_task = False
        assistant.awaiting_clarification = True
        assistant.current_question = "Which website?"
        service.router.assistant = assistant
        await service.start()
        await service.process_turn(VoiceTurn("reply", "Gmail", .99, True))
        assert assistant.calls[0][0] == "Gmail"
        assert not service.snapshot()["request_collection"]["active"] and not missions.all()
        await service.stop()
    asyncio.run(scenario())


@pytest.mark.parametrize("answer,approved", [("yes continue", True), ("no", False)])
def test_spoken_permission_decisions_bypass_collection(tmp_path, answer, approved):
    async def scenario():
        service, _, approvals, dialog, _, _ = permission_runtime(tmp_path)
        service.config = replace(service.config, collect_tasks=True, task_pause_seconds=.01)
        await service.start()
        root = approvals.manager.list_agents()[0]
        action = ComputerAction("browser.open", {}, root.agent_id, "permission:task",
                                "Open the requested browser", "browser.navigate")
        request = asyncio.create_task(approvals.request(action))
        await asyncio.sleep(0)
        assert dialog.pending
        await service.process_turn(VoiceTurn("answer", answer, .99, True))
        assert await request is approved
        assert not service.snapshot()["request_collection"]["active"]
        await service.stop()
    asyncio.run(scenario())


def test_permission_reply_does_not_consume_prior_unsubmitted_task_parts(tmp_path):
    async def scenario():
        service, _, approvals, dialog, _, _ = permission_runtime(tmp_path)
        service.config = replace(service.config, collect_tasks=True, task_pause_seconds=.01)
        assistant = Assistant()
        service.router.assistant = assistant
        await service.start()
        await service.process_turn(VoiceTurn("task", "Open Gmail after this task", .99, True))
        await finish_question(service)
        root = approvals.manager.list_agents()[0]
        request = asyncio.create_task(approvals.request(ComputerAction("browser.open", {}, root.agent_id,
            "permission:task", "Open browser", "browser.navigate")))
        await asyncio.sleep(0)
        await service.process_turn(VoiceTurn("deny", "no", .99, True))
        assert await request is False
        assert assistant.calls == [] and service.snapshot()["request_collection"]["part_count"] == 1
        await finish_question(service)
        await service.process_turn(VoiceTurn("finish", "no", .99, True))
        assert len(assistant.calls) == 1 and assistant.calls[0][0] == "Open Gmail after this task"
        await service.stop()
    asyncio.run(scenario())


@pytest.mark.parametrize("lifecycle", ["stop_start", "pause_resume"])
def test_old_collection_timers_and_asr_ids_do_not_leak_into_reconnected_session(tmp_path, lifecycle):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("0", "Old unsubmitted task", .99, True))
        if lifecycle == "stop_start":
            await service.stop()
            await service.start()
        else:
            await service.pause()
            await service.resume()
        await asyncio.sleep(.02)
        await service._check_request_pause()
        assert not service.snapshot()["request_collection"]["active"]
        assert service.snapshot()["assistant_question"] is None and not missions.all()
        await service.process_turn(VoiceTurn("0", "New request after reconnect", .99, True))
        await finish_question(service)
        await service.process_turn(VoiceTurn("1", "no", .99, True))
        assert len(missions.all()) == 1 and missions.all()[0].goal == "New request after reconnect"
        await service.stop()
    asyncio.run(scenario())


def test_silence_never_submits_buffer_and_stop_discards_it(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("one", "Open a browser", .99, True))
        await finish_question(service)
        await asyncio.sleep(.05)
        await service._check_request_pause()
        assert not missions.all() and service.history == []
        await service.stop()
        await service._check_request_pause()
        assert not missions.all() and not service.snapshot()["request_collection"]["active"]
    asyncio.run(scenario())


def test_unsubmitted_task_transcripts_are_not_persisted_by_default(tmp_path):
    async def scenario():
        service, _, missions, events, *_ = collecting_runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("one", "Open private.example and review my draft", .99, True))
        await finish_question(service)
        assert not missions.all()
        assert all("private.example" not in str(event.detail) for event in events.replay())
        await service.stop()
        assert "private.example" not in (tmp_path / "voice.json").read_text()
    asyncio.run(scenario())


@pytest.mark.parametrize("confidence,expected", [(0.0, 0.0), (.4, .4), (None, 0.0)])
def test_streaming_sdk_preserves_explicit_zero_confidence(monkeypatch, confidence, expected):
    module = ModuleType("assemblyai.streaming.v3")

    class Client:
        def __init__(self, _options): self.handlers = {}
        def on(self, event, handler): self.handlers[event] = handler
        def connect(self, _parameters): return SimpleNamespace(id="fake-session")
        def disconnect(self, **_): pass

    module.StreamingClient = Client
    module.StreamingClientOptions = lambda **kwargs: kwargs
    module.StreamingParameters = lambda **kwargs: kwargs
    module.StreamingEvents = SimpleNamespace(Turn="turn", Error="error")
    monkeypatch.setitem(sys.modules, "assemblyai.streaming.v3", module)

    async def scenario():
        received = []
        transport = AssemblyAIStreamingTransport(VoiceConfig("key"))
        await transport.connect(received.append, lambda error: pytest.fail(error))
        transport.client.handlers["turn"](SimpleNamespace(turn_order=1, transcript="no",
            end_of_turn_confidence=confidence, end_of_turn=True))
        assert received[0].confidence == expected
        await transport.disconnect()
    asyncio.run(scenario())


@pytest.mark.parametrize("stop_kind", ["service_stop", "spoken_stop"])
def test_stop_during_model_reasoning_prevents_late_task_submission(tmp_path, stop_kind):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        entered, release = asyncio.Event(), asyncio.Event()

        class SlowAssistant(Assistant):
            async def handle(self, text, **options):
                entered.set()
                await release.wait()
                return await super().handle(text, **options)

        assistant = SlowAssistant()
        service.router.assistant = assistant
        await service.start()
        await service.process_turn(VoiceTurn("task", "Open Gmail", .99, True))
        await finish_question(service)
        processing = asyncio.create_task(service.process_turn(VoiceTurn("finish", "no", .99, True)))
        async with asyncio.timeout(1):
            await entered.wait()
        if stop_kind == "service_stop":
            await service.stop()
        else:
            await service.process_turn(VoiceTurn("stop", "stop", .99, True))
        release.set()
        result = await asyncio.gather(processing, return_exceptions=True)
        assert isinstance(result[0], asyncio.CancelledError)
        assert not assistant.calls and not missions.all()
        assert not service.snapshot()["request_collection"]["active"]
        assert all(row["transcript_id"] != "finish" for row in service.history)
        await service.stop()
    asyncio.run(scenario())


def test_failed_planning_retains_exact_unsubmitted_parts_for_explicit_retry(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)

        class RetryAssistant(Assistant):
            async def handle(self, text, **options):
                result = await super().handle(text, **options)
                if len(self.calls) == 1:
                    result.update(status="failed", result="Planning provider unavailable")
                return result

        assistant = RetryAssistant()
        service.router.assistant = assistant
        await service.start()
        await service.process_turn(VoiceTurn("one", "Open Gmail", .98, True))
        await service.process_turn(VoiceTurn("two", "and read the latest subject", .97, True))
        await finish_question(service)
        await service.process_turn(VoiceTurn("finish", "no", .99, True))
        assert not missions.all() and len(assistant.calls) == 1
        assert service.snapshot()["request_collection"]["part_count"] == 2
        assert "try again" in service.snapshot()["assistant_question"].casefold()
        await service.process_turn(VoiceTurn("retry", "no", .99, True))
        assert len(assistant.calls) == 2 and assistant.calls[0][0] == assistant.calls[1][0]
        assert assistant.calls[1][0].count("Open Gmail") == 1
        assert not service.snapshot()["request_collection"]["active"]
        await service.stop()
    asyncio.run(scenario())


def test_queued_completion_cannot_confirm_details_added_after_it_was_spoken(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        await service.process_turn(VoiceTurn("task", "Open Gmail", .99, True))
        await finish_question(service)
        await service._turn_lock.acquire()
        addition = asyncio.create_task(service.process_turn(VoiceTurn("detail", "and read the subject lines", .99, True)))
        await asyncio.sleep(0)
        stale_finish = asyncio.create_task(service.process_turn(VoiceTurn("old-finish", "no", .99, True)))
        await asyncio.sleep(0)
        service._turn_lock.release()
        await asyncio.gather(addition, stale_finish)
        assert not missions.all() and service.snapshot()["request_collection"]["part_count"] == 2
        await finish_question(service)
        await service.process_turn(VoiceTurn("new-finish", "no", .99, True))
        assert len(missions.all()) == 1 and "subject lines" in missions.all()[0].goal
        await service.stop()
    asyncio.run(scenario())


def test_sdk_turn_already_queued_before_restart_cannot_enter_new_request(tmp_path, monkeypatch):
    async def scenario():
        service, transport, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        # The SDK has queued this coroutine, but it has not acquired its context yet.
        queued = []
        monkeypatch.setattr("app.voice.service.asyncio.run_coroutine_threadsafe",
                            lambda coroutine, loop: queued.append(coroutine))
        old_callback = transport.on_turn
        old_callback(VoiceTurn("0", "Old stream request", .99, True))
        await service.stop()
        await service.start()
        assert len(queued) == 1
        await queued.pop()
        await service._check_request_pause()
        assert not missions.all()
        assert not service.snapshot()["request_collection"]["active"]
        # An old connection must also stay inert if it delivers again after restart.
        old_callback(VoiceTurn("1", "Another stale request", .99, True))
        assert not queued
        assert not service.snapshot()["request_collection"]["active"]
        await service.stop()
    asyncio.run(scenario())


def test_delayed_old_stream_error_cannot_clear_new_session_draft(tmp_path):
    async def scenario():
        service, _, missions, *_ = collecting_runtime(tmp_path)
        await service.start()
        queued = []
        service._loop = SimpleNamespace(call_soon_threadsafe=lambda callback, *args: queued.append((callback, args)))
        service._on_error("Old streaming connection failed")
        await service.stop()
        await service.start()
        await service.process_turn(VoiceTurn("new", "New session task", .99, True))
        for callback, args in queued:
            callback(*args)
        assert service.health_check()
        assert service.snapshot()["request_collection"]["part_count"] == 1
        assert not missions.all()
        await service.stop()
    asyncio.run(scenario())
