from app.autonomy.automation_catalog import AUTOMATIONS, AutomationCatalog
from app.autonomy.automation_runner import AutomationRunner, all_permissions
from app.agents.manager import AgentManager
from app.agents.tools import RiskLevel, ToolRegistry, ToolSpec


def test_catalog_contains_exactly_one_hundred_automations():
    assert len(AUTOMATIONS) == 100
    assert len({item.automation_id for item in AUTOMATIONS}) == 100


def test_catalog_covers_video_blender_and_unreal():
    catalog = AutomationCatalog()
    assert len([item for item in catalog.all() if item.category == "video"]) == 15
    assert len([item for item in catalog.all() if item.category == "blender"]) == 15
    assert len([item for item in catalog.all() if item.category == "unreal"]) == 15
    assert catalog.get("blender-add-cube").external_dependency == "blender"
    assert catalog.get("unreal-create-blueprint").external_dependency == "unreal"


def test_reasoning_prompt_contains_only_catalog_metadata():
    catalog = AutomationCatalog()
    prompt = catalog.reasoning_prompt("create a 3d object", catalog.matching("blender"))
    assert "executable code" in prompt
    assert "blender-add-cube" in prompt


def test_catalog_runner_executes_registered_tools_sequentially():
    calls = []

    async def handler(arguments):
        calls.append(arguments["value"])
        return arguments["value"] * 2

    tools = ToolRegistry()
    tools.register(ToolSpec(
        "test.tool", "Test", "Test tool", frozenset(), RiskLevel.LOW, handler, ("value",), "number",
    ))
    manager = AgentManager(tools)
    parent = manager.create_root("Root", "orchestrator", "test", all_permissions())
    catalog = AutomationCatalog((
        AUTOMATIONS[0].__class__(
            "test-1", "Test one", "test", "test one", frozenset({"test.tool"}), frozenset(),
        ),
        AUTOMATIONS[0].__class__(
            "test-2", "Test two", "test", "test two", frozenset({"test.tool"}), frozenset(),
        ),
    ))

    import asyncio
    results = asyncio.run(AutomationRunner(manager, catalog).run_all(
        parent.agent_id, {"test-1": {"value": 1}, "test-2": {"value": 2}},
    ))

    assert [result.status for result in results] == ["completed", "completed"]
    assert [result.output for result in results] == [2, 4]
    assert calls == [1, 2]


def test_catalog_runner_reports_missing_tools_and_inputs():
    tools = ToolRegistry()
    manager = AgentManager(tools)
    parent = manager.create_root("Root", "orchestrator", "test", all_permissions())
    catalog = AutomationCatalog((AUTOMATIONS[0],))

    import asyncio
    results = asyncio.run(AutomationRunner(manager, catalog).run_all(parent.agent_id))

    assert results[0].status == "blocked"
    assert "desktop.launch" in (results[0].error or "")
