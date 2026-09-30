"""Tests for Blender voice assistant parsing, bare plan normalization, and live execution arguments."""
import json
import pytest

from app.voice.conversation import BrowserVoiceAssistant, VoiceConversationError
from app.autonomy.blender_capability import blender_candidate
from app.autonomy.blender_planner import plan_execution_arguments, BlenderPlanStep


@pytest.fixture
def blender_inventory():
    return {
        "blender.scene": {
            "arguments": ["operation", "project", "visible", "live", "steps"],
            "category": "creative",
            "description": "Blender scene automation",
            "destructive": False,
            "function": "blender.scene",
            "permissions": ["filesystem.read", "filesystem.write", "process.execute"],
            "reversible": True,
        }
    }


def test_bare_ordered_steps_converted_to_blender_scene_execution(blender_inventory):
    payload = json.dumps({
        "ordered_steps": [
            {"operation": "create_scene", "args": {}},
            {"operation": "add_cube", "args": {"name": "Wall", "location": [0, 0, 1], "scale": [10, 20, 3], "rotation": [0, 0, 0]}},
            {"operation": "render", "args": {}},
        ]
    })
    decision = BrowserVoiceAssistant.parse(payload, blender_inventory)
    assert decision["action"] == "execute"
    assert len(decision["sequence"]) == 1
    call = decision["sequence"][0]
    assert call["function"] == "blender.scene"
    args = call["arguments"]
    assert args["operation"] == "execute_plan"
    assert args["visible"] is True
    assert args["live"] is True
    assert len(args["steps"]) == 3


def test_bare_steps_list_converted_to_blender_scene_execution(blender_inventory):
    payload = json.dumps({
        "goal": "Build house in Blender",
        "project": "house.blend",
        "steps": [
            {"operation": "create_scene", "args": {}},
            {"operation": "add_cube", "args": {"name": "Roof", "location": [0, 0, 4], "scale": [11, 21, 1], "rotation": [0, 0, 0]}},
        ]
    })
    decision = BrowserVoiceAssistant.parse(payload, blender_inventory)
    assert decision["action"] == "execute"
    assert decision["goal"] == "Build house in Blender"
    call = decision["sequence"][0]
    assert call["function"] == "blender.scene"
    assert call["arguments"]["project"] == "house.blend"
    assert call["arguments"]["live"] is True
    assert call["arguments"]["visible"] is True


def test_blender_scene_with_large_step_sequence_exceeding_2000_chars(blender_inventory):
    steps = [{"operation": "create_scene", "args": {}}]
    for i in range(20):
        steps.append({
            "operation": "add_cube",
            "args": {
                "name": f"House_Detail_Segment_{i}",
                "location": [float(i), float(i * 2), 1.5],
                "scale": [2.0, 1.5, 0.5],
                "rotation": [0.0, 0.0, 0.785],
            }
        })
    steps.append({"operation": "render", "args": {"output": "house_render.png"}})

    payload = json.dumps({
        "action": "execute",
        "goal": "Construct a 10 by 20 house with multiple windows and gates in Blender",
        "sequence": [{
            "function": "blender.scene",
            "arguments": {
                "steps": steps,
            }
        }]
    })

    assert len(payload) > 2500, "Payload should exceed previous _MAX_TEXT limit of 2000"
    decision = BrowserVoiceAssistant.parse(payload, blender_inventory)
    assert decision["action"] == "execute"
    args = decision["sequence"][0]["arguments"]
    assert args["live"] is True
    assert args["visible"] is True
    assert args["operation"] == "execute_plan"
    assert args["project"] == "scene.blend"
    assert len(args["steps"]) == len(steps)


def test_blender_candidate_specifies_live_true_in_description():
    candidate = blender_candidate()
    assert "live=true" in candidate.description
    assert "visible=true" in candidate.description


def test_plan_execution_arguments_defaults_live_to_true():
    plan = (
        BlenderPlanStep("create_scene", {}),
        BlenderPlanStep("add_cube", {"name": "Cube", "location": [0, 0, 0], "scale": [1, 1, 1], "rotation": [0, 0, 0]}),
    )
    args = plan_execution_arguments(plan)
    assert args["live"] is True
    assert args["visible"] is True
    assert args["operation"] == "execute_plan"
