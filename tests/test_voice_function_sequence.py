import asyncio

from app.agents.manager import AgentManager
from app.agents.tools import RiskLevel, ToolRegistry, ToolSpec
from app.autonomy.executor import ActionRuntime
from app.autonomy.mission import Mission, MissionStatus
from app.autonomy.models import ComputerState
from app.autonomy.orchestrator import AutonomousRuntime
from app.autonomy.production_mission import RuntimeMissionComposer
from app.autonomy.task_engine import AutonomousTaskEngine
from app.safety.permissions import Permission


class RecordingController:
    def __init__(self):
        self.calls = []

    async def observe(self):
        return ComputerState(active_application="test")

    async def execute(self, action_type, arguments):
        self.calls.append((action_type, arguments))
        return "unused"


def test_voice_function_sequence_executes_registered_calls_in_exact_order(tmp_path):
    async def scenario():
        calls = []
        registry = ToolRegistry()
        registry.register(ToolSpec(
            "test.first", "First function", "Record the first call",
            frozenset({Permission.FILESYSTEM_READ.value}), RiskLevel.LOW,
            lambda arguments: calls.append(("test.first", arguments.copy())),
            ("value",),
        ))
        registry.register(ToolSpec(
            "test.second", "Second function", "Record the second call",
            frozenset({Permission.FILESYSTEM_READ.value}), RiskLevel.LOW,
            lambda arguments: calls.append(("test.second", arguments.copy())),
            ("value",),
        ))
        registry.register(ToolSpec(
            "test.multi", "Multi-permission function", "Record a call requiring two permissions",
            frozenset({Permission.FILESYSTEM_READ.value, Permission.FILESYSTEM_WRITE.value}),
            RiskLevel.LOW,
            lambda arguments: calls.append(("test.multi", arguments.copy())),
            ("value",),
        ))
        manager = AgentManager(registry)
        root = manager.create_root(
            "Operator", "root", "supervise",
            {Permission.SCREEN_READ.value, Permission.FILESYSTEM_READ.value,
             Permission.FILESYSTEM_WRITE.value},
        )
        controller = RecordingController()
        actions = ActionRuntime(manager, controller)
        autonomous = AutonomousRuntime(manager, actions)
        class UnexpectedAgentPlanner:
            async def select_or_create(self, *_args):
                raise AssertionError("prevalidated voice function calls must not re-enter an LLM")

        autonomous.agent_planner = UnexpectedAgentPlanner()
        engine = AutonomousTaskEngine(autonomous, actions)
        composer = RuntimeMissionComposer(autonomous, engine, root.agent_id)
        mission = Mission(
            "Run the requested functions in order",
            "voice",
            checkpoint={"function_sequence": [
                {"function": "test.second", "arguments": {"value": "B"}},
                {"function": "test.multi", "arguments": {"value": "M"}},
                {"function": "test.first", "arguments": {"value": "A"}},
            ]},
        )

        executed_task_ids = []
        original_execute = autonomous.execute
        async def tracking_execute(agent_id, task_id, *args, **kwargs):
            executed_task_ids.append(task_id)
            return await original_execute(agent_id, task_id, *args, **kwargs)
        autonomous.execute = tracking_execute

        assert await composer(mission) is MissionStatus.COMPLETED
        assert calls == [
            ("test.second", {"value": "B"}),
            ("test.multi", {"value": "M"}),
            ("test.first", {"value": "A"}),
        ]
        assert executed_task_ids
        for tid in executed_task_ids:
            assert not tid.startswith(f"{mission.mission_id}:{mission.mission_id}:")
            assert tid.startswith(f"{mission.mission_id}:")

    asyncio.run(scenario())


def test_voice_function_sequence_rejects_unregistered_or_schema_mismatched_calls(tmp_path):
    from types import SimpleNamespace
    import pytest

    from app.autonomy.production_mission import RuntimeMissionComposer

    manager = AgentManager()
    manager.create_root("Operator", "root", "supervise", set())
    actions = ActionRuntime(manager, RecordingController())
    composer = RuntimeMissionComposer(
        SimpleNamespace(analyzer=None, actions=actions), None, "root")

    with pytest.raises(KeyError, match="Unknown tool"):
        composer.graph_for(Mission(
            "invalid",
            "voice",
            checkpoint={"function_sequence": [
                {"function": "not.registered", "arguments": {}},
            ]},
        ))
    with pytest.raises(ValueError, match="Missing tool arguments: url"):
        composer.graph_for(Mission(
            "invalid",
            "voice",
            checkpoint={"function_sequence": [
                {"function": "browser.navigate", "arguments": {}},
            ]},
        ))
    with pytest.raises(ValueError, match="must not contain secrets"):
        composer.graph_for(Mission(
            "invalid",
            "voice",
            checkpoint={"function_sequence": [
                {"function": "browser.navigate", "arguments": {"url": "password=private"}},
            ]},
        ))
