"""Automatic task routing with capability acquisition and bounded retry."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.autonomy.capability_discovery import AutomaticCapabilityService
from app.autonomy.capability_lifecycle import CapabilityStatus


@dataclass(frozen=True, slots=True)
class TaskRoute:
    goal: str
    capability_status: str
    acquired: bool
    attempts: int


class UniversalTaskRouter:
    """Try the existing runtime, acquire a missing capability, then retry once.

    The executor remains the only component allowed to perform actions. Discovery
    can add a trusted registered tool, but it cannot invoke one directly.
    """

    def __init__(self, broker, capability_service: AutomaticCapabilityService | None,
                 executor: Callable[[str], Awaitable[Any]], *, max_acquisition_attempts: int = 1) -> None:
        if max_acquisition_attempts < 0 or max_acquisition_attempts > 3:
            raise ValueError("Capability acquisition attempts must be between 0 and 3")
        self.broker = broker
        self.capability_service = capability_service
        self.executor = executor
        self.max_acquisition_attempts = max_acquisition_attempts

    async def run(self, goal: str) -> tuple[TaskRoute, Any]:
        assessment = self.broker.assess(goal)
        if assessment.status.value != "discovery_required":
            return TaskRoute(goal, assessment.status.value, False, 1), await self.executor(goal)
        if self.capability_service is None:
            raise RuntimeError("No browser reasoning provider is configured for capability discovery")
        attempts = 0
        while attempts < self.max_acquisition_attempts:
            attempts += 1
            result = await self.capability_service.ensure(goal)
            if result is None:
                break
            if result.status is CapabilityStatus.ACTIVE:
                return TaskRoute(goal, result.status.value, True, attempts), await self.executor(goal)
            if result.status is CapabilityStatus.REJECTED:
                break
        raise RuntimeError(f"Capability acquisition failed for goal: {goal}")
