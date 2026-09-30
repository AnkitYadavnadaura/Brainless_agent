import asyncio

import pytest

from app.runtime.persistent_service import (
    PersistentAgentRuntime,
    PersistentRuntimeStore,
    service_health,
)


def test_tasks_survive_store_reopen_and_duplicate_submission(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    store = PersistentRuntimeStore(path)
    first = store.submit("same task")
    assert store.submit("same task") == first
    store.close()

    reopened = PersistentRuntimeStore(path)
    task = reopened.get(first)
    assert task is not None
    assert task.status == "PENDING"
    assert len(reopened.tasks()) == 1
    reopened.close()


@pytest.mark.asyncio
async def test_runtime_processes_task_and_remains_alive_when_idle(tmp_path):
    completed = []

    async def executor(task):
        completed.append(task.description)
        return "verified result"

    runtime = PersistentAgentRuntime(tmp_path, executor, poll_interval=0.01,
                                     heartbeat_interval=0.02)
    task_id = runtime.submit("perform one bounded task")
    worker = asyncio.create_task(runtime.run_forever())
    for _ in range(100):
        task = runtime.store.get(task_id)
        if task and task.status == "COMPLETED":
            break
        await asyncio.sleep(0.01)
    assert completed == ["perform one bounded task"]
    assert not worker.done()
    assert runtime.state == "IDLE"
    runtime.stop()
    await asyncio.wait_for(worker, 1)


@pytest.mark.asyncio
async def test_runtime_recovers_running_tasks_and_limits_retries(tmp_path):
    runtime_path = tmp_path / "data" / "runtime" / "service.sqlite3"
    store = PersistentRuntimeStore(runtime_path)
    task_id = store.submit("recover me")
    claimed = store.claim("old-worker")
    assert claimed and claimed.task_id == task_id
    store.close()

    calls = 0

    async def executor(_task):
        nonlocal calls
        calls += 1
        raise RuntimeError("worker failed")

    runtime = PersistentAgentRuntime(tmp_path, executor, max_retries=0)
    await runtime.run_once()
    task = runtime.store.get(task_id)
    assert task and task.status == "FAILED"
    assert calls == 1
    runtime.store.close()


def test_health_reports_stale_or_missing_heartbeat(tmp_path):
    assert service_health(tmp_path)["healthy"] is False
