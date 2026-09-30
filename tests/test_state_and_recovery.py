import asyncio
from unittest.mock import AsyncMock

import pytest

from app.autonomy.contracts import Idempotency
from app.autonomy.recovery import RecoveryEngine, RecoveryStrategy
from app.runtime.recovery_manager import RecoveryManager
from app.runtime.state_manager import RuntimeState, StateManager


def test_state_transitions_are_recorded() -> None:
    manager = StateManager()
    manager.transition(RuntimeState.INITIALIZING)
    manager.transition(RuntimeState.COMPLETED)
    assert manager.history == [RuntimeState.IDLE, RuntimeState.INITIALIZING, RuntimeState.COMPLETED]


def test_focusing_input_is_an_explicit_runtime_state() -> None:
    manager = StateManager()
    manager.transition(RuntimeState.FOCUSING_INPUT)
    assert manager.state is RuntimeState.FOCUSING_INPUT


def test_recovery_retries_after_failure() -> None:
    attempts = 0
    recoveries = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary")
        return "ok"

    async def recover() -> None:
        nonlocal recoveries
        recoveries += 1

    assert asyncio.run(RecoveryManager(1).run(operation, recover)) == "ok"
    assert recoveries == 1


@pytest.mark.parametrize("retries", [-1, True, 1.5])
def test_recovery_rejects_invalid_retry_budgets(retries) -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        RecoveryManager(retries)


def test_recovery_survives_a_failed_reload_and_uses_the_remaining_read_attempt() -> None:
    operation = AsyncMock(side_effect=[RuntimeError("stale DOM"), "recovered"])
    recover = AsyncMock(side_effect=RuntimeError("navigation interrupted"))
    assert asyncio.run(RecoveryManager(1).run(operation, recover)) == "recovered"
    assert operation.await_count == 2
    recover.assert_awaited_once()


def test_recovery_exhaustion_preserves_the_last_read_error() -> None:
    error = RuntimeError("response still missing")
    operation = AsyncMock(side_effect=error)
    recover = AsyncMock(side_effect=RuntimeError("reload failed"))
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(RecoveryManager(2).run(operation, recover))
    assert caught.value is error
    assert operation.await_count == 3
    assert recover.await_count == 2


def test_recovery_does_not_consume_more_attempts_when_cancelled() -> None:
    operation = AsyncMock(side_effect=asyncio.CancelledError)
    recover = AsyncMock()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(RecoveryManager(2).run(operation, recover))
    operation.assert_awaited_once()
    recover.assert_not_awaited()


@pytest.mark.parametrize("error", ["ACTION_FAILED: disconnected", "VERIFICATION_FAILED: missing", "INVALID_ARGUMENT: field"])
def test_recovery_decisions_respect_the_attempt_budget(error) -> None:
    assert RecoveryEngine().choose(error, Idempotency.SAFE_TO_RETRY, 2, 2) is RecoveryStrategy.ABORT


def test_conditional_actions_require_observation_before_retrying() -> None:
    strategy = RecoveryEngine().choose("ACTION_FAILED: unknown receipt", Idempotency.CONDITIONALLY_RETRYABLE, 1, 2)
    assert strategy is RecoveryStrategy.REOBSERVE
