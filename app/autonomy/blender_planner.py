"""Validated, website-planned Blender workflows."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from app.autonomy.blender_capability import OPERATIONS

MAX_PLAN_STEPS = 180
PLAN_BATCH_SIZE = 40


class BlenderPlanError(ValueError):
    """Raised when a website response is not a safe Blender plan."""


@dataclass(frozen=True, slots=True)
class BlenderPlanStep:
    operation: str
    arguments: dict[str, Any]


def planning_prompt(objective: str) -> str:
    return (
        "Plan this Blender task. Return JSON only with an ordered_steps array. "
        "Each item must be an object with operation and args. Allowed operations "
        f"are: {sorted(OPERATIONS)}. Args must be JSON data only; never return "
        "Python, shell commands, expressions, executable code, or file paths. "
        "The first operation must be create_scene. For every primitive object "
        "(add_cube, add_sphere, add_cylinder, add_cone, add_torus, add_plane), "
        "provide a unique name plus numeric location, scale, and rotation arrays "
        "of exactly three values. Immediately follow each created object with "
        "add_material using a name and RGBA color when appearance matters. "
        "Use add_camera with location, rotation, and name, add_light with "
        "location, rotation, name, and energy, and finish visual tasks with "
        "render. Build complete scenes with spatially separated objects; do not "
        "leave everything at the origin or use default transforms. "
        "Keep the plan within 180 ordered steps. "
        f"TASK={objective}"
    )


def parse_plan_response(text: str) -> tuple[BlenderPlanStep, ...]:
    data = _json_object(text)
    steps = data.get("ordered_steps")
    if not isinstance(steps, list) or not steps or len(steps) > MAX_PLAN_STEPS:
        raise BlenderPlanError(
            f"Blender plan must contain 1 to {MAX_PLAN_STEPS} ordered steps"
        )
    plan: list[BlenderPlanStep] = []
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("operation"), str):
            raise BlenderPlanError("Every Blender plan step must contain an operation")
        operation = step["operation"].strip().lower()
        if operation not in OPERATIONS:
            raise BlenderPlanError(f"Unsupported Blender operation: {operation}")
        arguments = step.get("args", {})
        if not isinstance(arguments, dict):
            raise BlenderPlanError(f"Arguments for {operation} must be a JSON object")
        arguments = dict(arguments)
        _validate_step_arguments(operation, arguments)
        plan.append(BlenderPlanStep(operation, arguments))
    if plan[0].operation != "create_scene":
        raise BlenderPlanError("Blender plans must begin with create_scene")
    return tuple(plan)


def execution_arguments(
    step: BlenderPlanStep,
    *,
    project: str = "scene.blend",
    visible: bool = True,
    render_output: str = "scene.png",
    export_output: str = "scene.glb",
) -> dict[str, Any]:
    arguments = dict(step.arguments)
    arguments.update({"operation": step.operation, "project": project, "visible": visible})
    if step.operation == "render":
        arguments["output"] = render_output
    elif step.operation == "export":
        arguments.update({"output": export_output, "format": "GLB"})
    return arguments


def plan_execution_arguments(
    plan: tuple[BlenderPlanStep, ...],
    *,
    project: str = "scene.blend",
    visible: bool = True,
    live: bool = True,
) -> dict[str, Any]:
    return {
        "operation": "execute_plan",
        "project": project,
        "visible": visible,
        "live": live,
        "steps": [
            {"operation": step.operation, "args": dict(step.arguments)}
            for step in plan
        ],
    }


def split_plan(
    plan: tuple[BlenderPlanStep, ...],
    *,
    batch_size: int = PLAN_BATCH_SIZE,
) -> tuple[tuple[BlenderPlanStep, ...], ...]:
    if batch_size < 1:
        raise ValueError("Blender plan batch size must be positive")
    if not plan:
        raise BlenderPlanError("Cannot split an empty Blender plan")
    batches: list[tuple[BlenderPlanStep, ...]] = []
    start = 0
    dependent_operations = frozenset({"add_material", "transform", "bevel", "smooth_shade"})
    while start < len(plan):
        end = min(start + batch_size, len(plan))
        while end < len(plan) and plan[end].operation in dependent_operations:
            end += 1
        batch = plan[start:end]
        if start and batch[0].operation == "create_scene":
            raise BlenderPlanError("create_scene may only be the first step")
        batches.append(batch)
        start = end
    return tuple(batches)


def _json_object(text: str) -> dict[str, object]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise BlenderPlanError("ChatGPT returned no valid JSON object for the Blender plan")


def plan_operations(plan: tuple[BlenderPlanStep, ...]) -> tuple[str, ...]:
    return tuple(step.operation for step in plan)


_PRIMITIVES = frozenset({
    "add_cube", "add_sphere", "add_cylinder", "add_cone", "add_torus", "add_plane",
})


def _validate_step_arguments(operation: str, arguments: dict[str, Any]) -> None:
    if operation in _PRIMITIVES:
        _require_name_and_vectors(operation, arguments, ("location", "scale", "rotation"))
    elif operation == "add_camera":
        _require_name_and_vectors(operation, arguments, ("location", "rotation"))
    elif operation == "add_light":
        _require_name_and_vectors(operation, arguments, ("location", "rotation"))
        if isinstance(arguments.get("energy"), bool) or not isinstance(
            arguments.get("energy", 1200), (int, float)
        ):
            raise BlenderPlanError("add_light energy must be numeric")
    elif operation == "add_material":
        if not isinstance(arguments.get("name"), str) or not arguments["name"].strip():
            raise BlenderPlanError("add_material requires a non-empty name")
        color = arguments.get("color")
        if not isinstance(color, list) or len(color) not in (3, 4):
            raise BlenderPlanError("add_material color must contain 3 or 4 values")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in color):
            raise BlenderPlanError("add_material color must be numeric")


def _require_name_and_vectors(
    operation: str,
    arguments: dict[str, Any],
    vector_keys: tuple[str, ...],
) -> None:
    if not isinstance(arguments.get("name"), str) or not arguments["name"].strip():
        raise BlenderPlanError(f"{operation} requires a non-empty name")
    for key in vector_keys:
        value = arguments.get(key)
        if (
            not isinstance(value, list)
            or len(value) != 3
            or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value)
        ):
            raise BlenderPlanError(f"{operation} requires numeric {key} with 3 values")
