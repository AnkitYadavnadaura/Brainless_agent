import logging
from collections.abc import Awaitable, Callable


LOGGER = logging.getLogger(__name__)


class RecoveryManager:
    def __init__(self, max_retries: int) -> None:
        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        self.max_retries = max_retries

    async def run(self, operation: Callable[[], Awaitable[str]], recover: Callable[[], Awaitable[None]],
                  *, non_retryable: tuple[type[Exception], ...] = ()) -> str:
        """Retry a read operation within its budget, even if a recovery hook fails.

        Callers identify control signals that must propagate without recovery.
        Cancellation always propagates because it is not an Exception.
        """
        for attempt in range(self.max_retries + 1):
            try:
                return await operation()
            except Exception as error:
                if isinstance(error, non_retryable) or attempt == self.max_retries:
                    raise
                LOGGER.warning("Recovery attempt %s/%s after %s: %s", attempt + 1, self.max_retries,
                               type(error).__name__, error)
                try:
                    await recover()
                except Exception as recovery_error:
                    if isinstance(recovery_error, non_retryable):
                        raise
                    LOGGER.warning("Recovery hook failed with %s: %s; trying the remaining read attempt",
                                   type(recovery_error).__name__, recovery_error)
        raise AssertionError("Retry loop finished without a result")
