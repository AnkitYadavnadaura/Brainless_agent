"""Production composition of persisted missions and the verified task engine."""
from __future__ import annotations

from app.autonomy.models import ActionProposal
from app.autonomy.mission import Mission, MissionStatus
from app.autonomy.task_graph import GraphTask, TaskGraph
from app.autonomy.task_runner import TaskEngineMissionRunner
from app.autonomy.governor import MissionContract
from app.safety.redaction import redact


class VerifiedMissionCriterion:
    """Requires at least one successful runtime-audited action for this mission."""
    def __init__(self, actions, mission_id: str) -> None:
        self.actions, self.mission_id = actions, mission_id

    async def verify(self, _) -> tuple[bool, str]:
        records = [item for item in self.actions.audit if item.task_id.startswith(self.mission_id)]
        passed = bool(records) and records[-1].error is None
        return passed, "No verified runtime action completed for the mission"


class PlannedFunctionDecisionProvider:
    """Return one prevalidated function call without asking a model to replan it."""

    def __init__(self, node: GraphTask) -> None:
        if node.tool is None or node.arguments is None:
            raise ValueError("Planned function step is missing its registered function or arguments")
        self.node = node
        self.tool_id = node.tool
        self.arguments = node.arguments
        self._emitted = False

    async def next_action(self, _) -> ActionProposal | None:
        if self._emitted:
            return None
        self._emitted = True
        return ActionProposal(
            self.tool_id,
            self.arguments,
            self.node.objective,
        )


class RuntimeMissionComposer:
    """Builds a least-privilege single-objective graph from runtime analysis."""
    def __init__(self, autonomous, task_engine, root_agent_id: str) -> None:
        self.autonomous, self.actions = autonomous, autonomous.actions
        self.runner = TaskEngineMissionRunner(task_engine, root_agent_id, self.graph_for,
                                               self.decision_provider, self.criteria_for)

    def graph_for(self, mission: Mission) -> TaskGraph:
        sequence = mission.checkpoint.get("function_sequence")
        if sequence is not None:
            return self._graph_for_function_sequence(mission, sequence)

        requirements = self.autonomous.analyzer.analyze(mission.goal)
        graph = TaskGraph()
        previous = None
        for index, tool_id in enumerate(sorted(requirements.tools)):
            tool = self.actions.manager.tools.get(tool_id)
            # Mission-scoped IDs prevent cross-mission authority, audit, and
            # dashboard-correlation collisions.
            task_id = f"{mission.mission_id}:objective:{index}"
            graph.add(GraphTask(task_id, mission.goal,
                                dependencies={previous} if previous else set(),
                                capabilities=requirements.capabilities,
                                permissions=tool.required_permissions,
                                resources=frozenset({tool_id.split(".")[0]}),
                                tool=tool_id, priority=mission.priority))
            previous = task_id
        if not graph.tasks:
            raise ValueError("Mission requires no executable capability; user clarification is required")
        permissions = frozenset(permission for task in graph.tasks.values() for permission in task.permissions)
        budget = mission.resource_policy if isinstance(mission.resource_policy, dict) else {}
        self.actions.governor.register(MissionContract(
            mission.mission_id,
            allowed_tools=frozenset(task.tool for task in graph.tasks.values() if task.tool),
            allowed_permissions=permissions,
            forbidden_actions=frozenset(mission.current_state.get("forbidden_actions", ())),
            max_actions=int(budget.get("max_actions", 1_000)),
            max_failures=int(budget.get("max_failures", 10)),
            minimum_confidence=float(budget.get("minimum_confidence", .5))), set(graph.tasks))
        return graph

    def _graph_for_function_sequence(self, mission: Mission, sequence) -> TaskGraph:
        if not isinstance(sequence, list) or not sequence or len(sequence) > 24:
            raise ValueError("Mission function sequence must contain 1-24 registered function calls")
        graph = TaskGraph()
        previous = None
        for index, call in enumerate(sequence):
            if not isinstance(call, dict) or set(call) != {"function", "arguments"}:
                raise ValueError("Mission function sequence contains an invalid call")
            tool_id, arguments = call["function"], call["arguments"]
            if not isinstance(tool_id, str) or not isinstance(arguments, dict):
                raise ValueError("Mission function sequence contains invalid function arguments")
            if redact(arguments) != arguments:
                raise ValueError("Mission function arguments must not contain secrets")
            tool = self.actions.manager.tools.get(tool_id)
            if not tool.required_permissions:
                raise ValueError(f"Function {tool_id} has no runtime permission contract")
            arguments = self.actions.manager.tools.normalize_arguments(tool_id, arguments)
            task_id = f"{mission.mission_id}:function:{index}"
            graph.add(GraphTask(
                task_id,
                f"Call {tool_id} for the voice task: {mission.goal}",
                dependencies={previous} if previous else set(),
                capabilities=frozenset({"computer.observe"}),
                permissions=tool.required_permissions,
                resources=frozenset({tool_id.split(".")[0]}),
                tool=tool_id,
                arguments=arguments,
                priority=mission.priority,
                max_retries=0,
            ))
            previous = task_id

        permissions = frozenset(
            permission for node in graph.tasks.values() for permission in node.permissions)
        budget = mission.resource_policy if isinstance(mission.resource_policy, dict) else {}
        self.actions.governor.register(MissionContract(
            mission.mission_id,
            allowed_tools=frozenset(node.tool for node in graph.tasks.values() if node.tool),
            allowed_permissions=permissions,
            forbidden_actions=frozenset(mission.current_state.get("forbidden_actions", ())),
            max_actions=len(graph.tasks),
            max_failures=len(graph.tasks),
            minimum_confidence=float(budget.get("minimum_confidence", .5))), set(graph.tasks))
        return graph

    @staticmethod
    def decision_provider(node: GraphTask):
        return PlannedFunctionDecisionProvider(node) if node.arguments is not None else None

    def criteria_for(self, mission: Mission):
        return (VerifiedMissionCriterion(self.actions, mission.mission_id),)

    async def __call__(self, mission: Mission):
        status = await self.runner(mission)
        observation = next((self.actions.result_for(record.action_id)
                            for record in reversed(self.actions.audit)
                            if record.task_id.startswith(mission.mission_id)
                            and record.tool == "browser.observe" and record.error is None), None)
        if observation and observation.success and isinstance(observation.output, dict):
            mission.checkpoint["browser_observation"] = observation.output
        if status is not MissionStatus.COMPLETED:
            failure = next((record.error for record in reversed(self.actions.audit)
                            if record.task_id.startswith(mission.mission_id) and record.error), None)
            if failure:
                mission.checkpoint["last_error"] = failure
        else:
            mission.checkpoint.pop("last_error", None)
        return status
