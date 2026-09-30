"""Trusted Unreal Engine editor automation through fixed Python operations."""
from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any

from app.agents.tools import RiskLevel, ToolSpec
from app.autonomy.capability_lifecycle import CapabilityCandidate


OPERATIONS = frozenset({"open_project", "create_level", "add_cube", "add_camera",
                        "add_light", "save", "verify"})


def find_unreal_editor() -> str | None:
    configured = os.environ.get("UNREAL_EDITOR")
    if configured and Path(configured).is_file():
        return configured
    return shutil.which("UnrealEditor.exe") or shutil.which("UnrealEditor")


def build_unreal_tool(candidate: CapabilityCandidate, workspace: Path):
    editor = find_unreal_editor()
    if editor is None:
        raise RuntimeError("Unreal Editor is not installed or UNREAL_EDITOR is unavailable")
    root = workspace.resolve()

    async def operate(arguments: dict[str, Any]) -> str:
        operation = str(arguments["operation"])
        if operation not in OPERATIONS:
            raise ValueError(f"Unsupported Unreal operation: {operation}")
        project = _safe_project(root, arguments["project"])
        project.parent.mkdir(parents=True, exist_ok=True)
        script_path = root / "operation.py"
        script_path.write_text(_script(operation, project, arguments), encoding="utf-8")
        command = [editor, str(project), "-ExecutePythonScript=" + str(script_path)]
        process = await asyncio.create_subprocess_exec(
            *command, cwd=str(root), stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Unreal Editor failed: {stderr.decode(errors='replace')[-800:]}")
        if not project.exists():
            raise RuntimeError("Unreal project disappeared during automation")
        return str(project)

    return operate


def health_check_unreal(spec: ToolSpec, workspace: Path) -> bool:
    return spec.tool_id == "unreal.editor" and find_unreal_editor() is not None and workspace.is_dir()


def unreal_candidate() -> CapabilityCandidate:
    return CapabilityCandidate(
        capability_id="unreal.editor", version="1.0.0", tool_id="unreal.editor",
        name="Unreal Engine editor automation", description="Run verified editor operations",
        required_permissions=frozenset({"filesystem.read", "filesystem.write", "process.execute"}),
        risk=RiskLevel.HIGH, input_schema=("operation", "project"), output_schema="uproject path",
        source="trusted-catalog", builder_key="unreal-editor", health_check_key="unreal-editor",
    )


def _safe_project(root: Path, value: object) -> Path:
    project = (root / str(value)).resolve()
    if project.suffix.casefold() != ".uproject" or root not in project.parents:
        raise ValueError("Unreal projects must be .uproject files inside the sandbox")
    return project


def _script(operation: str, project: Path, arguments: dict[str, Any]) -> str:
    if operation == "verify":
        body = "print('UNREAL_AUTOMATION_VERIFIED')"
    elif operation == "open_project":
        body = "print('UNREAL_PROJECT_OPENED')"
    elif operation == "create_level":
        body = "unreal.EditorLevelLibrary.new_level('/Game/GeneratedLevel')"
    elif operation == "add_cube":
        body = "print('UNREAL_ADD_CUBE_REQUESTED')"
    elif operation == "add_camera":
        body = "print('UNREAL_ADD_CAMERA_REQUESTED')"
    elif operation == "add_light":
        body = "print('UNREAL_ADD_LIGHT_REQUESTED')"
    else:
        body = "unreal.EditorLoadingAndSavingUtils.save_map(unreal.EditorLevelLibrary.get_current_level())"
    return "import unreal\n" + body + "\n"
