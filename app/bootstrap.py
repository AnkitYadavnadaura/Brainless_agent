"""Application composition root shared by CLI and desktop UI."""
from __future__ import annotations

from pathlib import Path

from app.browser.browser_manager import BrowserManager
from app.browser.external_client import ExternalBrowserClient
from app.agents.manager import AgentManager
from app.agents.runtime_tools import register_runtime_tools, register_capability_skilling_tool
from app.agents.tools import ToolRegistry
from app.computer.screenshot import ScreenshotRecorder
from app.config.settings import Settings
from app.memory.sqlite_memory import SQLiteMemory
from app.prompts.prompt_manager import PromptManager
from app.providers.registry import ProviderRegistry
from app.runtime.agent_runtime import AgentRuntime
from app.autonomy.controllers import PlaywrightComputerController
from app.autonomy.executor import ActionRuntime as AutonomousActionRuntime
from app.autonomy.orchestrator import AutonomousRuntime
from app.autonomy.task_engine import AutonomousTaskEngine
from app.safety.intervention import UserInterventionGate
from app.learning import ExperienceMemory, LearningCoordinator, SkillRegistry, AgentPerformanceMemory
from app.event_system import create_event_platform
from app.autonomy.capability_broker import CapabilityBroker
from app.autonomy.capability_discovery import AutomaticCapabilityService, WebsiteCapabilityDiscovery
from app.autonomy.capability_lifecycle import CapabilityLifecycle, CapabilityStore
from app.autonomy.universal_router import UniversalTaskRouter
from app.autonomy.mission import MissionStore
from app.autonomy.universal_mission import (
    GeneralCliMissionAdapter, MissionIntent, UniversalAgent, UniversalMissionCoordinator)
from app.autonomy.environment import BoundaryMemory, EnvironmentExplorer
from app.autonomy.tool_builder import ToolBuilder
from app.autonomy.video_capability import build_ffmpeg_video_tool, health_check_ffmpeg
from app.autonomy.automation_catalog import AutomationCatalog
from app.autonomy.automation_runner import AutomationRunner
from app.autonomy.blender_capability import build_blender_tool, health_check_blender
from app.autonomy.blender_mission import BlenderMissionAdapter
from app.autonomy.unreal_capability import build_unreal_tool, health_check_unreal
from app.autonomy.vscode_worker import VscodeWorker
from app.autonomy.capability_skilling import CapabilityGapCoordinator


class Application:
    def __init__(self, root: Path, settings: Settings, intervention: UserInterventionGate | None = None,
                 *, providers: ProviderRegistry | None = None) -> None:
        self.memory = SQLiteMemory(root / "data/memory.db")
        self.browser = BrowserManager(settings.browser, root)
        self.external_browser = ExternalBrowserClient(root)
        self.gmail_profiles = self.external_browser
        self.vscode_worker = VscodeWorker(root)
        tools = ToolRegistry()
        register_runtime_tools(
            tools, self.browser, root,
            screenshots=ScreenshotRecorder(root / "screenshots"),
            gmail_profiles=self.gmail_profiles,
            external_browser=self.external_browser,
        )
        self.agent_manager = AgentManager(tools, audit_store=self.memory)
        # Desktop events/actions are composed independently from reasoning. Detectors remain
        # idle until a caller starts polling, and sensitive observation defaults to off.
        self.event_platform = create_event_platform()
        self.autonomous_actions = AutonomousActionRuntime(
            self.agent_manager, PlaywrightComputerController(self.browser), audit_store=self.memory)
        self.autonomous = AutonomousRuntime(self.agent_manager, self.autonomous_actions)
        # Learning stores structured runtime outcomes separately from conversational memory.
        self.experience_memory = ExperienceMemory(root / "data/experience.db")
        self.skill_registry = SkillRegistry(root / "data/skills.db")
        self.learning = LearningCoordinator(self.experience_memory, self.skill_registry)
        # Browser-authorized capability gaps are completed only through the
        # runtime-owned worker/validation gate; providers never promote skills.
        self.capability_skilling = CapabilityGapCoordinator(
            self.vscode_worker, self.learning)
        register_capability_skilling_tool(tools, self.capability_skilling)
        self.agent_performance = AgentPerformanceMemory(root / "data/agent_performance.db")
        # The normal autonomous entry point shares the controlled learning coordinator.
        self.task_engine = AutonomousTaskEngine(self.autonomous, self.autonomous_actions,
                                                journal=self.memory, learning=self.learning, performance=self.agent_performance)
        self.providers = providers if providers is not None else ProviderRegistry.from_settings(self.browser, settings.providers)
        self.capability_lifecycle = CapabilityLifecycle(
            tools,
            CapabilityStore(root / "data/capabilities.db"),
            root / "data/capability-sandbox",
            allow_sources=frozenset({"trusted-catalog"}),
        )
        self.capability_lifecycle.register_builder(
            "ffmpeg-video", build_ffmpeg_video_tool, health_check_ffmpeg)
        self.capability_lifecycle.register_builder(
            "blender-scene", build_blender_tool, health_check_blender)
        self.capability_lifecycle.register_builder(
            "unreal-editor", build_unreal_tool, health_check_unreal)
        self.capability_broker = CapabilityBroker(
            self.agent_manager, self.autonomous.registry, self.autonomous.analyzer)
        self.automation_catalog = AutomationCatalog()
        self.automation_runner = AutomationRunner(self.agent_manager, self.automation_catalog)
        self.capability_discovery = None
        if self.providers.names:
            self.capability_discovery = AutomaticCapabilityService(
                self.capability_broker,
                WebsiteCapabilityDiscovery(
                    self.providers.get(self.providers.names[0]), self.capability_lifecycle,
                ),
            )
        self.runtime = AgentRuntime(
            self.browser, self.providers, PromptManager(root / "prompts"), self.memory,
            settings.agent.max_retries, settings.agent.max_actions, settings.agent.max_task_minutes,
            screenshots=ScreenshotRecorder(root / "screenshots"),
            intervention=intervention,
        )
        self.universal_router = UniversalTaskRouter(
            self.capability_broker, self.capability_discovery,
            self.runtime.run,
        )
        # Mission state is provider-independent. Domain workflows register
        # trusted adapters here; browser-team remains an optional complex-task
        # adapter rather than the default execution engine.
        self.mission_store = MissionStore(root / "data/missions.json")
        self.missions = UniversalMissionCoordinator(self.mission_store, {})
        self.missions.register_adapter(
            MissionIntent.BLENDER_SCENE,
            BlenderMissionAdapter(self.capability_lifecycle),
        )
        self.environment_explorer = EnvironmentExplorer()
        self.missions.register_adapter(
            MissionIntent.GENERAL,
            GeneralCliMissionAdapter(self.environment_explorer, root),
        )
        self.boundary_memory = BoundaryMemory(root / "data/boundaries.db")
        self.tool_builder = ToolBuilder(root / "data/generated-tools")
        self.universal_agent = UniversalAgent(
            self.missions, self.environment_explorer, self.boundary_memory)

    async def close(self) -> None:
        self.event_platform.emergency_stop()
        self.event_platform.manager.stop()
        self.experience_memory.close()
        self.skill_registry.close()
        self.capability_lifecycle.store.close()
        self.agent_performance.close()
        self.boundary_memory.close()
        self.memory.close()
        # Close Playwright's driver and browser context before the asyncio loop
        # exits. This prevents Windows Proactor pipe finalizer warnings.
        await self.browser.close()
