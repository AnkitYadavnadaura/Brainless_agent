import pytest

from app.autonomy.capability_skilling import CapabilityGapCoordinator
from app.autonomy.vscode_worker import WorkerAvailability, VscodeWorker
from app.learning import ExperienceMemory, LearningCoordinator, SkillRegistry, SkillStatus


def plan(worker="codex"):
    return {
        "authority": "browser-leader", "task_id": "gap-1",
        "objective": "Learn the repository test workflow", "worker": worker,
        "prompt": "Implement the structured skill without adding commands.",
        "validation": "compile",
        "skill": {
            "name": "repository testing", "description": "Run repository tests",
            "required_capabilities": ["testing"], "required_permissions": [],
            "workflow": [{"objective": "Run the repository test workflow"}],
            "expected_outcomes": ["tests pass"],
        },
    }


@pytest.mark.asyncio
async def test_missing_worker_is_explicitly_blocked(tmp_path):
    worker = VscodeWorker(tmp_path)
    worker.discover = lambda: WorkerAvailability(None, None, None, "python", "git")
    learning = LearningCoordinator(ExperienceMemory(tmp_path / "e.db"),
                                   SkillRegistry(tmp_path / "s.db"))
    result = await CapabilityGapCoordinator(worker, learning).run(plan())
    assert result.status == "blocked"
    assert "not installed" in (result.reason or "")


@pytest.mark.asyncio
async def test_only_successful_bounded_validation_promotes_skill(tmp_path, monkeypatch):
    worker = VscodeWorker(tmp_path)
    worker.discover = lambda: WorkerAvailability(None, "codex", None, "python", "git")
    monkeypatch.setattr(worker, "delegate", lambda worker, prompt: _ok())
    monkeypatch.setattr(worker, "validate", lambda command: _ok())
    learning = LearningCoordinator(ExperienceMemory(tmp_path / "e.db"),
                                   SkillRegistry(tmp_path / "s.db"))
    result = await CapabilityGapCoordinator(worker, learning).develop(plan())
    assert result.status == "promoted"
    assert learning.skills.get(result.skill_id).status is SkillStatus.VERIFIED


async def _ok():
    return {"returncode": 0, "stdout": "", "stderr": ""}
