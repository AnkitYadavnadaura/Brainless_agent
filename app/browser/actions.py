"""Data-only action types accepted by the generic browser agent."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class BrowserActionType(str, Enum):
    NAVIGATE = "navigate"
    BACK = "back"
    FORWARD = "forward"
    REFRESH = "refresh"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    TYPE = "type"
    CLEAR = "clear"
    PRESS = "press"
    SELECT = "select"
    SCROLL = "scroll"
    HOVER = "hover"
    WAIT = "wait"
    NEW_TAB = "new_tab"
    SWITCH_TAB = "switch_tab"
    CLOSE_TAB = "close_tab"
    READ_TEXT = "read_text"
    READ_ATTRIBUTE = "read_attribute"
    PLAY = "play"
    PAUSE = "pause"


@dataclass(frozen=True, slots=True)
class BrowserAction:
    action: BrowserActionType | str
    target: str | None = None
    url: str | None = None
    text: str | None = None
    key: str | None = None
    value: str | None = None
    attribute: str | None = None
    direction: str | None = None
    amount: int | None = None
    tab_id: str | None = None
    timeout_ms: int | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "BrowserAction":
        if not isinstance(value, dict):
            raise ValueError("Browser action must be an object")
        fields = {field for field in cls.__dataclass_fields__}
        if set(value) - fields or "action" not in value:
            raise ValueError("Browser action contains unsupported fields")
        return cls(**value)
