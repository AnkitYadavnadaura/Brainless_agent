from app.autonomy.blender_capability import OPERATIONS, _script
from app.autonomy.blender_workflows import CAR_MODEL_SINGLE_OPERATION, CAR_MODEL_WORKFLOW, car_workflow_arguments


def test_car_workflow_contains_complete_consecutive_operations():
    assert CAR_MODEL_WORKFLOW.operations[0] == "create_scene"
    assert "create_car_body" in CAR_MODEL_WORKFLOW.operations
    assert "create_car_wheels" in CAR_MODEL_WORKFLOW.operations
    assert CAR_MODEL_WORKFLOW.operations[-2:] == ("render", "export")
    assert set(CAR_MODEL_WORKFLOW.operations) <= OPERATIONS
    assert set(CAR_MODEL_SINGLE_OPERATION.operations) <= OPERATIONS


def test_car_workflow_arguments_are_structured_not_shell_commands():
    arguments = car_workflow_arguments()
    assert len(arguments) == len(CAR_MODEL_WORKFLOW.operations)
    assert arguments[1]["operation"] == "create_car_body"
    assert arguments[-1]["output"] == "car.glb"
    assert all(";" not in str(item) for item in arguments)


def test_car_scripts_include_expected_scene_parts(tmp_path):
    project = tmp_path / "car.blend"
    assert "Car_Body" in _script("create_car_body", project, {})
    assert "Car_Wheel" in _script("create_car_wheels", project, {})
    assert "Car_Headlight" in _script("create_car_lights", project, {})
    assert "Car_Body" in _script("create_car", project, {})
