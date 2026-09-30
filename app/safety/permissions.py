"""Capability permissions and policy decisions for agent-owned tool access."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from threading import RLock
from typing import Any


class Permission(str, Enum):
    KEYBOARD_READ = "keyboard.read"
    KEYBOARD_WRITE = "keyboard.write"
    MOUSE_READ = "mouse.read"
    MOUSE_MOVE = "mouse.move"
    MOUSE_CLICK = "mouse.click"
    MOUSE_DRAG = "mouse.drag"
    SCREEN_READ = "screen.read"
    WINDOW_READ = "window.read"
    WINDOW_CONTROL = "window.control"
    CLIPBOARD_READ = "clipboard.read"
    CLIPBOARD_WRITE = "clipboard.write"
    BROWSER_READ = "browser.read"
    BROWSER_NAVIGATE = "browser.navigate"
    BROWSER_CLICK = "browser.click"
    BROWSER_TYPE = "browser.type"
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    PROCESS_READ = "process.read"
    PROCESS_EXECUTE = "process.execute"


COMPUTER_READ = frozenset({Permission.SCREEN_READ.value, Permission.MOUSE_READ.value, Permission.KEYBOARD_READ.value})
COMPUTER_CONTROL = frozenset({Permission.MOUSE_MOVE.value, Permission.MOUSE_CLICK.value, Permission.KEYBOARD_WRITE.value})
BROWSER = frozenset({Permission.BROWSER_READ.value, Permission.BROWSER_NAVIGATE.value,
                     Permission.BROWSER_CLICK.value, Permission.BROWSER_TYPE.value})
FILESYSTEM = frozenset({Permission.FILESYSTEM_READ.value, Permission.FILESYSTEM_WRITE.value})
PROCESS = frozenset({Permission.PROCESS_READ.value, Permission.PROCESS_EXECUTE.value})


class ApprovalMode(str, Enum):
    AUTO_APPROVE = "auto_approve"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class PermissionDenied(PermissionError):
    def __init__(self, agent_id: str, permission: str, reason: str) -> None:
        self.agent_id, self.permission, self.reason = agent_id, permission, reason
        super().__init__(f"PERMISSION_DENIED {permission}: {reason}")


class ApprovalRequired(PermissionDenied):
    pass


class PermissionGrantStore:
    """Remember only an explicitly approved tool and its exact capabilities."""

    def __init__(self, path: Path) -> None:
        self.path, self._lock = Path(path), RLock()

    def allows(self, tool: str, permission: str) -> bool:
        with self._lock:
            return permission in self._read().get(tool, {})

    def grant(self, tool: str, permissions: tuple[str, ...], actor: str) -> None:
        if not tool or not permissions or any(not item for item in permissions):
            raise ValueError("A remembered grant needs an exact tool and permissions")
        with self._lock:
            data = self._read()
            for permission in permissions:
                data.setdefault(tool, {})[permission] = {
                    "approved_at": datetime.now(timezone.utc).isoformat(), "approved_by": actor,
                }
            self._write(data)

    def revoke(self, tool: str, permission: str | None = None) -> None:
        with self._lock:
            data = self._read()
            if permission is None:
                data.pop(tool, None)
            else:
                data.get(tool, {}).pop(permission, None)
            self._write(data)

    def _read(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or any(not isinstance(value, dict) for value in data.values()):
                return {}
            return data
        except (ValueError, OSError):
            # A damaged or unreadable file never creates implicit authority.
            return {}

    def _write(self, data: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)


def can_remember_tool(tool: Any) -> bool:
    """Sensitive or irreversible tools always keep their action-level consent."""
    sensitive_permissions = {"process.execute", "filesystem.write", "keyboard.write",
        "mouse.click", "mouse.drag", "clipboard.read", "clipboard.write", "browser.external_action"}
    sensitive_words = {"send", "delete", "purchase", "pay", "payment", "submit", "credential", "password"}
    name_parts = set(tool.tool_id.casefold().replace("_", ".").replace("-", ".").split("."))
    return (tool.risk.value in {"low", "medium"} and tool.reversible and not tool.destructive
            and not (tool.required_permissions & sensitive_permissions)
            and not (name_parts & sensitive_words))


class PermissionPolicy:
    """Global policy layer; ownership checks remain in the agent manager."""
    def __init__(self, modes: dict[str, ApprovalMode] | None = None, *,
                 grant_store: PermissionGrantStore | None = None, require_first_use: bool = False) -> None:
        self.modes = modes or {}
        self.grant_store, self.require_first_use = grant_store, require_first_use
        self._approved: set[tuple[str, str, str | None]] = set()
        self._action_approvals: ContextVar[frozenset[tuple[str, str, str]]] = ContextVar(
            f"permission_action_approvals_{id(self)}", default=frozenset())

    def approve_once(self, agent_id: str, permission: str, *, tool: str | None = None) -> None:
        """Runtime-only one-shot approval consumed by the next policy check."""
        self._approved.add((agent_id, permission, tool))

    @contextmanager
    def approved_scope(self, agent_id: str, tool: str, permissions: tuple[str, ...]) -> Iterator[None]:
        """Bind a human decision to this execution; cancellation cannot leak a grant."""
        token = self._action_approvals.set(frozenset((agent_id, permission, tool) for permission in permissions))
        try:
            yield
        finally:
            self._action_approvals.reset(token)

    def check(self, agent_id: str, permission: str, *, tool: str | None = None,
              consume: bool = True, allow_remembered: bool = True) -> None:
        default = ApprovalMode.REQUIRE_APPROVAL if self.require_first_use else ApprovalMode.AUTO_APPROVE
        mode = ApprovalMode(self.modes.get(permission, default))
        if mode is ApprovalMode.DENY:
            raise PermissionDenied(agent_id, permission, "Global policy denies this permission")
        if mode is ApprovalMode.REQUIRE_APPROVAL:
            if tool and (agent_id, permission, tool) in self._action_approvals.get():
                return
            for key in ((agent_id, permission, tool), (agent_id, permission, None)):
                if key in self._approved:
                    if consume:
                        self._approved.remove(key)
                    return
            if allow_remembered and tool and self.grant_store and self.grant_store.allows(tool, permission):
                return
            raise ApprovalRequired(agent_id, permission, "Human approval is required")
