"""Validation boundary between planner output and browser operations."""
from __future__ import annotations

from urllib.parse import urljoin

from app.browser.actions import BrowserAction, BrowserActionType
from app.browser.observer import PageObservation
from app.browser.permissions import PermissionManager
from app.browser.policies import BrowserPolicy


_NEEDED_FIELDS = {
    "navigate": {"url"},
    "back": set(), "forward": set(), "refresh": set(),
    "click": {"target"}, "double_click": {"target"}, "type": {"target", "text"},
    "clear": {"target"}, "press": {"target", "key"},
    "select": {"target", "value"}, "scroll": {"direction", "amount"},
    "hover": {"target"}, "wait": set(),
    "new_tab": set(), "switch_tab": {"tab_id"}, "close_tab": {"tab_id"},
    "read_text": {"target"}, "read_attribute": {"target", "attribute"},
    "play": {"target"}, "pause": {"target"},
}
_TARGET_ACTIONS = {
    "click", "double_click", "type", "clear", "press", "select", "hover",
    "read_text", "read_attribute", "play", "pause",
}
_READABLE_ATTRIBUTES = frozenset({
    "alt", "aria-label", "checked", "disabled", "href", "name",
    "placeholder", "rel", "role", "title", "type",
})


class BrowserTargetStaleError(ValueError):
    """The current page no longer contains the exact observed target."""


class BrowserActionValidator:
    def __init__(self, permissions: PermissionManager,
                 policy: BrowserPolicy) -> None:
        self.permissions, self.policy = permissions, policy

    def validate(self, action: BrowserAction, observation: PageObservation | None,
                 *, confirm_external: bool = False) -> BrowserAction:
        try:
            kind = BrowserActionType(action.action).value
        except (ValueError, TypeError) as error:
            raise ValueError("Unsupported browser action") from error
        if kind not in self.policy.allowed_actions:
            raise ValueError(f"Browser action is blocked by policy: {kind}")
        values = {
            "url": action.url, "target": action.target, "text": action.text,
            "key": action.key, "value": action.value, "attribute": action.attribute,
            "direction": action.direction, "amount": action.amount,
            "tab_id": action.tab_id, "timeout_ms": action.timeout_ms,
        }
        required = _NEEDED_FIELDS[kind]
        if any(values[field] is None for field in required):
            raise ValueError(f"Browser action {kind} is missing required arguments")
        allowed = required | ({"timeout_ms"} if kind == "wait" else set())
        if any(value is not None and field not in allowed
               for field, value in values.items()):
            raise ValueError(f"Browser action {kind} contains unsupported arguments")
        if any(value is not None and not isinstance(value, str)
               for field, value in values.items()
               if field in {"url", "target", "text", "key", "value",
                            "attribute", "tab_id"}):
            raise ValueError("Browser action text and identifiers must be strings")
        if action.text is not None and len(action.text) > self.policy.max_text_length:
            raise ValueError("Browser action text exceeds the policy length limit")
        if action.key is not None and (not action.key or len(action.key) > 40):
            raise ValueError("Browser key must contain 1-40 characters")
        if kind == "navigate":
            self.policy.validate_url(action.url)
        if kind == "scroll" and (
                action.direction not in {"up", "down"}
                or type(action.amount) is not int
                or not 1 <= action.amount <= self.policy.max_scroll_amount):
            raise ValueError("Browser scroll must use up/down and a bounded integer amount")
        if kind == "wait" and (
                action.timeout_ms is not None
                and (type(action.timeout_ms) is not int
                     or not 1 <= action.timeout_ms <= 30_000)):
            raise ValueError("Browser wait timeout must be between 1 and 30000ms")
        if kind == "read_attribute" and action.attribute not in _READABLE_ATTRIBUTES:
            raise ValueError("Browser attribute is not in the safe read allowlist")
        element = None
        if kind in _TARGET_ACTIONS:
            if observation is None:
                raise ValueError("Observe the page before targeting a browser element")
            element = next((item for item in observation.elements
                           if item.target_id == action.target), None)
            if element is None or not element.visible:
                raise BrowserTargetStaleError(
                    "Browser target is missing or stale; observe the page again")
            if kind == "click" and element.href:
                self.policy.validate_url(urljoin(observation.url, element.href))
            if kind in {"click", "double_click", "press", "hover", "play", "pause"} and not element.enabled:
                raise ValueError("Browser target is disabled")
            if kind in {"type", "clear", "select"} and element.role not in {
                    "input", "textarea", "select", "textbox", "combobox"}:
                raise ValueError(f"Browser target is not an editable field for {kind}")
            if kind in {"click", "double_click", "press"} and element.external and not confirm_external:
                raise PermissionError("This form submission requires explicit user confirmation")
        self.permissions.require(
            kind, external=bool(
                element and element.external
                and kind in {"click", "double_click", "press"}))
        return action
