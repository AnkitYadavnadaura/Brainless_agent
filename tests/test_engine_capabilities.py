import pytest

from app.autonomy.blender_capability import _plan_outputs, _safe_path, _script
from app.autonomy.unreal_capability import _safe_project


def test_blender_operations_are_fixed_and_paths_are_sandboxed(tmp_path):
    cube_script = _script(
        "add_cube", tmp_path / "scene.blend",
        {"name": "Wall", "location": [1, 2, 3], "scale": [4, 5, 6], "rotation": [0, 0, 1]},
    )
    assert "primitive_cube_add" in cube_script
    assert "obj.location" in cube_script
    assert "obj.scale" in cube_script
    assert "active_object.name" in cube_script
    assert "primitive_cylinder_add" in _script("add_cylinder", tmp_path / "scene.blend", {})
    assert "scene.camera" in _script("add_camera", tmp_path / "scene.blend", {})
    assert "rotation_euler" in _script(
        "transform", tmp_path / "scene.blend",
        {"location": [1, 2, 3], "scale": [2, 2, 2], "rotation": [0, 0, 1]},
    )
    assert "materials.new" in _script(
        "add_material", tmp_path / "scene.blend",
        {"name": "Blue", "color": [0.1, 0.2, 0.8]},
    )
    assert "active_object" in _script(
        "add_material", tmp_path / "scene.blend",
        {"name": "Blue", "color": [0.1, 0.2, 0.8]},
    )
    with pytest.raises(ValueError):
        _safe_path(tmp_path, "../escape.blend")


def test_unreal_projects_are_sandboxed_and_have_required_extension(tmp_path):
    assert _safe_project(tmp_path, "game.uproject").name == "game.uproject"
    with pytest.raises(ValueError):
        _safe_project(tmp_path, "../escape.uproject")
    with pytest.raises(ValueError):
        _safe_project(tmp_path, "notes.txt")


def test_plan_render_default_matches_generated_render_path(tmp_path):
    outputs = _plan_outputs(
        tmp_path,
        {
            "project": "scene.blend",
            "steps": [{"operation": "render", "args": {}}],
        },
    )
    assert outputs[-1] == tmp_path / "render.png"
