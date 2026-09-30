"""Validation and conservative normalization for URLs supplied to browser tools."""
from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit


_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^()\s]+)\)")


def normalize_web_url(value: object) -> str:
    """Return a plain HTTP(S) URL, unwrapping common LLM Markdown formatting.

    Bare website names get an ``https://`` scheme. Other schemes, credentials,
    malformed hosts/ports, and whitespace are rejected before browser navigation.
    """
    if not isinstance(value, str):
        raise ValueError("URL must be a string")
    candidate = value.strip()
    if not candidate:
        raise ValueError("URL cannot be empty")

    markdown = _MARKDOWN_LINK.fullmatch(candidate)
    if markdown:
        candidate = markdown.group(2)
    elif len(candidate) >= 2 and candidate[0] == candidate[-1] == "`":
        candidate = candidate[1:-1].strip()
    elif len(candidate) >= 2 and candidate[0] == "<" and candidate[-1] == ">":
        candidate = candidate[1:-1].strip()

    if not candidate or any(char.isspace() or ord(char) < 0x20 or ord(char) == 0x7F
                            for char in candidate):
        raise ValueError("URL must not contain whitespace or control characters")
    if "\\" in candidate:
        raise ValueError("URL must not contain backslashes")

    if candidate.startswith("//"):
        candidate = "https:" + candidate
    elif "://" not in candidate:
        candidate = "https://" + candidate

    try:
        parts = urlsplit(candidate)
        port = parts.port  # Access validates malformed and out-of-range ports.
    except ValueError as error:
        raise ValueError("URL has an invalid host or port") from error

    if parts.scheme.casefold() not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are allowed")
    if not parts.hostname:
        raise ValueError("URL must include a host name")
    if parts.username is not None or parts.password is not None:
        raise ValueError("URLs containing embedded credentials are not allowed")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("URL port must be between 1 and 65535")

    return urlunsplit((parts.scheme.casefold(), parts.netloc, parts.path,
                       parts.query, parts.fragment))
