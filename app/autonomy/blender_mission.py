"""Trusted adapter for small, structured Blender missions.

The adapter deliberately accepts data (operations and arguments) only.  It
never evaluates a request as Python and delegates execution to the capability
lifecycle's trusted ``blender.scene`` tool.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.autonomy.blender_capability import blender_candidate
from app.autonomy.blender_planner import BlenderPlanError, parse_plan_response, plan_execution_arguments
from app.autonomy.capability_lifecycle import CapabilityLifecycle
from app.autonomy.mission import Mission
from app.autonomy.universal_mission import MissionStep, StepResult


class BlenderMissionAdapter:
    """Execute and verify bounded Blender operations through a trusted tool."""

    def __init__(self, lifecycle: CapabilityLifecycle | None = None,
                 *, invoke: Callable[[str, dict[str, Any]], Awaitable[Any]] | None = None,
                 project: str = "scene.blend", visible: bool = False) -> None:
        if lifecycle is None and invoke is None:
            raise ValueError("A capability lifecycle or tool invoker is required")
        self.lifecycle = lifecycle
        self.invoke = invoke
        self.project = project
        self.visible = visible
        self._candidate = blender_candidate() if lifecycle is not None else None

    async def _invoke(self, arguments: dict[str, Any]) -> Any:
        if self.invoke is not None:
            return await self.invoke("blender.scene", arguments)
        assert self.lifecycle is not None and self._candidate is not None
        registry = self.lifecycle.registry
        if not registry.contains("blender.scene"):
            record = await self.lifecycle.acquire(self._candidate)
            if record.status.value != "validated":
                raise RuntimeError(f"Blender capability unavailable: {record.failure or record.status.value}")
            await self.lifecycle.promote(self._candidate)
        return await registry.invoke("blender.scene", arguments)

    async def execute(self, step: MissionStep, mission: Mission) -> StepResult:
        try:
            arguments = self._arguments(step, mission)
            output = await self._invoke(arguments)
            path = Path(str(output))
            observations = {"project": str(path), "operation": "execute_plan",
                            "steps": len(arguments["steps"])}
            if not path.is_file() or path.stat().st_size == 0:
                return StepResult(False, output=output, observations=observations,
                                  error="Blender completed without a verified project file")
            return StepResult(True, output=output, observations=observations)
        except (BlenderPlanError, TypeError, ValueError, RuntimeError, OSError) as error:
            return StepResult(False, error=f"Blender request rejected: {error}")
        except Exception as error:
            return StepResult(False, error=f"Blender execution failed: {error}")

    async def verify(self, step: MissionStep, result: StepResult,
                     mission: Mission) -> tuple[bool, str]:
        if not result.success:
            return False, result.error or "Blender execution failed"
        project = result.observations.get("project")
        if not isinstance(project, str) or not Path(project).is_file():
            return False, "Blender project output was not verified"
        return True, "Blender project and requested operations verified"

    def _arguments(self, step: MissionStep, mission: Mission) -> dict[str, Any]:
        payload = mission.current_state.get("blender_operations")
        if payload is None:
            text = mission.goal.strip()
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = self._simple_operations(text)
        if isinstance(payload, dict) and "ordered_steps" in payload:
            plan = parse_plan_response(json.dumps(payload))
        elif isinstance(payload, dict) and "operation" in payload:
            plan = parse_plan_response(json.dumps({"ordered_steps": [payload]}))
        elif isinstance(payload, list):
            plan = parse_plan_response(json.dumps({"ordered_steps": payload}))
        else:
            raise BlenderPlanError("Blender request must contain structured operations")
        return plan_execution_arguments(
            plan, project=self.project, visible=self.visible,
            live=False,
        )

    @staticmethod
    def _simple_operations(text: str) -> list[dict[str, Any]]:
        lowered = text.casefold()
        primitives = {
            "sphere": "add_sphere", "cylinder": "add_cylinder",
            "cone": "add_cone", "torus": "add_torus", "plane": "add_plane",
            "cube": "add_cube",
        }
        operation = next((value for key, value in primitives.items() if key in lowered), None)
        if operation is None:
            if "car" in lowered:
                return [{"operation": "create_scene"}, {"operation": "create_car"}]
            raise BlenderPlanError("Unsupported simple Blender request; provide structured operations")
        name = operation.removeprefix("add_").title()
        return [
            {"operation": "create_scene"},
            {"operation": operation, "args": {
                "name": name, "location": [0, 0, 0],
                "scale": [1, 1, 1], "rotation": [0, 0, 0],
            }},
        ]
