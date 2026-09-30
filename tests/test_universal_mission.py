from __future__ import annotations

import pytest

from app.autonomy.mission import MissionStatus, MissionStore
from app.autonomy.universal_mission import (
    BrowserTeamMissionAdapter,
    GeneralCliMissionAdapter,
    MissionIntent,
    MissionStep,
    StepResult,
    UniversalMissionCoordinator,
    plan_request,
    understand_request,
)
from app.autonomy.environment import EnvironmentSnapshot
from app.autonomy.mission import Mission


def test_understanding_routes_simple_and_collaborative_tasks():
    youtube = understand_request("play Believer by Imagine Dragons on YouTube")
    assert youtube.intent is MissionIntent.YOUTUBE_PLAY
    assert not youtube.needs_clarification
    assert not youtube.needs_browser_team

    generic = understand_request("play music on youtube")
    assert generic.needs_clarification

    creative = understand_request("multiple agents review a complex Blender game scene")
    assert creative.intent is MissionIntent.BLENDER_SCENE
    assert creative.needs_browser_team


def test_plan_contains_bounded_verifiable_youtube_steps():
    plan = plan_request(understand_request("play Believer on youtube"))
    assert [step.step_id for step in plan.steps] == [
        "open-youtube-music", "select-youtube-content", "verify-youtube-playback"
    ]
    assert plan.steps[-1].verification == {"media_playing": True}


class Adapter:
    def __init__(self):
        self.executed = []

    async def execute(self, step, mission):
        self.executed.append(step.step_id)
        return StepResult(True, observations={"media_playing": True})

    async def verify(self, step, result, mission):
        return True, "verified"


@pytest.mark.asyncio
async def test_coordinator_persists_verified_completion(tmp_path):
    adapter = Adapter()
    coordinator = UniversalMissionCoordinator(
        MissionStore(tmp_path / "missions.json"),
        {MissionIntent.YOUTUBE_PLAY: adapter},
        ask=lambda _: _answer("Believer by Imagine Dragons"),
    )
    mission = await coordinator.create("play music on youtube")
    assert mission.status is MissionStatus.PLANNING
    assert mission.current_state["understanding"]["intent"] == "youtube_play"

    completed = await coordinator.execute(mission)
    assert completed.status is MissionStatus.COMPLETED
    assert adapter.executed == [
        "open-youtube-music", "select-youtube-content", "verify-youtube-playback"
    ]
    saved = coordinator.store.load(mission.mission_id)
    assert saved is not None and saved.status is MissionStatus.COMPLETED


@pytest.mark.asyncio
async def test_browser_team_adapter_returns_structured_verified_result():
    calls = []

    async def runner(goal):
        calls.append(goal)
        return {"status": "completed", "evidence": ["provider-review"]}

    adapter = BrowserTeamMissionAdapter(runner)
    from app.autonomy.mission import Mission
    current = Mission(goal="Research Blender lighting options", owner="test")
    step = plan_request(understand_request("research Blender lighting options")).steps[0]
    result = await adapter.execute(step, current)
    verified, detail = await adapter.verify(step, result, current)

    assert verified is True
    assert "completed" in detail
    assert calls == [current.goal]
    assert result.observations["collaboration"] == "browser-team"


async def _answer(value):
    return value


def test_checksum_requests_have_deterministic_bounded_plan():
    understanding = understand_request("create a SHA-256 checksum report for input.bin")
    assert understanding.required_capabilities == frozenset({"cli.checksum", "filesystem.write_report"})
    assert [step.step_id for step in plan_request(understanding).steps] == [
        "discover-checksum-cli", "write-checksum-report", "verify-checksum-report"
    ]


@pytest.mark.asyncio
async def test_checksum_adapter_rejects_paths_outside_workspace(tmp_path):
    adapter = GeneralCliMissionAdapter(
        EnvironmentSnapshot("nt", str(tmp_path), {"sha256sum": "sha256sum"}, {}, False, False, False),
        tmp_path,
    )
    mission = Mission("create checksum report for ..\\secret.txt", "user")
    result = await adapter.execute(
        MissionStep("write-checksum-report", mission.goal, frozenset(), {"report_created": True}), mission)
    assert not result.success
    assert "workspace" in (result.error or "")
