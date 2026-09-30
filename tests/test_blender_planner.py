import pytest

from app.autonomy.blender_planner import (
    BlenderPlanError,
    BlenderPlanStep,
    MAX_PLAN_STEPS,
    PLAN_BATCH_SIZE,
    execution_arguments,
    plan_execution_arguments,
    parse_plan_response,
    plan_operations,
    split_plan,
)


def test_generic_plan_accepts_structured_steps_and_preserves_arguments():
    plan = parse_plan_response(
        '{"ordered_steps": ['
        '{"operation": "create_scene", "args": {}},'
        '{"operation": "add_cube", "args": {"name": "Cube",'
        '"location": [0, 0, 0], "scale": [1, 1, 1], "rotation": [0, 0, 0]}},'
        '{"operation": "transform", "args": {"location": [1, 2, 3]}},'
        '{"operation": "render", "args": {}}]}'
    )
    assert plan_operations(plan) == ("create_scene", "add_cube", "transform", "render")
    assert execution_arguments(plan[2])["location"] == [1, 2, 3]
    assert plan_execution_arguments(plan)["operation"] == "execute_plan"
    assert plan_execution_arguments(plan)["visible"] is True


def test_plan_rejects_code_unknown_operations_and_bad_start():
    with pytest.raises(BlenderPlanError):
        parse_plan_response('{"ordered_steps": [{"operation": "run_python", "args": {}}]}')
    with pytest.raises(BlenderPlanError):
        parse_plan_response('{"ordered_steps": [{"operation": "add_cube", "args": {}}]}')
    with pytest.raises(BlenderPlanError):
        parse_plan_response('{"ordered_steps": [{"operation": "create_scene", "args": "bad"}]}')
    with pytest.raises(BlenderPlanError):
        parse_plan_response(
            '{"ordered_steps": [{"operation": "create_scene", "args": {}},'
            '{"operation": "add_cube", "args": {}}]}'
        )


def test_camera_and_light_do_not_require_scale():
    plan = parse_plan_response(
        '{"ordered_steps": ['
        '{"operation": "create_scene", "args": {}},'
        '{"operation": "add_camera", "args": {"name": "Camera",'
        '"location": [8, -8, 6], "rotation": [1, 0, 0]}},'
        '{"operation": "add_light", "args": {"name": "Sun",'
        '"location": [4, -4, 8], "rotation": [0, 0, 0], "energy": 1200}}]}'
    )
    assert plan_operations(plan) == ("create_scene", "add_camera", "add_light")


def test_large_scene_plan_is_supported_within_safe_limit():
    steps = ['{"operation": "create_scene", "args": {}}']
    steps.extend(
        '{"operation": "add_cube", "args": {"name": "Object%d",'
        '"location": [0, 0, 0], "scale": [1, 1, 1], "rotation": [0, 0, 0]}}' % index
        for index in range(MAX_PLAN_STEPS - 1)
    )
    plan = parse_plan_response('{"ordered_steps": [' + ",".join(steps) + "]}")
    assert len(plan) == MAX_PLAN_STEPS


def test_large_plan_is_split_without_repeating_scene_creation():
    steps = [BlenderPlanStep("create_scene", {})]
    steps.extend(
        BlenderPlanStep(
            "add_cube",
            {
                "name": f"Object{index}",
                "location": [0, 0, 0],
                "scale": [1, 1, 1],
                "rotation": [0, 0, 0],
            },
        )
        for index in range(PLAN_BATCH_SIZE + 1)
    )
    batches = split_plan(tuple(steps), batch_size=PLAN_BATCH_SIZE)
    assert len(batches) == 2
    assert batches[0][0].operation == "create_scene"
    assert all(step.operation != "create_scene" for step in batches[1])


def test_plan_batches_keep_material_with_its_created_object():
    plan = (
        BlenderPlanStep("create_scene", {}),
        BlenderPlanStep("add_cube", {
            "name": "Wall", "location": [0, 0, 0],
            "scale": [1, 1, 1], "rotation": [0, 0, 0],
        }),
        BlenderPlanStep("add_material", {"name": "WallMaterial", "color": [1, 0, 0, 1]}),
        BlenderPlanStep("add_cube", {
            "name": "Roof", "location": [0, 0, 1],
            "scale": [1, 1, 1], "rotation": [0, 0, 0],
        }),
    )
    batches = split_plan(plan, batch_size=2)
    assert [len(batch) for batch in batches] == [3, 1]
    assert batches[0][-1].operation == "add_material"
