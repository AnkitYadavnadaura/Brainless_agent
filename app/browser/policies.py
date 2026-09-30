"""URL and action policy for the generic browser automation layer."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class BrowserPolicy:
    allowed_schemes: frozenset[str] = frozenset({"https"})
    blocked_hosts: frozenset[str] = frozenset()
    allowed_actions: frozenset[str] = frozenset({
        "navigate", "back", "forward", "refresh", "click", "double_click",
        "type", "clear", "press", "select", "scroll", "hover", "wait",
        "new_tab", "switch_tab", "close_tab", "read_text",
        "read_attribute", "play", "pause",
    })
    max_text_length: int = 20_000
    max_scroll_amount: int = 2_000

    def validate_url(self, url: str) -> str:
        if not isinstance(url, str) or not url or len(url) > 4_096:
            raise ValueError("Browser URL must contain 1-4096 characters")
        parts = urlsplit(url)
        host = (parts.hostname or "").casefold().rstrip(".")
        if (parts.scheme.casefold() not in self.allowed_schemes or not host
                or parts.username is not None or parts.password is not None
                or parts.port not in (None, 443)
                or any(ord(char) < 32 or char.isspace() for char in url)):
            raise ValueError("Browser navigation requires an allowed absolute HTTPS URL")
        if any(host == blocked or host.endswith("." + blocked)
               for blocked in self.blocked_hosts):
            raise ValueError("Browser navigation to this host is blocked by policy")
        return url


DEFAULT_BROWSER_POLICY = BrowserPolicy()
