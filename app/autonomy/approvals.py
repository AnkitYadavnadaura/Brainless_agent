"""Durable human approval authority for suspended runtime actions."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from pathlib import Path
from threading import RLock
from typing import Any

from app.autonomy.models import ComputerAction
from app.safety.permissions import ApprovalMode, can_remember_tool
from app.safety.redaction import redact


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    approval_id: str
    mission_id: str
    task_id: str
    agent_id: str
    tool: str
    reason: str
    risk_level: str
    permission: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_at: str = ""
    decided_at: str | None = None
    decided_by: str | None = None
    permissions: tuple[str, ...] = ()
    tool_name: str = ""
    can_remember: bool = False
    remembered: bool = False


class ApprovalStore:
    """Atomic metadata-only persistence; action arguments are intentionally excluded."""
    def __init__(self, path: Path) -> None:
        self.path, self._lock = path, RLock()

    def put(self, request: ApprovalRequest) -> None:
        with self._lock:
            data = self._read(); payload = asdict(request); payload["status"] = request.status.value
            data[request.approval_id] = payload; self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, sort_keys=True), encoding="utf-8"); temporary.replace(self.path)

    def get(self, approval_id: str) -> ApprovalRequest | None:
        data = self._read().get(approval_id)
        return _request(data) if data else None

    def all(self) -> tuple[ApprovalRequest, ...]:
        return tuple(_request(item) for item in self._read().values())

    def _read(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}


class ApprovalSystem:
    """Runtime waits for a human decision; the dashboard can only submit that decision."""
    def __init__(self, store: ApprovalStore, manager, *, timeout_seconds: float = 300,
                 on_requested: Callable[[ApprovalRequest], None] | None = None,
                 on_resolved: Callable[[ApprovalRequest], None] | None = None) -> None:
        self.store, self.manager, self.timeout_seconds = store, manager, timeout_seconds
        self.on_requested, self.on_resolved = on_requested, on_resolved
        self._active: set[str] = set()
        self._lock = RLock()
        # A persisted request has no suspended executor after process restart.
        for request in self.store.all():
            if request.status is ApprovalStatus.PENDING:
                self.store.put(self._final(request, ApprovalStatus.EXPIRED, "runtime_restart"))

    def pending(self) -> tuple[ApprovalRequest, ...]:
        """Only decisions that still have a live suspended runtime action."""
        with self._lock:
            return tuple(request for request in self.store.all()
                         if request.approval_id in self._active and request.status is ApprovalStatus.PENDING)

    async def request(self, action: ComputerAction) -> bool:
        tool = self.manager.tools.get(action.action_type)
        with self._lock:
            existing = self.store.get(action.action_id)
            if existing is not None:
                # Approval identities are single-use, including across restarts.
                return False
            request = ApprovalRequest(action.action_id, action.task_id.split(":", 1)[0], action.task_id,
                action.agent_id, action.action_type, redact(action.reason), tool.risk.value, action.permission,
                requested_at=datetime.now(timezone.utc).isoformat(),
                permissions=tuple(sorted(tool.required_permissions)), tool_name=tool.name,
                can_remember=can_remember_tool(tool) and self.manager.policy.grant_store is not None)
            self.store.put(request)
            self._active.add(action.action_id)
        try:
            self._notify(self.on_requested, request)
            deadline = asyncio.get_running_loop().time() + self.timeout_seconds
            while True:
                current = self.store.get(action.action_id)
                if current and current.status is ApprovalStatus.APPROVED:
                    return True
                if current and current.status in {ApprovalStatus.DENIED, ApprovalStatus.EXPIRED}:
                    return False
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    self._expire_if_pending(action.action_id, "runtime_timeout")
                    return False
                await asyncio.sleep(min(.05, remaining))
        finally:
            self._expire_if_pending(action.action_id, "runtime_cancelled")
            with self._lock:
                self._active.discard(action.action_id)

    def decide(self, approval_id: str, status: ApprovalStatus, actor: str, *,
               remember: bool = False) -> ApprovalRequest:
        status = ApprovalStatus(status)
        if status not in {ApprovalStatus.APPROVED, ApprovalStatus.DENIED, ApprovalStatus.EXPIRED}:
            raise ValueError("Approval decision must be final")
        with self._lock:
            request = self.store.get(approval_id)
            if request is None:
                raise KeyError(f"Unknown approval: {approval_id}")
            if request.status is not ApprovalStatus.PENDING or approval_id not in self._active:
                raise ValueError("Approval is no longer pending in the runtime")
            remembered = False
            if status is ApprovalStatus.APPROVED and remember and request.can_remember:
                tool = self.manager.tools.get(request.tool)
                policy = self.manager.policy
                if (can_remember_tool(tool) and policy.grant_store is not None
                        and frozenset(request.permissions) == tool.required_permissions
                        and all(ApprovalMode(policy.modes.get(permission, ApprovalMode.AUTO_APPROVE))
                                is not ApprovalMode.DENY for permission in request.permissions)):
                    policy.grant_store.grant(request.tool, request.permissions, actor)
                    remembered = True
            decided = self._final(request, status, actor, remembered=remembered)
            self.store.put(decided)
        self._notify(self.on_resolved, decided)
        return decided

    def cancel(self, *, mission_id: str | None = None) -> None:
        """Resolve active requests when an operator cancels a mission or stops the app."""
        for request in self.pending():
            if mission_id is None or request.mission_id == mission_id:
                self._expire_if_pending(request.approval_id, "runtime_cancelled")

    def _expire_if_pending(self, approval_id: str, actor: str) -> None:
        with self._lock:
            request = self.store.get(approval_id)
            if request is None or request.status is not ApprovalStatus.PENDING:
                return
            self.decide(approval_id, ApprovalStatus.EXPIRED, actor)

    @staticmethod
    def _final(request: ApprovalRequest, status: ApprovalStatus, actor: str, *,
               remembered: bool = False) -> ApprovalRequest:
        return ApprovalRequest(**(asdict(request) | {"status": status, "remembered": remembered,
            "decided_at": datetime.now(timezone.utc).isoformat(), "decided_by": actor}))

    @staticmethod
    def _notify(callback: Callable[[ApprovalRequest], None] | None, request: ApprovalRequest) -> None:
        if callback:
            try:
                callback(request)
            except Exception:
                logging.getLogger(__name__).exception("Approval notification failed for %s", request.approval_id)


def _request(data: dict[str, Any]) -> ApprovalRequest:
    payload = dict(data)
    payload["status"] = ApprovalStatus(payload["status"])
    payload["permissions"] = tuple(payload.get("permissions") or (payload["permission"],))
    return ApprovalRequest(**payload)
