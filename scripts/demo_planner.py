import asyncio
import json
import sys
from types import SimpleNamespace
from pathlib import Path

# Ensure project root is on sys.path so `import app` works when executed as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.manager import AgentManager
from app.agents.tools import ToolRegistry, ToolSpec, RiskLevel
from app.agents.planning import AgentPlanningWorkflow


class FakeRegistry:
    def __init__(self):
        self.items = {}
        self.capabilities = {}

    def register(self, agent, capabilities):
        self.items[agent.agent_id] = agent
        self.capabilities[agent.agent_id] = capabilities

    def agents(self): return tuple(self.items.values())
    def capabilities_for(self, agent_id): return self.capabilities[agent_id]
    def available(self, agent_id): return self.items[agent.agent_id].status.value in {"ready", "completed"}

    def find(self, requirements):
        return next((agent for agent in self.items.values()
                     if requirements.capabilities.issubset(self.capabilities[agent.agent_id])
                     and requirements.permissions.issubset(agent.permissions)
                     and requirements.tools.issubset(agent.available_tools)), None)


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def prepare_conversation(self, prompt):
        self.prompts.append(prompt)

    async def open(self):
        pass

    async def verify_page(self):
        pass

    async def start_conversation(self):
        pass

    async def send_prompt(self, _):
        pass

    async def wait_for_response(self):
        pass

    def remember_conversation(self):
        pass

    async def extract_response(self):
        return self.responses.pop(0)


def setup_runtime():
    tools = ToolRegistry()
    tools.register(ToolSpec("browser.navigate", "Navigate", "Navigate browser",
                            frozenset({"browser.navigate"}), RiskLevel.MEDIUM, lambda _: None))
    manager = AgentManager(tools)
    root = manager.create_root("Root", "operator", "Delegate", {"screen.read", "browser.navigate"})
    requirements = SimpleNamespace(capabilities=frozenset({"computer.observe", "browser.navigation"}),
                                   permissions=frozenset({"screen.read", "browser.navigate"}),
                                   tools=frozenset({"browser.navigate"}), role="BrowserAgent")
    return manager, root, FakeRegistry(), requirements


def definition(task):
    return {"name": "Web worker", "role": "BrowserAgent", "objective": task, "task": task,
            "permissions": ["browser.navigate", "screen.read"], "tools": ["browser.navigate"],
            "subscriptions": [], "context": {}, "resource_limits": {}, "allowed_applications": [],
            "allowed_directories": [], "risk_policy": "medium"}


async def main():
    manager, root, registry, requirements = setup_runtime()
    provider = FakeProvider([
        json.dumps({"decision": "create", "agent_id": None,
                    "task": "Visit website",
                    "required_capabilities": sorted(requirements.capabilities),
                    "required_permissions": sorted(requirements.permissions),
                    "required_tools": sorted(requirements.tools)}),
        json.dumps({"agent_definition": definition("Visit website"), "python_code": "print(1)"}),
    ])

    workflow = AgentPlanningWorkflow.__new__(AgentPlanningWorkflow)
    workflow.provider, workflow.manager, workflow.registry, workflow.root = provider, manager, registry, Path(__file__).resolve().parent
    workflow._provider_lock = asyncio.Lock()
    workflow.prompt1, workflow.prompt2 = "PROMPT1", "PROMPT2"

    agent, created = await workflow.select_or_create(root.agent_id, "task-demo", "Visit website", requirements)
    print(f"Created: {created}")
    generated = Path(workflow.root) / "data/generated-agents/task-demo.py"
    if generated.exists():
        print("Generated agent file:")
        print(generated.read_text(encoding="utf-8"))
    else:
        print("No generated file found at:", generated)


if __name__ == "__main__":
    asyncio.run(main())
