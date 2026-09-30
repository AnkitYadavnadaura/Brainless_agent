"""Root decision flow: analyse requirements, reuse or create, then supervise."""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from app.agents.manager import AgentManager
from app.agents.models import Agent
from app.autonomy.executor import ActionRuntime, DecisionProvider
from app.autonomy.factory import AgentFactory
from app.autonomy.reasoning_provider import ReasoningDecisionProvider
from app.autonomy.models import AgentSpec, TaskRequirements
from app.autonomy.registry import AgentRegistry
from app.safety.permissions import Permission


@dataclass(frozen=True, slots=True)
class AutonomousResult:
    agent_id: str
    created: bool
    actions: int
    result: str


class CapabilityAnalyzer:
    """Conservative task analyser; replaceable by a model-backed planner later."""
    def analyze(self, task: str) -> TaskRequirements:
        lower = task.lower()
        capabilities: set[str] = {"computer.observe"}
        permissions: set[str] = {Permission.SCREEN_READ.value}
        tools: set[str] = set()
        role = "ComputerAgent"
        if any(word in lower for word in ("browser", "website", "web", "navigate", "url")):
            capabilities.add("browser.navigation"); permissions.add(Permission.BROWSER_NAVIGATE.value); tools.add("browser.navigate"); role = "BrowserAgent"
        if any(word in lower for word in ("canva", "presentation", "slide", "figma", "design")):
            capabilities.update({"browser.navigation", "mouse.control", "keyboard.input"})
            permissions.update({Permission.BROWSER_NAVIGATE.value, Permission.MOUSE_CLICK.value, Permission.KEYBOARD_WRITE.value})
            tools.update({"browser.navigate", "mouse.click", "keyboard.write"})
            role = "BrowserAgent"
        if any(word in lower for word in ("email", "gmail", "compose email", "send email")):
            capabilities.update({"browser.navigation", "keyboard.input"})
            permissions.update({Permission.BROWSER_NAVIGATE.value, Permission.KEYBOARD_WRITE.value})
            tools.update({"browser.navigate", "keyboard.write"})
            role = "BrowserAgent"
        if any(word in lower for word in ("crawl", "scrape", "explore site", "extract links")):
            capabilities.update({"browser.navigation", "browser.crawl"})
            permissions.update({Permission.BROWSER_NAVIGATE.value, Permission.SCREEN_READ.value})
            tools.update({"browser.navigate", "browser.crawl"})
            role = "BrowserAgent"
        if "youtube" in lower or "youtube music" in lower:
            capabilities.add("browser.navigation")
            permissions.update({Permission.BROWSER_NAVIGATE.value, Permission.SCREEN_READ.value})
            tools.add("youtube.play")
            role = "BrowserAgent"
        if any(word in lower for word in ("document", "text editor", "write")):
            capabilities.add("keyboard.input"); permissions.add(Permission.KEYBOARD_WRITE.value); tools.add("keyboard.write")
        if any(word in lower for word in ("document", "save", "file")):
            capabilities.add("filesystem.write"); permissions.add(Permission.FILESYSTEM_WRITE.value); tools.add("filesystem.write")
            role = "DocumentAgent"
        if any(word in lower for word in ("click", "button", "mouse")):
            capabilities.add("mouse.control"); permissions.add(Permission.MOUSE_CLICK.value); tools.add("mouse.click")
        if any(word in lower for word in ("calculator", "calculate", "notepad", "paint", "file explorer",
                                          "display settings", "open settings")):
            capabilities.add("desktop.control")
            permissions.add(Permission.WINDOW_CONTROL.value)
            tools.add("desktop.launch")
        if any(word in lower for word in ("type in notepad", "type into", "visible text")):
            capabilities.add("desktop.control")
            permissions.update({Permission.WINDOW_CONTROL.value, Permission.KEYBOARD_WRITE.value})
            tools.add("desktop.type")
        if any(word in lower for word in ("add ", "plus", "divide", "multiply", "calculate")) and "calculator" in lower:
            capabilities.add("desktop.control")
            permissions.update({Permission.WINDOW_CONTROL.value, Permission.KEYBOARD_WRITE.value})
            tools.add("desktop.calculator")
        if any(word in lower for word in (
            "blender", "3d model", "3d object", "car model", "model a car",
            "building", "house", "room", "robot", "spaceship", "vehicle",
            "furniture", "chair", "table", "tree", "environment", "sculpture",
        )):
            capabilities.add("blender.scene")
            permissions.update({
                Permission.FILESYSTEM_READ.value,
                Permission.FILESYSTEM_WRITE.value,
                Permission.PROCESS_EXECUTE.value,
            })
            tools.add("blender.scene")
            role = "BlenderAgent"
        # If the task asks to "search" or mentions Google/typing, require
        # keyboard and mouse control so the runtime will create/choose an
        # agent capable of human-like interactions (typing and clicking).
        if any(word in lower for word in ("search", "google", "type", "open chrome", "open chrome and")):
            capabilities.add("keyboard.input"); permissions.add(Permission.KEYBOARD_WRITE.value); tools.add("keyboard.write")
            capabilities.add("mouse.control"); permissions.add(Permission.MOUSE_CLICK.value); tools.add("mouse.click")
        return TaskRequirements(frozenset(capabilities), frozenset(permissions), frozenset(tools), role)


class AutonomousRuntime:
    def __init__(self, manager: AgentManager, actions: ActionRuntime,
                 registry: AgentRegistry | None = None, analyzer: CapabilityAnalyzer | None = None,
                 reasoning_provider=None, agent_planner=None) -> None:
        self.manager, self.actions = manager, actions
        self.registry, self.analyzer = registry or AgentRegistry(), analyzer or CapabilityAnalyzer()
        self.reasoning_provider = reasoning_provider
        self.agent_planner = agent_planner
        self.factory = AgentFactory(manager)

    async def execute(self, root_agent_id: str, task_id: str, task: str, decider: DecisionProvider | None = None,
                      requirements: TaskRequirements | None = None,
                      *, use_agent_planner: bool = True) -> AutonomousResult:
        # Graph execution supplies validated requirements; ad-hoc execution is analysed.
        if decider is None:
            if self.reasoning_provider is None:
                raise RuntimeError("A DecisionProvider or configured ReasoningProvider is required")
            decider = ReasoningDecisionProvider(self.reasoning_provider, self.actions.proposal_validator, self.manager)
        requirements = requirements or self.analyzer.analyze(task)
        planner = self.agent_planner if use_agent_planner else None
        if planner is not None:
            agent, created = await planner.select_or_create(
                root_agent_id, task_id, task, requirements)
        else:
            agent = self.registry.find(requirements)
            created = agent is None
        if planner is None and agent is None:
            agent = self.factory.create(root_agent_id, AgentSpec(
                name=requirements.role, role=requirements.role, objective=f"Execute {task}", task=task,
                required_capabilities=requirements.capabilities, tools=requirements.tools, task_id=task_id,
                constraints={"least_privilege": True},
            ))
            self.registry.register(agent, requirements.capabilities)
        elif planner is None:
            self.manager.assign_task(root_agent_id, agent.agent_id, task, task_id=task_id)

        async def work(child: Agent, _: AgentManager) -> str:
            results = await self.actions.run_loop(child.agent_id, task_id, task, decider)
            if not results or not results[-1].success:
                raise RuntimeError("Autonomous task did not produce a verified action")
            successful = sum(result.success and result.verified for result in results)
            recovered = len(results) - successful
            suffix = f" after {recovered} recovered failure(s)" if recovered else ""
            return f"Completed {successful} verified action(s){suffix}"

        started = monotonic()
        try:
            outcome = await self.manager.start_agent(root_agent_id, agent.agent_id, work)
        except Exception:
            self.registry.record_result(agent.agent_id, success=False, verified=False,
                                        duration_ms=(monotonic() - started) * 1000)
            raise
        self.registry.record_result(agent.agent_id, success=True, verified=True,
                                    duration_ms=(monotonic() - started) * 1000)
        return AutonomousResult(agent.agent_id, created, len(agent.execution_history), outcome)
