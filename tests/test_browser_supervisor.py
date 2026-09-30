import asyncio

import pytest

from app.browser.supervisor import BrowserSupervisor, SupervisorStore


@pytest.mark.asyncio
async def test_supervisor_retries_with_persisted_backoff(tmp_path):
    calls = []

    async def runner(arguments, root, progress):
        calls.append(arguments)
        return 1 if len(calls) == 1 else 0

    def status_reader(path, session):
        return {"sessions": [{"request": {"status": "extracted"}}],
                "unresolved_submissions": []}

    store = SupervisorStore(tmp_path / "queue.sqlite3")
    supervisor = BrowserSupervisor(tmp_path, store, base_backoff=0.1,
                                   runner=runner, status_reader=status_reader)
    ident = supervisor.enqueue("do something", "stable")
    assert await supervisor.run_once()
    assert store.get(ident).status == "retrying"
    assert store.get(ident).attempts == 1
    store.update(ident, status="queued", next_attempt=0)
    assert await supervisor.run_once()
    assert store.get(ident).status == "completed"
    assert len(calls) == 2
    store.close()


@pytest.mark.asyncio
async def test_uncertain_browser_submission_is_never_replayed(tmp_path):
    calls = 0

    async def runner(arguments, root, progress):
        nonlocal calls
        calls += 1
        return 1

    def status_reader(path, session):
        return {"sessions": [], "unresolved_submissions": [{"member_id": "chatgpt"}]}

    store = SupervisorStore(tmp_path / "queue.sqlite3")
    supervisor = BrowserSupervisor(tmp_path, store, runner=runner,
                                   status_reader=status_reader)
    ident = supervisor.enqueue("send once")
    await supervisor.run_once()
    assert store.get(ident).status == "awaiting_recovery"
    assert calls == 1
    assert not await supervisor.run_once()
    store.close()


@pytest.mark.asyncio
async def test_supervisor_waits_without_busy_loop(tmp_path):
    store = SupervisorStore(tmp_path / "queue.sqlite3")
    supervisor = BrowserSupervisor(tmp_path, store, poll_interval=0.01)
    task = asyncio.create_task(supervisor.run_forever())
    await asyncio.sleep(0.03)
    assert not task.done()
    supervisor.stop()
    await asyncio.wait_for(task, 1)
    store.close()
