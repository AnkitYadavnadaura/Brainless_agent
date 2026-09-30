"""Least-privilege permissions for generic browser actions."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from collections.abc import Iterable


class BrowserPermission(str, Enum):
    READ = "browser.read"
    NAVIGATE = "browser.navigate"
    WRITE = "browser.write"
    EXTERNAL_ACTION = "browser.external_action"


_ACTION_PERMISSIONS = {
    "navigate": BrowserPermission.NAVIGATE,
    "back": BrowserPermission.NAVIGATE,
    "forward": BrowserPermission.NAVIGATE,
    "refresh": BrowserPermission.NAVIGATE,
    "new_tab": BrowserPermission.NAVIGATE,
    "switch_tab": BrowserPermission.NAVIGATE,
    "close_tab": BrowserPermission.NAVIGATE,
    "click": BrowserPermission.WRITE,
    "double_click": BrowserPermission.WRITE,
    "type": BrowserPermission.WRITE,
    "clear": BrowserPermission.WRITE,
    "press": BrowserPermission.WRITE,
    "select": BrowserPermission.WRITE,
    "scroll": BrowserPermission.WRITE,
    "hover": BrowserPermission.WRITE,
    "play": BrowserPermission.WRITE,
    "pause": BrowserPermission.WRITE,
    "wait": BrowserPermission.READ,
    "read_text": BrowserPermission.READ,
    "read_attribute": BrowserPermission.READ,
}


@dataclass(slots=True)
class PermissionManager:
    granted: set[BrowserPermission] | Iterable[str]

    def __post_init__(self) -> None:
        self.granted = {
            permission if isinstance(permission, BrowserPermission)
            else BrowserPermission(permission)
            for permission in self.granted
        }

    def allows(self, action: str, *, external: bool = False) -> bool:
        required = _ACTION_PERMISSIONS.get(action)
        return (required is not None and required in self.granted
                and (not external or BrowserPermission.EXTERNAL_ACTION in self.granted))

    def require(self, action: str, *, external: bool = False) -> None:
        required = _ACTION_PERMISSIONS.get(action)
        if required is None:
            raise PermissionError(f"Unsupported browser action: {action}")
        if required not in self.granted:
            raise PermissionError(f"Browser action requires {required.value}")
        if external and BrowserPermission.EXTERNAL_ACTION not in self.granted:
            raise PermissionError("This browser action requires browser.external_action")
