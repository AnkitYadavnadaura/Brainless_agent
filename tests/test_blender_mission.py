from pathlib import Path

import pytest

from app.autonomy.blender_mission import BlenderMissionAdapter
from app.autonomy.mission import Mission
from app.autonomy.universal_mission import MissionStep


@pytest.mark.asyncio
async def test_blender_adapter_executes_structured_operations_and_verifies_output(tmp_path):
    project = tmp_path / "scene.blend"
    calls = []

    async def invoke(tool_id, arguments):
        calls.append((tool_id, arguments))
        project.write_bytes(b"blend")
        return str(project)

    adapter = BlenderMissionAdapter(invoke=invoke, project="scene.blend")
    mission = Mission("create a cube", "test")
    mission.current_state["blender_operations"] = [
        {"operation": "create_scene"},
        {"operation": "add_cube", "args": {
            "name": "Cube", "location": [0, 0, 0],
            "scale": [1, 1, 1], "rotation": [0, 0, 0],
        }},
    ]
    step = MissionStep("execute-blender-scene", mission.goal, frozenset({"blender.scene_edit"}))

    result = await adapter.execute(step, mission)

    assert result.success
    assert calls[0][0] == "blender.scene"
    assert calls[0][1]["operation"] == "execute_plan"
    assert Path(result.observations["project"]) == project
    assert (await adapter.verify(step, result, mission)) == (
        True, "Blender project and requested operations verified"
    )


@pytest.mark.asyncio
async def test_blender_adapter_rejects_code_and_reports_missing_output():
    async def invoke(_tool_id, _arguments):
        return "missing.blend"

    adapter = BlenderMissionAdapter(invoke=invoke)
    mission = Mission('{"ordered_steps":[{"operation":"run_python","args":{"code":"x"}}]}', "test")
    step = MissionStep("execute-blender-scene", mission.goal, frozenset())

    result = await adapter.execute(step, mission)

    assert not result.success
    assert "Unsupported Blender operation" in (result.error or "")
