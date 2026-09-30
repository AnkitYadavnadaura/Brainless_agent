"""Runtime-owned capability-gap self-skilling workflow.

The browser may authorize a *description* of a skill, but it never supplies
code or commands.  Workers are only asked to perform the bounded, structured
work and the runtime decides whether the result is evidence worth retaining.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.autonomy.vscode_worker import VscodeWorker
from app.learning import Experience, ExperienceSource, Skill, SkillStatus


@dataclass(frozen=True, slots=True)
class SkillPlanResult:
    status: str
    task_id: str
    reason: str | None = None
    worker: str | None = None
    packet: str | None = None
    skill_id: str | None = None
    validation: dict[str, Any] | None = None

    def snapshot(self) -> dict[str, Any]:
        return {key: value for key, value in {
            "status": self.status, "task_id": self.task_id, "reason": self.reason,
            "worker": self.worker, "packet": self.packet, "skill_id": self.skill_id,
            "validation": self.validation,
        }.items() if value is not None}


class CapabilityGapCoordinator:
    """Accept, execute, validate, and promote browser-authorized skill plans."""

    _VALIDATION_COMMANDS = {
        "smoke": ("python", "-m", "pytest", "-q"),
        "tests": ("python", "-m", "pytest", "-q"),
        "compile": ("python", "-m", "compileall", "-q", "app"),
    }
    _WORKERS = {"codex", "copilot", "vscode", "vscode-copilot"}
    _FORBIDDEN = {"command", "commands", "shell", "script", "code", "source_code"}

    def __init__(self, worker: VscodeWorker, learning, *, max_plan_bytes: int = 50_000) -> None:
        self.worker, self.learning, self.max_plan_bytes = worker, learning, max_plan_bytes

    async def develop(self, plan: dict[str, Any]) -> SkillPlanResult:
        try:
            data = self._validate_plan(plan)
        except (TypeError, ValueError) as error:
            task_id = str(plan.get("task_id", "invalid")) if isinstance(plan, dict) else "invalid"
            return SkillPlanResult("rejected", task_id, str(error))

        task_id = data["task_id"]
        packet = self.worker.write_coordination_packet(task_id, data["objective"], data)
        availability = self.worker.discover()
        selected = data["worker"]
        if selected == "vscode-copilot":
            selected = "copilot"
        executable = getattr(availability, selected)
        if executable is None:
            return SkillPlanResult(
                "blocked", task_id, f"{selected} worker is not installed",
                selected, str(packet),
            )

        try:
            if selected == "vscode":
                delegation = await self.worker.open_workspace()
            else:
                delegation = await self.worker.delegate(selected, data["prompt"])
            if "returncode" in delegation and delegation["returncode"] != 0:
                return SkillPlanResult(
                    "failed", task_id, "worker delegation failed", selected,
                    str(packet), validation=delegation)
            validation = await self.worker.validate(
                " ".join(self._VALIDATION_COMMANDS[data["validation"]]))
        except (RuntimeError, ValueError) as error:
            return SkillPlanResult(
                "blocked", task_id, str(error), selected, str(packet))

        if validation.get("returncode") != 0:
            return SkillPlanResult(
                "failed", task_id, "bounded validation failed", selected, str(packet),
                validation=validation)
        skill = self._record_validated(data, validation, delegation)
        return SkillPlanResult(
            "promoted", task_id, worker=selected, packet=str(packet),
            skill_id=skill.skill_id, validation=validation)

    async def run(self, plan: dict[str, Any]) -> SkillPlanResult:
        """Compatibility entry point for runtime command routers."""
        return await self.develop(plan)

    async def coordinate(self, plan: dict[str, Any]) -> SkillPlanResult:
        return await self.develop(plan)

    def _record_validated(self, data: dict[str, Any], validation: dict[str, Any],
                          delegation: dict[str, Any]) -> Skill:
        spec = data["skill"]
        experience = Experience(
            goal=data["objective"], task_type="capability_gap",
            environment={"workspace": str(self.worker.workspace)},
            plan={"task_id": data["task_id"], "worker": data["worker"]},
            success=True, verified=True, final_result="bounded validation passed",
            agents_used=(data["worker"],),
            verification_results=("allow-listed validation returned zero",),
            capabilities_used=tuple(spec["required_capabilities"]),
            failures=(), source=ExperienceSource.RUNTIME,
        )
        self.learning.experiences.store(experience)
        skill = Skill(
            name=spec["name"], description=spec["description"],
            required_capabilities=frozenset(spec["required_capabilities"]),
            required_permissions=frozenset(spec["required_permissions"]),
            workflow=tuple(spec["workflow"]),
            expected_outcomes=tuple(spec["expected_outcomes"]),
            status=SkillStatus.CANDIDATE, source_experience_id=experience.experience_id,
            evaluation={"success_rate": 1.0, "verification_rate": 1.0},
        )
        self.learning.skills.register(skill)
        self.learning.skills.set_status(
            skill.skill_id, SkillStatus.TESTED, actor="runtime",
            reason="bounded validation passed")
        self.learning.skills.approve(
            skill.skill_id, actor="browser-leader",
            reason="browser-authorized plan passed runtime validation")
        return self.learning.skills.get(skill.skill_id)

    def _validate_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        import json
        if not isinstance(plan, dict):
            raise TypeError("skill plan must be an object")
        if len(json.dumps(plan, sort_keys=True)) > self.max_plan_bytes:
            raise ValueError("skill plan is too large")
        if plan.get("authority") != "browser-leader":
            raise ValueError("skill plan must be browser-authorized")
        task_id = plan.get("task_id")
        if not isinstance(task_id, str) or not task_id or not task_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("skill plan has an invalid task ID")
        worker = plan.get("worker")
        if worker not in self._WORKERS:
            raise ValueError("skill plan selected an unsupported worker")
        validation = plan.get("validation", "smoke")
        if validation not in self._VALIDATION_COMMANDS:
            raise ValueError("skill plan selected an unsupported validation profile")
        objective = plan.get("objective")
        prompt = plan.get("prompt", objective)
        if not isinstance(objective, str) or not objective.strip() or not isinstance(prompt, str):
            raise ValueError("skill plan requires objective and prompt")
        skill = plan.get("skill")
        if not isinstance(skill, dict):
            raise ValueError("skill plan requires a structured skill")
        if self._FORBIDDEN & set(skill):
            raise ValueError("skill workflow cannot contain code or shell commands")
        required = ("name", "description", "required_capabilities",
                    "required_permissions", "workflow", "expected_outcomes")
        if any(key not in skill for key in required):
            raise ValueError("skill plan omitted required skill fields")
        if not isinstance(skill["workflow"], list) or not skill["workflow"]:
            raise ValueError("skill workflow must contain structured steps")
        for step in skill["workflow"]:
            if not isinstance(step, dict) or not isinstance(step.get("objective"), str):
                raise ValueError("skill workflow steps must be structured objectives")
            if self._FORBIDDEN & set(step):
                raise ValueError("skill workflow cannot contain code or shell commands")
            if set(step) - {"objective", "resources", "tool"}:
                raise ValueError("skill workflow contains unsupported fields")
        return {**plan, "task_id": task_id, "worker": worker,
                "validation": validation, "objective": objective,
                "prompt": prompt, "skill": skill}


# A descriptive alias for callers that use the shorter workflow name.
SelfSkillingCoordinator = CapabilityGapCoordinator
