"""AssemblyAI Streaming v3 input service; finalized turns alone reach runtime routing."""
from __future__ import annotations
import asyncio
import logging
import re
from math import isfinite
from datetime import datetime, timezone
from time import monotonic
from typing import Awaitable, Callable, Protocol
from uuid import uuid4

from app.autonomy.events import AutonomousEvent, AutonomousEventBus, EventType
from app.autonomy.mission import Mission, MissionStatus
from app.voice.config import VoiceConfig, VoiceMode
from app.voice.intent import VoiceIntent, VoiceIntentEngine, VoiceIntentType
from app.voice.models import VoiceSession, VoiceSessionStatus, VoiceTurn
from app.voice.store import VoiceMetadataStore


TurnHandler = Callable[[VoiceTurn], None]
logger = logging.getLogger(__name__)


class StreamingTransport(Protocol):
    async def connect(self, on_turn: TurnHandler, on_error: Callable[[str], None]) -> str | None: ...
    async def stream_microphone(self) -> None: ...
    async def disconnect(self) -> None: ...
    def health_check(self) -> bool: ...


class AssemblyAIStreamingTransport:
    """Thin SDK adapter for wss://streaming.assemblyai.com/v3/ws."""
    def __init__(self, config: VoiceConfig) -> None:
        self.config, self.client, self._connected = config, None, False

    async def connect(self, on_turn: TurnHandler, on_error: Callable[[str], None]) -> str | None:
        from assemblyai.streaming.v3 import (StreamingClient, StreamingClientOptions,
                                              StreamingEvents, StreamingParameters)
        self.client = StreamingClient(StreamingClientOptions(api_key=self.config.api_key))
        def receive_turn(*args) -> None:
            turn = args[-1]
            confidence = getattr(turn, "end_of_turn_confidence", None)
            on_turn(VoiceTurn(str(getattr(turn, "turn_order", uuid4())),
                getattr(turn, "transcript", ""),
                float(confidence) if confidence is not None else 0.0,
                bool(getattr(turn, "end_of_turn", False))))
        self.client.on(StreamingEvents.Turn, receive_turn)
        self.client.on(StreamingEvents.Error, lambda *args: on_error(str(args[-1])))
        options = {"sample_rate": self.config.sample_rate, "speech_model": self.config.model,
                   "language_detection": not bool(self.config.language)}
        if self.config.language: options["language_code"] = self.config.language
        parameters = StreamingParameters(**options)
        connected = await asyncio.to_thread(self.client.connect, parameters)
        self._connected = True
        return str(getattr(connected, "id", "") or getattr(self.client, "session_id", "")) or None

    async def stream_microphone(self) -> None:
        from assemblyai.extras import MicrophoneStream
        if self.client is None: raise RuntimeError("AssemblyAI stream is not connected")
        microphone = MicrophoneStream(sample_rate=self.config.sample_rate)
        await asyncio.to_thread(self.client.stream, microphone)

    async def disconnect(self) -> None:
        try:
            if self.client is not None:
                await asyncio.to_thread(self.client.disconnect, terminate=True)
        finally:
            self._connected = False
            self.client = None

    def health_check(self) -> bool: return self._connected


class AssemblyAISpeechProvider(AssemblyAIStreamingTransport):
    """Named provider implementation; the legacy transport name remains compatible."""


class VoiceRuntimeRouter:
    """Maps structured voice intent only into existing runtime-owned services."""
    def __init__(self, operator, missions, approvals=None,
                 emergency_stop: Callable[[], Awaitable[None] | None] | None = None,
                 approval_authorizer: Callable[[VoiceIntent], Awaitable[bool] | bool] | None = None,
                 assistant=None, require_assistant: bool = False, permission_dialog=None) -> None:
        self.operator, self.missions, self.approvals, self.emergency_stop = operator, missions, approvals, emergency_stop
        self.approval_authorizer = approval_authorizer
        self.assistant, self.require_assistant = assistant, require_assistant
        self.permission_dialog = permission_dialog

    @property
    def awaiting_clarification(self) -> bool:
        return bool((self.permission_dialog and self.permission_dialog.pending)
                    or (self.assistant and self.assistant.awaiting_clarification))

    @property
    def current_question(self) -> str | None:
        if self.permission_dialog and self.permission_dialog.pending:
            return self.permission_dialog.current_question
        if not self.assistant or not self.assistant.awaiting_clarification:
            return None
        return self.assistant.current_question

    @property
    def clarification_timeout_seconds(self) -> float:
        if self.permission_dialog and self.permission_dialog.pending:
            return float(self.approvals.timeout_seconds)
        return float(getattr(self.assistant, "clarification_timeout_seconds", 0))

    async def route(self, intent: VoiceIntent, *, allow_execution: bool = True,
                    minimum_confidence: float = 0.75,
                    permission_request_id: str | None = None) -> dict[str, str | None]:
        stop_types = {VoiceIntentType.EMERGENCY_STOP, VoiceIntentType.STOP,
                      VoiceIntentType.PAUSE, VoiceIntentType.TAKEOVER}
        if self.permission_dialog:
            if intent.type in stop_types:
                self.permission_dialog.cancel_pending()
            else:
                answer = self.permission_dialog.respond(
                    intent.transcript, allow_execution=allow_execution,
                    confidence=intent.confidence, minimum_confidence=minimum_confidence,
                    request_id=permission_request_id)
                if answer is not None:
                    return answer
        is_control = intent.type not in {VoiceIntentType.EXECUTE_TASK,
                                        VoiceIntentType.CREATE_MISSION,
                                        VoiceIntentType.ASK_INFORMATION}
        if is_control and self.assistant and intent.type is not VoiceIntentType.QUERY_STATUS:
            self.assistant.reset()
        if intent.type in {VoiceIntentType.EXECUTE_TASK, VoiceIntentType.CREATE_MISSION,
                           VoiceIntentType.ASK_INFORMATION}:
            if self.assistant:
                try:
                    result = await self.assistant.handle(
                        intent.goal or intent.transcript,
                        confidence=intent.confidence,
                        minimum_confidence=minimum_confidence,
                        allow_execution=allow_execution,
                    )
                    control_types = {
                        "pause": VoiceIntentType.PAUSE,
                        "takeover": VoiceIntentType.TAKEOVER,
                        "resume": VoiceIntentType.RESUME,
                        "status": VoiceIntentType.QUERY_STATUS,
                    }
                    control = result.get("control")
                    if control is not None:
                        control_type = control_types.get(control)
                        if control_type is None:
                            raise ValueError("Browser LLM selected an unsupported voice control")
                        return await self.route(VoiceIntent(
                            control_type, control, None, confidence=intent.confidence))
                    return result
                except Exception:
                    logger.exception("Browser LLM voice reasoning failed")
                    self.assistant.reset()
                    return {"status": "failed", "mission_id": None,
                            "result": "I couldn't complete the voice request. "
                                      "Check mission history before retrying."}
            if self.require_assistant:
                return {"status": "failed", "mission_id": None,
                        "result": "Configure a browser LLM provider before using voice tasks."}
            if not allow_execution:
                return {"status": "waiting", "mission_id": None,
                        "result": "I didn't catch that clearly. Please repeat the request."}
            mission = Mission(intent.goal or intent.transcript, "voice")
            await self.operator.create(mission)
            return {"status": "accepted", "mission_id": mission.mission_id, "result": "Mission created"}
        if intent.type in {VoiceIntentType.EMERGENCY_STOP, VoiceIntentType.STOP, VoiceIntentType.PAUSE}:
            self.operator.takeover.begin()
            if self.emergency_stop:
                result = self.emergency_stop()
                if hasattr(result, "__await__"): await result
            else:
                for mission in self.missions.active():
                    mission.status = MissionStatus.PAUSED; mission.touch(); self.missions.save(mission)
            return {"status": "completed", "mission_id": None, "result": "Autonomous work paused"}
        if intent.type is VoiceIntentType.TAKEOVER:
            self.operator.takeover.begin()
            return {"status": "completed", "mission_id": None, "result": "User takeover enabled"}
        if intent.type is VoiceIntentType.RESUME:
            self.operator.takeover.resume()
            for mission in self.missions.active():
                if mission.status in {MissionStatus.PAUSED, MissionStatus.AWAITING_USER}:
                    mission.status = MissionStatus.WAITING
                    mission.touch()
                    self.missions.save(mission)
                    await self.operator.events.publish(AutonomousEvent(
                        EventType.MISSION_TRIGGERED, mission.mission_id,
                        {"source": "authorized_voice_resume"}))
            return {"status": "completed", "mission_id": None, "result": "Control returned to runtime"}
        if intent.type is VoiceIntentType.QUERY_STATUS:
            return {"status": "completed", "mission_id": None,
                    "result": f"{len(self.missions.active())} active missions"}
        if intent.type is VoiceIntentType.APPROVAL:
            if self.approval_authorizer is None:
                return {"status": "waiting", "mission_id": None,
                        "result": "Voice approval is disabled; use the authenticated dashboard"}
            authorized = self.approval_authorizer(intent)
            if hasattr(authorized, "__await__"): authorized = await authorized
            if not authorized:
                return {"status": "waiting", "mission_id": None,
                        "result": "Voice approval authorization failed"}
            pending = self.approvals.store.all() if self.approvals else ()
            pending = [item for item in pending if item.status.value == "pending"]
            if len(pending) != 1: return {"status": "waiting", "mission_id": None,
                                        "result": "Approval is ambiguous; use the dashboard"}
            from app.autonomy.approvals import ApprovalStatus
            decision = ApprovalStatus.APPROVED if intent.transcript.casefold().strip(" .!") == "approve" else ApprovalStatus.DENIED
            item = self.approvals.decide(pending[0].approval_id, decision, "voice_user")
            return {"status": "completed", "mission_id": item.mission_id, "result": decision.value}
        return {"status": "waiting", "mission_id": None, "result": "Command requires clarification"}


class VoiceService:
    def __init__(self, config: VoiceConfig, transport: StreamingTransport, router: VoiceRuntimeRouter,
                 events: AutonomousEventBus, store: VoiceMetadataStore, intent_engine: VoiceIntentEngine | None = None) -> None:
        config.validate()
        self.config, self.transport, self.router, self.events, self.store = config, transport, router, events, store
        self.intent_engine = intent_engine or VoiceIntentEngine()
        self.session: VoiceSession | None = None
        self.history: list[dict[str, object]] = list(store.all())[-config.context_limit:]
        self.reconnects = 0
        self._seen: set[str] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._last_activity = monotonic()
        self._turn_lock = asyncio.Lock()
        self._request_parts: list[VoiceTurn] = []
        self._request_question: str | None = None
        self._request_needs_repeat = False
        self._request_overflow = False
        self._request_generation = 0
        self._request_timer: asyncio.Task | None = None
        self._speech_in_progress = False
        self._processing_tasks: set[asyncio.Task] = set()
        self._stream_epoch = 0

    @property
    def is_working_on_task(self) -> bool:
        """True when a mission is actively executing and no question/clarification is pending."""
        if not self.session or not self.session.active_mission:
            return False
        if self.router.awaiting_clarification or self._request_active or self._request_question is not None:
            return False
        if self.router and self.router.missions:
            try:
                mission = self.router.missions.load(self.session.active_mission)
                if mission and mission.status is MissionStatus.RUNNING:
                    return True
            except Exception:
                pass
        return False

    @property
    def _request_active(self) -> bool:
        return bool(self._request_parts or self._request_needs_repeat or self._request_overflow)

    def _cancel_request_timer(self) -> None:
        timer, self._request_timer = self._request_timer, None
        if timer is not None and timer is not asyncio.current_task():
            timer.cancel()

    def _clear_request(self) -> None:
        self._cancel_request_timer()
        self._request_generation += 1
        self._request_parts.clear()
        self._request_question = None
        self._request_needs_repeat = self._request_overflow = False
        self._speech_in_progress = False

    def _invalidate_input(self) -> None:
        self._clear_request()
        current = asyncio.current_task()
        for task in tuple(self._processing_tasks):
            if task is not current:
                task.cancel()

    def _present_request(self, question: str | None = None, *, status: str | None = None) -> None:
        self._request_question = question
        dialog, assistant = self.router.permission_dialog, self.router.assistant
        if dialog:
            if question:
                dialog.show_conversation(question)
            else:
                dialog.dismiss_conversation()
                if status:
                    dialog.status(status)
        elif assistant:
            if question:
                assistant.show_question(question)
            else:
                assistant.dismiss_question()

    def _schedule_request_pause(self) -> None:
        self._cancel_request_timer()
        generation = self._request_generation
        async def prompt_after_pause():
            try:
                await asyncio.sleep(self.config.task_pause_seconds)
                if generation == self._request_generation:
                    await self._check_request_pause()
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("Could not present the complete-request question")
        self._request_timer = asyncio.create_task(prompt_after_pause(), name="voice-request-pause")

    async def _check_request_pause(self) -> None:
        async with self._turn_lock:
            if (not self.health_check() or not self._request_active or self._speech_in_progress
                    or self._request_question is not None
                    or monotonic() - self._last_activity < self.config.task_pause_seconds):
                return
            self._present_request("Is there anything else you want to add, or have you finished your input? Say yes and continue, or no when you're finished.")
            self.session.status = VoiceSessionStatus.WAITING
            self._last_activity = monotonic()
            await self.events.publish(AutonomousEvent(EventType.VOICE_SESSION, detail={
                "session_id": self.session.session_id, "status": "waiting", "request_collection": True}))

    @staticmethod
    def _request_reply(text: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s']", " ", text.casefold().replace("\u2019", "'"))).strip()

    _FINISHED_REPLIES = {"no", "no thanks", "no thank you", "no that's all", "no thats all", "that's all",
        "thats all", "that is all", "nothing else", "no nothing else", "no go ahead", "no continue",
        "no proceed", "i'm done", "i am done", "done", "finished", "finished input", "no more",
        "nothing more", "all done", "proceed", "go ahead", "nahi", "nahin", "aur nahi", "bas"}

    async def _collect_request(self, turn: VoiceTurn, reply_context: tuple[int, bool]):
        """Buffer only task speech; never treat task completion as tool consent."""
        text, reply = turn.transcript.strip(), self._request_reply(turn.transcript)
        confident = isfinite(turn.confidence) and turn.confidence >= self.config.min_confidence
        finished = reply in self._FINISHED_REPLIES
        question = None
        if not confident:
            if not finished:
                self._request_needs_repeat = True
            question = ("I didn't catch that clearly. Please repeat that part of your request."
                        if self._request_needs_repeat else "I didn't catch that clearly. Is there anything else you want to add?")
        elif reply in {"cancel request", "cancel this request", "discard that", "start over"}:
            self._clear_request()
            self._present_request(status="Request cleared. Tell me your new task.")
            return {"status": "waiting", "mission_id": None, "result": "Request cleared. Tell me your new task."}, None
        elif finished:
            if self._request_overflow:
                question = "That request is too long. Say 'start over' and give a shorter task."
            elif self._request_needs_repeat:
                question = "Please repeat the unclear part before I analyze the full request."
            elif (self._request_parts and self._request_question
                    and reply_context == (self._request_generation, True)):
                parts = tuple(self._request_parts)
                self._clear_request()  # Claim exactly once before any model/runtime await.
                self._present_request(status="Understanding your complete request...")
                return None, parts
            elif self._request_parts:
                question = "Is there anything else you want to add? Say no when you're finished."
            else:
                self._present_request(status="Listening. Tell me when you have a task.")
                return {"status": "waiting", "mission_id": None, "result": "Listening. Tell me when you have a task."}, None
        elif self._request_question and reply in {"yes", "yeah", "yep", "yes please", "haan", "han"}:
            self._request_generation += 1
            self._present_request(status="Go ahead. I'm listening to the rest of your request.")
            self._schedule_request_pause()
        elif len("\n".join(part.transcript for part in self._request_parts) + "\n" + text) > 2_000:
            self._request_overflow = True
            question = "That request is too long. Say 'start over' and give a shorter task."
        else:
            self._request_generation += 1
            self._request_parts.append(turn)
            self._request_needs_repeat = False
            self._present_request(status="I'm listening. Continue your request whenever you're ready.")
            self._schedule_request_pause()
        if question:
            self._cancel_request_timer()
            self._present_request(question)
        return {"status": "waiting", "mission_id": None,
                "result": question or "Listening to the rest of your request", "question": question}, None

    async def start(self, user_id: str = "local_user") -> VoiceSession:
        if self.session and self.session.status not in {VoiceSessionStatus.STOPPED, VoiceSessionStatus.ERROR} and self.transport.health_check():
            return self.session
        self.session = VoiceSession(user_id); self.session.status = VoiceSessionStatus.LISTENING
        self._clear_request()
        self._seen.clear()
        self._loop = asyncio.get_running_loop()
        try:
            self.session.assemblyai_session_id = await self._connect_with_backoff()
        except Exception:
            self.session.status = VoiceSessionStatus.ERROR
            self.session.connection_status = "disconnected"
            self.session.error_state = "AssemblyAI connection failed"
            raise
        self.session.connection_status = "connected"
        if self.router.permission_dialog:
            self.router.permission_dialog.start()
        await self.events.publish(AutonomousEvent(EventType.VOICE_SESSION, detail={"session_id": self.session.session_id, "status": "listening"}))
        return self.session

    async def listen(self) -> None:
        if not self.session: raise RuntimeError("Voice session is not started")
        stream = asyncio.create_task(self.transport.stream_microphone())
        started = monotonic()
        try:
            while not stream.done():
                await asyncio.sleep(min(1, self.config.idle_timeout))
                session_expired = monotonic() - started >= self.config.max_session_duration
                awaiting_clarification = self.router.awaiting_clarification or self._request_active
                processing_turn = (self.session.status is VoiceSessionStatus.PROCESSING
                                   or self.is_working_on_task)
                idle_timeout = max(
                    self.config.idle_timeout,
                    max(self.router.clarification_timeout_seconds, 120 if self._request_active else 0)
                    if awaiting_clarification else 0,
                )
                push_to_talk_idle = (
                    self.config.mode is VoiceMode.PUSH_TO_TALK
                    and not processing_turn
                    and monotonic() - self._last_activity >= self.config.idle_timeout
                    and monotonic() - self._last_activity >= idle_timeout
                )
                if session_expired or push_to_talk_idle:
                    await self.pause(); stream.cancel(); break
            results = await asyncio.gather(stream, return_exceptions=True)
            failure = next((item for item in results if isinstance(item, Exception)
                            and not isinstance(item, asyncio.CancelledError)), None)
            if failure and self.session:
                self.session.status = VoiceSessionStatus.ERROR
                self.session.error_state = "Microphone streaming error"
                await self.events.publish(AutonomousEvent(EventType.VOICE_SESSION,
                    detail={"session_id": self.session.session_id, "status": "error",
                            "error": type(failure).__name__}))
        finally:
            if not stream.done(): stream.cancel()

    async def stop(self) -> None:
        self._stream_epoch += 1
        self._invalidate_input()
        if self.config.collect_tasks and self.router.assistant:
            self.router.assistant.reset()
        if self.router.permission_dialog:
            self.router.permission_dialog.stop()
        disconnect_error = None
        try:
            await self.transport.disconnect()
        except Exception as error:
            disconnect_error = error
        if self.session:
            self.session.status = VoiceSessionStatus.STOPPED; self.session.connection_status = "disconnected"
            self.session.ended_at = datetime.now(timezone.utc)
            self.store.append({"session_id": self.session.session_id, "status": "stopped",
                               "started_at": self.session.started_at.isoformat(), "ended_at": self.session.ended_at.isoformat()})
            await self.events.publish(AutonomousEvent(EventType.VOICE_SESSION, detail={"session_id": self.session.session_id,
                "status": "stopped", "disconnect_error": type(disconnect_error).__name__ if disconnect_error else None}))

    async def pause(self) -> None:
        self._stream_epoch += 1
        self._invalidate_input()
        if self.router.permission_dialog:
            self.router.permission_dialog.stop()
        await self.transport.disconnect()
        if self.session: self.session.status = VoiceSessionStatus.WAITING; self.session.connection_status = "paused"

    async def resume(self) -> None:
        if not self.session: await self.start(); return
        self._clear_request()
        self._seen.clear()
        self.session.assemblyai_session_id = await self._connect_with_backoff()
        self.session.status = VoiceSessionStatus.LISTENING; self.session.connection_status = "connected"
        if self.router.permission_dialog:
            self.router.permission_dialog.start()

    def health_check(self) -> bool:
        return bool(self.session and self.session.status not in {
            VoiceSessionStatus.STOPPED, VoiceSessionStatus.ERROR} and self.transport.health_check())

    def _on_turn(self, turn: VoiceTurn, *, stream_epoch: int | None = None) -> None:
        epoch = self._stream_epoch if stream_epoch is None else stream_epoch
        if self._loop:
            asyncio.run_coroutine_threadsafe(self.process_turn(turn, stream_epoch=epoch), self._loop)

    def _on_error(self, error: str, *, stream_epoch: int | None = None) -> None:
        epoch = self._stream_epoch if stream_epoch is None else stream_epoch
        def mark_failed():
            if epoch != self._stream_epoch:
                return
            if self.session:
                self.session.status = VoiceSessionStatus.ERROR
                self.session.error_state = "AssemblyAI streaming error"
            self._invalidate_input()
        if self._loop:
            self._loop.call_soon_threadsafe(mark_failed)

    async def process_turn(self, turn: VoiceTurn, *, stream_epoch: int | None = None) -> None:
        epoch = self._stream_epoch if stream_epoch is None else stream_epoch
        if epoch != self._stream_epoch:
            return
        if (self.config.collect_tasks and turn.finalized and self.health_check()
                and turn.transcript_id not in self._seen
                and turn.confidence >= self.config.min_confidence
                and self.intent_engine.parse(turn.transcript, turn.confidence).type in {
                    VoiceIntentType.STOP, VoiceIntentType.EMERGENCY_STOP,
                    VoiceIntentType.PAUSE, VoiceIntentType.TAKEOVER}):
            # Stop a pending model request before it can submit a late mission.
            self._invalidate_input()
        dialog = self.router.permission_dialog
        request_id = (dialog.request_id or "") if dialog else None
        reply_context = (self._request_generation, self._request_question is not None)
        session_id = self.session.session_id if self.session else None
        task = asyncio.current_task()
        self._processing_tasks.add(task)
        try:
            async with self._turn_lock:
                if (not self.session or self.session.session_id != session_id
                        or epoch != self._stream_epoch):
                    return
                await self._process_turn(turn, permission_request_id=request_id, reply_context=reply_context)
        finally:
            self._processing_tasks.discard(task)

    async def _process_turn(self, turn: VoiceTurn, *, permission_request_id=None, reply_context=(0, False)) -> None:
        if (not self.session or turn.transcript_id in self._seen
                or self.session.status in {VoiceSessionStatus.STOPPED, VoiceSessionStatus.ERROR}
                or self.session.connection_status != "connected"):
            return
        self._last_activity = monotonic()
        self.session.current_transcript = turn.transcript
        if not turn.finalized:
            if self.is_working_on_task:
                self.session.status = VoiceSessionStatus.EXECUTING
                return
            self._speech_in_progress = True
            self._cancel_request_timer()
            self.session.status = VoiceSessionStatus.TRANSCRIBING
            await self.events.publish(AutonomousEvent(EventType.VOICE_PARTIAL, detail={"session_id": self.session.session_id, "status": "transcribing"}))
            return
        self._seen.add(turn.transcript_id); self.session.last_final_transcript = turn.transcript
        self._speech_in_progress = False
        if not turn.transcript.strip():
            if self._request_active and not self._request_question:
                self._schedule_request_pause()
            self.session.status = VoiceSessionStatus.EXECUTING if self.is_working_on_task else VoiceSessionStatus.LISTENING
            return
        self.session.status = VoiceSessionStatus.PROCESSING
        transcript = turn.transcript.strip()
        collected_only = False
        if self.router.permission_dialog:
            self.router.permission_dialog.status("Thinking about your request: " + transcript[:180])
        parsed_intent = self.intent_engine.parse(transcript, turn.confidence)
        immediate_controls = {
            VoiceIntentType.EMERGENCY_STOP,
            VoiceIntentType.STOP,
        }
        if self.router.permission_dialog and self.router.permission_dialog.pending:
            immediate_controls.update({VoiceIntentType.PAUSE, VoiceIntentType.TAKEOVER})
        if self.config.collect_tasks or self.is_working_on_task:
            immediate_controls.update({VoiceIntentType.PAUSE, VoiceIntentType.TAKEOVER,
                                       VoiceIntentType.RESUME, VoiceIntentType.QUERY_STATUS})
            if self.router.awaiting_clarification or self._request_active:
                immediate_controls.discard(VoiceIntentType.RESUME)
        if self.is_working_on_task and parsed_intent.type not in immediate_controls:
            logger.info("Ignoring utterance while working on active mission %s: %s",
                        self.session.active_mission, transcript)
            self.session.status = VoiceSessionStatus.EXECUTING
            return
        if parsed_intent.type in immediate_controls:
            intent = parsed_intent
            if turn.confidence >= self.config.min_confidence and parsed_intent.type in {
                    VoiceIntentType.STOP, VoiceIntentType.EMERGENCY_STOP, VoiceIntentType.PAUSE,
                    VoiceIntentType.TAKEOVER}:
                self._clear_request()
                self._present_request(status="Request collection stopped.")
            result = (await self.router.route(intent) if turn.confidence >= self.config.min_confidence
                      else {"status": "waiting", "mission_id": None,
                            "result": "Control phrase confidence was too low; please repeat"})
        else:
            intent = VoiceIntent(VoiceIntentType.EXECUTE_TASK, transcript, transcript,
                                 confidence=turn.confidence)
            dialog, assistant = self.router.permission_dialog, self.router.assistant
            permission_reply = bool(permission_request_id or (dialog and dialog.pending))
            accepting_new = (not assistant or getattr(assistant, "accepting_new_task",
                                                      not self.router.awaiting_clarification))
            parts, result = None, None
            stale_finish = (reply_context[1] and reply_context[0] != self._request_generation
                            and self._request_reply(transcript) in self._FINISHED_REPLIES)
            if not permission_reply and stale_finish:
                collected_only = True
                result = {"status": "waiting", "mission_id": None,
                          "result": "That answer belongs to an earlier question. Please answer the current question."}
            elif self.config.collect_tasks and not permission_reply and (self._request_active or accepting_new):
                result, parts = await self._collect_request(turn, reply_context)
                collected_only = parts is None
                if parts:
                    transcript = "\n".join(part.transcript.strip() for part in parts)
                    intent = VoiceIntent(VoiceIntentType.EXECUTE_TASK, transcript, transcript,
                        confidence=min(turn.confidence, *(part.confidence for part in parts)))
            if result is None:
                result = await self.router.route(
                    intent,
                    allow_execution=intent.confidence >= self.config.min_confidence,
                    minimum_confidence=self.config.min_confidence,
                    permission_request_id=permission_request_id,
                )
                if parts and result.get("status") == "failed" and not result.get("mission_id"):
                    self._request_parts = list(parts)
                    self._present_request("I couldn't analyze the complete request yet. Add anything else, or say no to try again.")
                elif permission_reply and self._request_active and not (dialog and dialog.pending):
                    # The consent answer belongs to its displayed tool request,
                    # never to the buffered task's completion question.
                    if self._request_question:
                        self._present_request(self._request_question)
                    else:
                        self._schedule_request_pause()
        if not collected_only:
            self.session.active_mission = result.get("mission_id")
        self.session.status = VoiceSessionStatus.WAITING if result["status"] == "waiting" else VoiceSessionStatus.LISTENING
        if self.router.permission_dialog:
            self.router.permission_dialog.status(str(result.get("result") or "Working on your request…"))
        if collected_only:
            # Unsubmitted fragments live only in this request buffer, not in
            # the mission/command history or persisted event payloads.
            await self.events.publish(AutonomousEvent(EventType.VOICE_SESSION, detail={
                "session_id": self.session.session_id, "status": "waiting", "request_collection": True}))
            return
        record = {"session_id": self.session.session_id, "transcript_id": turn.transcript_id,
                  "timestamp": turn.timestamp.isoformat(), "transcript": intent.transcript,
                  "intent": intent.type.value, "confidence": intent.confidence, **result}
        self.history.append(record); self.history[:] = self.history[-self.config.context_limit:]
        self.store.append(record, include_transcript=self.config.store_transcripts)
        event_record = dict(record)
        if not self.config.store_transcripts: event_record["transcript"] = "[NOT STORED]"
        await self.events.publish(AutonomousEvent(EventType.VOICE_COMMAND, result.get("mission_id"), event_record))

    async def mission_finished(self, mission: Mission) -> None:
        """Publish a follow-up only after runtime verification, serialized with speech."""
        async with self._turn_lock:
            if not self.health_check() or not self.router.assistant:
                return
            epoch, generation = self._stream_epoch, self._request_generation
            continuation = asyncio.create_task(self.router.assistant.mission_finished(mission),
                                               name="voice-mission-followup")
            self._processing_tasks.add(continuation)
            try:
                result = await continuation
            except asyncio.CancelledError:
                if epoch != self._stream_epoch or generation != self._request_generation:
                    # Voice shutdown/stop cancels its reasoning, not the
                    # operator loop that delivered the completed mission.
                    return
                raise
            finally:
                self._processing_tasks.discard(continuation)
            if result:
                self.session.active_mission = result.get("mission_id")
                self.session.status = (VoiceSessionStatus.WAITING if result["status"] == "waiting"
                                       else VoiceSessionStatus.LISTENING)
            else:
                self.session.active_mission = None
                self.session.status = VoiceSessionStatus.LISTENING
            if self.router.awaiting_clarification:
                self._last_activity = monotonic()
                self.session.status = VoiceSessionStatus.WAITING
            if self._request_active:
                # A completed older mission cannot steal the current draft's
                # finish question. Permission prompts still have priority.
                if self._request_question:
                    self._present_request(self._request_question)
                else:
                    self._present_request(status="I'm listening to the rest of your request.")
                    self._schedule_request_pause()

    async def _connect_with_backoff(self) -> str | None:
        self._stream_epoch += 1
        epoch = self._stream_epoch
        def on_turn(turn):
            if epoch == self._stream_epoch:
                self._on_turn(turn, stream_epoch=epoch)
        def on_error(error):
            if epoch == self._stream_epoch:
                self._on_error(error, stream_epoch=epoch)
        error = None
        for attempt in range(self.config.reconnect_limit + 1):
            try: return await self.transport.connect(on_turn, on_error)
            except Exception as caught:
                error = caught
                if attempt < self.config.reconnect_limit:
                    self.reconnects += 1
                    await asyncio.sleep(min(2 ** attempt, 8))
        raise ConnectionError("AssemblyAI connection failed") from error

    def snapshot(self) -> dict[str, object]:
        session = self.session
        finalized = [item for item in self.history if "confidence" in item]
        successful = sum(item.get("status") in {"accepted", "completed"} for item in finalized)
        return {"status": "executing" if self.is_working_on_task else (session.status.value if session else "idle"), "connection": session.connection_status if session else "disconnected",
                "session_id": session.session_id if session else None, "assemblyai_session_id": session.assemblyai_session_id if session else None,
                "microphone": session.microphone if session else "default", "current_transcript": session.current_transcript if session else "",
                "final_transcript": session.last_final_transcript if session else "", "active_mission": session.active_mission if session else None,
                "error": session.error_state if session else None, "history": list(self.history), "model": self.config.model,
                "sample_rate": self.config.sample_rate, "mode": self.config.mode.value,
                "activation": "complete_spoken_requests" if self.config.collect_tasks else "all_finalized_transcripts",
                "collect_tasks": self.config.collect_tasks, "task_pause_seconds": self.config.task_pause_seconds,
                "request_collection": {"active": self._request_active,
                    "awaiting_finish": self._request_question is not None, "part_count": len(self._request_parts)},
                "assistant_question": (self.router.current_question if self.router.permission_dialog
                    and self.router.permission_dialog.pending else self._request_question or self.router.current_question),
                "analytics": {"sessions": 1 if session else 0, "commands": len(finalized),
                              "successful_commands": successful, "failed_commands": len(finalized) - successful,
                              "average_confidence": (sum(float(item["confidence"]) for item in finalized) / len(finalized)) if finalized else None,
                              "reconnects": self.reconnects}}
