"""Bounded method changes within an already-authorized browser action."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


class MethodUnavailable(RuntimeError):
    """A method failed with a known outcome and an alternative may be attempted."""


async def run_methods(methods: Sequence[tuple[str, Callable[[], Awaitable[T]]]],
                      *, attempts: list[dict] | None = None) -> T:
    """Try each supported method once; never catch cancellation or uncertain input."""
    if not 1 <= len(methods) <= 3 or len({name for name, _ in methods}) != len(methods):
        raise ValueError("Provide one to three distinct execution methods")
    history = attempts if attempts is not None else []
    errors = []
    for name, method in methods:
        try:
            result = await method()
        except MethodUnavailable as error:
            history.append({"method": name, "status": "unavailable"})
            errors.append(f"{name}: {error}")
            logger.info("Browser method %s unavailable; checking the next supported method", name)
        else:
            history.append({"method": name, "status": "verified"})
            return result
    raise MethodUnavailable("All supported methods failed. " + " | ".join(errors))
