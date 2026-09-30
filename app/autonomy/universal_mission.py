"""Provider-independent mission planning and bounded execution.

This module is the connected flow used by the application boundary.  Providers
may help interpret or plan a mission, but they do not own mission state and
cannot claim that an action succeeded.  Capability adapters execute steps and
their verifiers certify the observed outcome.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol

from app.autonomy.mission import Mission, MissionStatus, MissionStore
from app.autonomy.environment import BoundaryMemory, EnvironmentExplorer, EnvironmentSnapshot


class MissionIntent(str, Enum):
    YOUTUBE_PLAY = "youtube_play"
    BLENDER_SCENE = "blender_scene"
    UNREAL_SCENE = "unreal_scene"
    GAME_DEVELOPMENT = "game_development"
    DESKTOP_ACTION = "desktop_action"
    WEB_RESEARCH = "web_research"
    GENERAL = "general"


@dataclass(frozen=True, slots=True)
class MissionUnderstanding:
    intent: MissionIntent
    objective: str
    needs_clarification: bool = False
    clarification: str | None = None
    needs_browser_team: bool = False
    required_capabilities: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class MissionStep:
    step_id: str
    objective: str
    required_capabilities: frozenset[str]
    verification: dict[str, Any] = field(default_factory=dict)
    max_attempts: int = 1


@dataclass(frozen=True, slots=True)
class MissionPlan:
    understanding: MissionUnderstanding
    steps: tuple[MissionStep, ...]


@dataclass(frozen=True, slots=True)
class StepResult:
    success: bool
    output: Any = None
    observations: dict[str, Any] = field(default_factory=dict)
    uncertain: bool = False
    error: str | None = None


class StepAdapter(Protocol):
    async def execute(self, step: MissionStep, mission: Mission) -> StepResult: ...
    async def verify(self, step: MissionStep, result: StepResult, mission: Mission) -> tuple[bool, str]: ...


def understand_request(request: str) -> MissionUnderstanding:
    """Classify obvious capabilities locally before opening any provider."""
    if not isinstance(request, str) or not request.strip():
        raise ValueError("A mission request is required")
    text = request.strip()
    lowered = text.casefold()
    if "youtube" in lowered or "youtube music" in lowered:
        generic_words = {
            "a", "an", "and", "from", "go", "goto", "in", "music", "on",
            "open", "play", "please", "song", "some", "tab", "the", "to",
            "youtube",
        }
        remaining = [word.strip(".,!?") for word in lowered.replace("-", " ").split()
                     if word.strip(".,!?") not in generic_words]
        if not remaining:
            return MissionUnderstanding(
                MissionIntent.YOUTUBE_PLAY, text, True,
                "Specify a song and artist, or choose a recommendation.",
                required_capabilities=frozenset({"browser.navigation", "browser.media_playback"}),
            )
        return MissionUnderstanding(
            MissionIntent.YOUTUBE_PLAY, text,
            required_capabilities=frozenset({"browser.navigation", "browser.media_playback"}),
        )
    if any(term in lowered for term in ("unreal", "game development", "game dev", "gamedev")):
        return MissionUnderstanding(
            MissionIntent.UNREAL_SCENE if "unreal" in lowered else MissionIntent.GAME_DEVELOPMENT,
            text, needs_browser_team=True,
            required_capabilities=frozenset({"creative.collaboration", "desktop.application"}),
        )
    if any(term in lowered for term in ("blender", "3d model", "model a ", "render a scene")):
        complex_terms = ("team", "multiple", "agents", "research", "review", "iterate", "complex", "architecture")
        return MissionUnderstanding(
            MissionIntent.BLENDER_SCENE, text,
            needs_browser_team=any(term in lowered for term in complex_terms),
            required_capabilities=frozenset({"blender.scene_edit"}),
        )
    if any(term in lowered for term in ("research", "compare", "look up", "find online", "web search")):
        return MissionUnderstanding(
            MissionIntent.WEB_RESEARCH, text, needs_browser_team=True,
            required_capabilities=frozenset({"browser.navigation", "web.research"}),
        )
    if any(term in lowered for term in ("open ", "click ", "type ", "launch ", "desktop")):
        return MissionUnderstanding(
            MissionIntent.DESKTOP_ACTION, text,
            required_capabilities=frozenset({"desktop.control"}),
        )
    if any(term in lowered for term in ("sha-256", "sha256", "checksum")):
        return MissionUnderstanding(
            MissionIntent.GENERAL, text,
            required_capabilities=frozenset({"cli.checksum", "filesystem.write_report"}),
        )
    return MissionUnderstanding(MissionIntent.GENERAL, text, needs_browser_team=False)


def plan_request(understanding: MissionUnderstanding) -> MissionPlan:
    """Create a bounded default plan; complex plans can be supplied by a leader."""
    if understanding.needs_clarification:
        return MissionPlan(understanding, ())
    intent = understanding.intent
    if intent is MissionIntent.YOUTUBE_PLAY:
        steps = (
            MissionStep("open-youtube-music", "Open YouTube Music",
                        frozenset({"browser.navigation"}), {"host": "music.youtube.com"}),
            MissionStep("select-youtube-content", "Select the requested song or recommendation",
                        frozenset({"browser.navigation", "browser.media_playback"}),
                        {"watch_url": True}),
            MissionStep("verify-youtube-playback", "Start playback and verify the media is playing",
                        frozenset({"browser.media_playback"}), {"media_playing": True}),
        )
    elif intent is MissionIntent.BLENDER_SCENE:
        steps = (MissionStep("execute-blender-scene", understanding.objective,
                             frozenset({"blender.scene_edit"}), {"scene_updated": True}),)
    elif intent in {MissionIntent.UNREAL_SCENE, MissionIntent.GAME_DEVELOPMENT}:
        steps = (MissionStep("collaborative-creative-plan", understanding.objective,
                             frozenset({"creative.collaboration"}), {"knowledge_shared": True}),)
    elif intent is MissionIntent.WEB_RESEARCH:
        steps = (MissionStep("research-web", understanding.objective,
                             frozenset({"web.research"}), {"evidence_collected": True}),)
    elif "cli.checksum" in understanding.required_capabilities:
        steps = (
            MissionStep("discover-checksum-cli", "Select a discovered checksum CLI",
                        frozenset({"cli.checksum"}), {"tool_allow_list": True}),
            MissionStep("write-checksum-report", understanding.objective,
                        frozenset({"cli.checksum", "filesystem.write_report"}),
                        {"report_created": True}),
            MissionStep("verify-checksum-report", "Verify the checksum report contents",
                        frozenset({"filesystem.read_report"}), {"report_verified": True}),
        )
    else:
        steps = (MissionStep("execute-general-task", understanding.objective, frozenset(), {}),)
    return MissionPlan(understanding, steps)


class UniversalMissionCoordinator:
    """Persist, execute, verify, and recover any bounded mission."""

    def __init__(self, store: MissionStore, adapters: dict[MissionIntent, StepAdapter],
                 *, ask: Callable[[str], Awaitable[str]] | None = None) -> None:
        self.store, self.adapters, self.ask = store, adapters, ask

    def register_adapter(self, intent: MissionIntent, adapter: StepAdapter) -> None:
        """Register a trusted domain adapter at the composition boundary."""
        if not isinstance(intent, MissionIntent):
            raise TypeError("Mission adapter intent must be a MissionIntent")
        self.adapters[intent] = adapter

    async def create(self, request: str, *, owner: str = "user") -> Mission:
        understanding = understand_request(request)
        if understanding.needs_clarification:
            if self.ask is None:
                raise ValueError(understanding.clarification or "Mission needs clarification")
            answer = (await self.ask(understanding.clarification or "Please clarify the task")).strip()
            request = (f"Play {answer} on YouTube Music"
                       if answer else "Play a recommendation on YouTube Music")
            understanding = understand_request(request)
        plan = plan_request(understanding)
        mission = Mission(goal=request, owner=owner, status=MissionStatus.PLANNING,
                          acceptance_criteria=tuple(step.objective for step in plan.steps))
        mission.current_state["understanding"] = {
            "intent": understanding.intent.value,
            "needs_browser_team": understanding.needs_browser_team,
            "required_capabilities": sorted(understanding.required_capabilities),
        }
        mission.task_graph = {
            step.step_id: {"objective": step.objective, "status": "pending",
                           "capabilities": sorted(step.required_capabilities),
                           "verification": step.verification}
            for step in plan.steps
        }
        self.store.save(mission)
        return mission


    async def execute(self, mission: Mission) -> Mission:
        understanding = MissionIntent(mission.current_state["understanding"]["intent"])
        adapter = self.adapters.get(understanding)
        if adapter is None:
            mission.status = MissionStatus.BLOCKED
            mission.current_state["error"] = f"No adapter registered for {understanding.value}"
            self.store.save(mission)
            return mission
        mission.status = MissionStatus.RUNNING
        for step_id, state in mission.task_graph.items():
            if state.get("status") == "completed":
                continue
            step = MissionStep(step_id, state["objective"], frozenset(state.get("capabilities", ())),
                               dict(state.get("verification", {})))
            state["status"] = "running"
            mission.touch()
            self.store.save(mission)
            result = await adapter.execute(step, mission)
            if result.uncertain:
                state["status"] = "uncertain"
                mission.status = MissionStatus.PAUSED
                mission.current_state["uncertain_step"] = step_id
                mission.current_state["error"] = result.error or "External action outcome is uncertain"
                self.store.save(mission)
                return mission
            if not result.success:
                state["status"] = "failed"
                mission.status = MissionStatus.FAILED
                mission.current_state["error"] = result.error or "Mission step failed"
                self.store.save(mission)
                return mission
            verified, detail = await adapter.verify(step, result, mission)
            state["observations"] = result.observations
            state["verification"] = detail
            if not verified:
                state["status"] = "failed"
                mission.status = MissionStatus.FAILED
                mission.current_state["error"] = detail
                self.store.save(mission)
                return mission
            state["status"] = "completed"
            mission.refresh_progress()
            self.store.save(mission)
        mission.status = MissionStatus.COMPLETED
        mission.refresh_progress()
        self.store.save(mission)
        return mission


class UniversalAgent:
    """Perceive, plan, execute, verify, and remember task boundaries."""

    def __init__(self, coordinator: UniversalMissionCoordinator,
                 explorer: EnvironmentExplorer, boundaries: BoundaryMemory) -> None:
        self.coordinator, self.explorer, self.boundaries = coordinator, explorer, boundaries
        self.environment: EnvironmentSnapshot | None = None

    async def run(self, request: str, *, owner: str = "user") -> Mission:
        self.environment = await self.explorer.explore()
        mission = await self.coordinator.create(request, owner=owner)
        signature = mission.current_state["understanding"]["intent"]
        known_failures = self.boundaries.known(signature, mission.goal, "failure")
        if known_failures:
            mission.status = MissionStatus.BLOCKED
            mission.current_state["error"] = "Known boundary: " + known_failures[0]["detail"]
            self.coordinator.store.save(mission)
            return mission
        mission = await self.coordinator.execute(mission)
        outcome = "success" if mission.status is MissionStatus.COMPLETED else "failure"
        detail = mission.current_state.get("error", mission.status.value)
        self.boundaries.record(signature, mission.goal, outcome, str(detail))
        return mission


class GeneralCliMissionAdapter:
    """Bounded adapter for harmless, deterministic CLI missions.

    Only executables discovered by :class:`EnvironmentExplorer` are invoked.
    The adapter never evaluates generated source or accepts shell command text.
    """

    _FILE = re.compile(r"\b(?:for|of)\s+[\"']?([^\"']+?)[\"']?(?:\s+(?:to|as)\s+|$)", re.I)
    _OUTPUT = re.compile(r"\b(?:to|as)\s+[\"']?([^\"']+?)[\"']?\s*$", re.I)

    def __init__(self, environment: EnvironmentSnapshot | EnvironmentExplorer, root=None, *,
                     approval: Callable[[MissionStep, Mission], Awaitable[bool] | bool] | None = None) -> None:
            self.environment = environment
            self.root = Path(root or (environment.cwd if isinstance(environment, EnvironmentSnapshot) else Path.cwd())).resolve()
            self.approval = approval

    def _paths(self, goal: str):
            match = self._FILE.search(goal)
            if not match:
                raise ValueError("Checksum task must name an input file with 'for' or 'of'")
            source = (self.root / match.group(1).strip()).resolve()
            output_match = self._OUTPUT.search(goal)
            output = (self.root / (output_match.group(1).strip() if output_match else "sha256-report.txt")).resolve()
            for path in (source, output):
                if path != self.root and self.root not in path.parents:
                    raise ValueError("Input and report paths must remain inside the mission workspace")
            if not source.is_file():
                raise FileNotFoundError(f"Checksum input does not exist: {source.name}")
            return source, output

    def _tool(self):
            for name in ("sha256sum", "shasum", "certutil"):
                if name in self.environment.executables:
                    return name, self.environment.executables[name]
            raise RuntimeError("No discovered allow-listed SHA-256 CLI is available")

    async def execute(self, step: MissionStep, mission: Mission) -> StepResult:
            if mission.risk_policy == "deny":
                return StepResult(False, error="Mission risk policy denies CLI execution")
            try:
                if isinstance(self.environment, EnvironmentExplorer):
                    self.environment = await self.environment.explore()
                if step.step_id == "discover-checksum-cli":
                    name, _ = self._tool()
                    return StepResult(True, observations={"tool": name, "risk": "low"})
                source, output = self._paths(mission.goal)
                if self.approval is not None and step.step_id == "write-checksum-report":
                    decision = self.approval(step, mission)
                    if asyncio.iscoroutine(decision):
                        decision = await decision
                    if not decision:
                        return StepResult(False, error="CLI report write was not approved")
                name, executable = self._tool()
                if step.step_id == "write-checksum-report":
                    args = [executable, str(source)] if name == "sha256sum" else (
                        [executable, "-a", "256", str(source)] if name == "shasum"
                        else [executable, "-hashfile", str(source), "SHA256"])
                    result = await asyncio.to_thread(
                        subprocess.run, args, capture_output=True, text=True, timeout=10, check=False)
                    if result.returncode:
                        return StepResult(False, error=f"{name} failed with exit code {result.returncode}")
                    digest = _parse_checksum(name, result.stdout)
                    output.write_text(f"{source.name}  {digest}\n", encoding="utf-8")
                    return StepResult(True, observations={"report": str(output), "digest": digest, "tool": name})
                if step.step_id == "verify-checksum-report":
                    data = output.read_text(encoding="utf-8").strip().split()
                    digest = data[-1] if data else ""
                    expected = hashlib.sha256(source.read_bytes()).hexdigest()
                    return StepResult(digest.casefold() == expected, observations={"report_verified": digest.casefold() == expected},
                                      error=None if digest.casefold() == expected else "Checksum report did not match input")
                return StepResult(False, error=f"Unsupported general CLI step: {step.step_id}")
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                return StepResult(False, error=str(error))

    async def verify(self, step: MissionStep, result: StepResult, mission: Mission) -> tuple[bool, str]:
            expected = step.verification
            if expected.get("tool_allow_list") and not result.observations.get("tool"):
                return False, "No allow-listed checksum CLI was selected"
            if expected.get("report_created") and not result.observations.get("report"):
                return False, "Checksum report was not created"
            if expected.get("report_verified") and result.observations.get("report_verified") is not True:
                return False, result.error or "Checksum report verification failed"
            return result.success, result.error or "verified"


def _parse_checksum(tool: str, text: str) -> str:
    for line in text.splitlines():
            match = re.search(r"\b([0-9a-fA-F]{64})\b", line)
            if match:
                return match.group(1).lower()
    raise ValueError(f"{tool} returned no SHA-256 digest")


class YouTubeBrowserAdapter:
    """Local YouTube capability; no reasoning provider is required."""

    def __init__(self, browser) -> None:
        self.browser = browser

    async def execute(self, step: MissionStep, mission: Mission) -> StepResult:
        await self.browser.start()
        if step.step_id == "open-youtube-music":
            page = await self.browser.page_for("https://music.youtube.com/")
            return StepResult(True, observations={"url": page.url, "host": "music.youtube.com"})
        if step.step_id == "select-youtube-content":
            query = mission.goal.removeprefix("Play ").removesuffix(" on YouTube Music").strip()
            if query.casefold() == "a recommendation":
                page = await self.browser.page_for("https://music.youtube.com/")
                for selector in (
                    "ytmusic-two-row-item-renderer a[href*='/watch']",
                    "ytmusic-responsive-list-item-renderer a[href*='/watch']",
                    "a[href*='/watch']",
                ):
                    try:
                        if await page.locator(selector).count():
                            await page.locator(selector).first.click()
                            return StepResult(True, observations={"url": page.url, "selected": "recommendation"})
                    except Exception:
                        continue
                return StepResult(False, error="No YouTube Music recommendation was available")
            page = await self.browser.page_for(
                "https://www.youtube.com/results?search_query=" + _quote(query))
            selector = "ytd-video-renderer a#video-title"
            try:
                await page.wait_for_selector(selector, timeout=5000)
                await page.locator(selector).first.click()
            except Exception as error:
                return StepResult(False, error=f"YouTube result selection failed: {error}")
            return StepResult(True, observations={"url": page.url, "selected": query})
        if step.step_id == "verify-youtube-playback":
            page = await self.browser.page_for("https://www.youtube.com/")
            for selector in ("button.ytp-large-play-button", "button.ytp-play-button"):
                if await page.locator(selector).count():
                    await page.locator(selector).first.click()
                    break
            playing = await page.evaluate(
                "() => { const v = document.querySelector('video'); "
                "return Boolean(v && !v.paused && v.currentTime > 0); }"
            )
            return StepResult(playing, observations={"media_playing": playing},
                              error=None if playing else "YouTube media is not playing")
        return StepResult(False, error=f"Unsupported YouTube step: {step.step_id}")

    async def verify(self, step: MissionStep, result: StepResult, mission: Mission) -> tuple[bool, str]:
        expected = step.verification
        if expected.get("host") and result.observations.get("host") != expected["host"]:
            return False, "YouTube Music did not open"
        if expected.get("watch_url") and "/watch" not in str(result.observations.get("url", "")):
            return False, "A YouTube video was not selected"
        if expected.get("media_playing") and result.observations.get("media_playing") is not True:
            return False, "YouTube media is not playing"
        return result.success, result.error or "verified"


def _quote(value: str) -> str:
    from urllib.parse import quote_plus
    return quote_plus(value)


class BrowserTeamMissionAdapter:
    """Bridge complex missions to the existing collaborative browser workflow."""

    def __init__(self, runner: Callable[[str], Awaitable[Any]]) -> None:
        self.runner = runner

    async def execute(self, step: MissionStep, mission: Mission) -> StepResult:
        try:
            output = await self.runner(mission.goal)
        except Exception as error:
            return StepResult(False, error=f"Browser-team execution failed: {error}")
        return StepResult(True, output=output,
                          observations={"collaboration": "browser-team",
                                        "step": step.step_id})

    async def verify(self, step: MissionStep, result: StepResult,
                     mission: Mission) -> tuple[bool, str]:
        if not result.success:
            return False, result.error or "Browser-team execution failed"
        return True, "Browser-team workflow completed"
