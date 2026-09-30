import asyncio
from types import SimpleNamespace

from app.autonomy.capability_lifecycle import CapabilityStatus
from run_dashboard import (
    _activate_blender_voice_tool,
    _activate_unreal_voice_tool,
    dashboard_token,
)


def test_dashboard_generates_strong_per_run_token_when_unconfigured():
    first, generated = dashboard_token({})
    second, second_generated = dashboard_token({})
    assert generated and second_generated
    assert len(first) >= 16 and first != second


def test_dashboard_honors_valid_configured_token_and_rejects_short_value():
    configured = "owner-configured-token"
    assert dashboard_token({"BRAINLESS_DASHBOARD_TOKEN": configured}) == (configured, False)

    try:
        dashboard_token({"BRAINLESS_DASHBOARD_TOKEN": "short"})
    except ValueError as error:
        assert "at least 16" in str(error)
    else:
        raise AssertionError("short dashboard token was accepted")


def test_blender_voice_tool_is_promoted_before_voice_inventory(monkeypatch):
    async def scenario():
        calls = []

        class Lifecycle:
            async def acquire(self, candidate):
                calls.append(("acquire", candidate))
                return SimpleNamespace(status=CapabilityStatus.VALIDATED, failure=None)

            async def promote(self, candidate):
                calls.append(("promote", candidate))

        monkeypatch.setattr("run_dashboard.find_blender", lambda: "blender.exe")
        application = SimpleNamespace(capability_lifecycle=Lifecycle())
        assert await _activate_blender_voice_tool(application)
        assert [operation for operation, _ in calls] == ["acquire", "promote"]
        candidate = calls[0][1]
        assert candidate.tool_id == "blender.scene"
        assert set(candidate.input_schema) == {
            "operation", "project", "visible", "live", "steps",
        }

    asyncio.run(scenario())


def test_blender_voice_tool_is_not_advertised_when_application_is_unavailable(monkeypatch):
    async def scenario():
        class Lifecycle:
            async def acquire(self, _candidate):
                raise AssertionError("must not acquire Blender when executable is absent")

        monkeypatch.setattr("run_dashboard.find_blender", lambda: None)
        application = SimpleNamespace(capability_lifecycle=Lifecycle())
        assert not await _activate_blender_voice_tool(application)

    asyncio.run(scenario())


def test_unreal_voice_tool_is_promoted_when_editor_is_available(monkeypatch):
    async def scenario():
        calls = []

        class Lifecycle:
            async def acquire(self, candidate):
                calls.append(("acquire", candidate))
                return SimpleNamespace(status=CapabilityStatus.VALIDATED, failure=None)

            async def promote(self, candidate):
                calls.append(("promote", candidate))

        monkeypatch.setattr("run_dashboard.find_unreal_editor", lambda: "UnrealEditor.exe")
        application = SimpleNamespace(capability_lifecycle=Lifecycle())
        assert await _activate_unreal_voice_tool(application)
        assert [operation for operation, _ in calls] == ["acquire", "promote"]
        assert calls[0][1].tool_id == "unreal.editor"

    asyncio.run(scenario())
