"""Trusted multi-step Blender workflows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BlenderWorkflow:
    workflow_id: str
    operations: tuple[str, ...]
    description: str


CAR_MODEL_WORKFLOW = BlenderWorkflow(
    "car-model",
    (
        "create_scene",
        "create_car_body",
        "create_car_wheels",
        "create_car_windows",
        "create_car_lights",
        "apply_car_materials",
        "setup_car_camera",
        "setup_car_lighting",
        "render",
        "export",
    ),
    "Create a complete low-poly car model, render it, and save the Blender project.",
)

CAR_MODEL_SINGLE_OPERATION = BlenderWorkflow(
    "car-model-single-operation",
    ("create_scene", "create_car", "render", "export"),
    "Create a complete car model in one trusted Blender operation sequence.",
)


def car_workflow_arguments(project: str = "car.blend", render: str = "car.png",
                           export: str = "car.glb") -> tuple[dict[str, Any], ...]:
    return tuple(
        {"operation": operation, "project": project,
         **({"output": render} if operation == "render" else {}),
         **({"output": export, "format": "GLB"} if operation == "export" else {})}
        for operation in CAR_MODEL_WORKFLOW.operations
    )
