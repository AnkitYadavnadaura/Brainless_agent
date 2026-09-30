"""Durable, always-running service wrapper for the existing agent runtime.

This module owns service lifecycle and task persistence. It deliberately
delegates task execution to an injected callable so existing browser, desktop,
and provider workflows remain the source of execution behavior.
"""
from __future__ import annotations

import asyncio
import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import signal
import sqlite3
import time
from typing import Awaitable, Callable
import uuid


def _now() -> float:
    return time.time()


def _iso(timestamp: float | None) -> str | None:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat() if timestamp else None


@dataclass(frozen=True, slots=True)
class ServiceTask:
    task_id: str
    description: str
    priority: int
    status: str
    created_at: float
    started_at: float | None
    completed_at: float | None
    assigned_agent: str | None
    retry_count: int
    result: str | None
    error: str | None
    verification_status: str

    def snapshot(self) -> dict[str, object]:
        value = asdict(self)
        for key in ("created_at", "started_at", "completed_at"):
            value[key] = _iso(value[key])
        return value


class PersistentRuntimeStore:
    """SQLite store with atomic task claiming and crash recovery."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=30000")
        try:
            self.db.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            # Another short-lived CLI reader may be changing the journal mode.
            # SQLite's default journal remains safe; subsequent writes still
            # use the configured busy timeout.
            pass
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS runtime_tasks (
                task_id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                description TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                started_at REAL,
                completed_at REAL,
                assigned_agent TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                result TEXT,
                error TEXT,
                verification_status TEXT NOT NULL DEFAULT 'pending'
            );
            CREATE UNIQUE INDEX IF NOT EXISTS runtime_active_fingerprint
                ON runtime_tasks(fingerprint)
                WHERE status IN ('PENDING','RUNNING','WAITING');
            CREATE TABLE IF NOT EXISTS runtime_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runtime_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at REAL NOT NULL,
                event TEXT NOT NULL,
                task_id TEXT,
                agent_id TEXT,
                status TEXT,
                duration REAL,
                error TEXT
            );
            CREATE TABLE IF NOT EXISTS runtime_agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at REAL,
                updated_at REAL NOT NULL
            );
            """
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def set_meta(self, key: str, value: object) -> None:
        self.db.execute(
            "INSERT INTO runtime_meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)),
        )
        self.db.commit()

    def meta(self) -> dict[str, object]:
        return {
            row["key"]: json.loads(row["value"])
            for row in self.db.execute("SELECT key,value FROM runtime_meta")
        }

    def request_stop(self) -> None:
        self.set_meta("stop_requested", True)

    def clear_stop(self) -> None:
        self.set_meta("stop_requested", False)

    def claim_runtime(self, runtime_id: str, *, stale_after: float = 30.0) -> None:
        meta = self.meta()
        heartbeat = float(meta["last_heartbeat"]) if meta.get("last_heartbeat") else None
        active_states = {"STARTING", "READY", "IDLE", "EXECUTING"}
        if (heartbeat and _now() - heartbeat <= stale_after
                and meta.get("runtime_state") in active_states
                and meta.get("runtime_id") != runtime_id):
            raise RuntimeError("A persistent runtime instance is already active")
        self.set_meta("runtime_id", runtime_id)

    def submit(self, description: str, priority: int = 0) -> str:
        fingerprint = hashlib.sha256(description.strip().encode("utf-8")).hexdigest()
        existing = self.db.execute(
            "SELECT task_id FROM runtime_tasks WHERE fingerprint=? "
            "AND status IN ('PENDING','RUNNING','WAITING')",
            (fingerprint,),
        ).fetchone()
        if existing:
            return str(existing["task_id"])
        task_id = str(uuid.uuid4())
        try:
            self.db.execute(
                "INSERT INTO runtime_tasks(task_id,fingerprint,description,priority,status,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (task_id, fingerprint, description.strip(), priority, "PENDING", _now()),
            )
            self.db.commit()
        except sqlite3.IntegrityError:
            row = self.db.execute(
                "SELECT task_id FROM runtime_tasks WHERE fingerprint=? "
                "AND status IN ('PENDING','RUNNING','WAITING')", (fingerprint,),
            ).fetchone()
            if row:
                return str(row["task_id"])
            raise
        return task_id

    def claim(self, agent_id: str) -> ServiceTask | None:
        self.db.execute("BEGIN IMMEDIATE")
        row = self.db.execute(
            "SELECT * FROM runtime_tasks WHERE status IN ('PENDING','WAITING') "
            "ORDER BY priority DESC, created_at LIMIT 1"
        ).fetchone()
        if row is None:
            self.db.commit()
            return None
        self.db.execute(
            "UPDATE runtime_tasks SET status='RUNNING', started_at=?, assigned_agent=? "
            "WHERE task_id=?",
            (_now(), agent_id, row["task_id"]),
        )
        self.db.commit()
        return self.get(str(row["task_id"]))

    def get(self, task_id: str) -> ServiceTask | None:
        row = self.db.execute("SELECT * FROM runtime_tasks WHERE task_id=?", (task_id,)).fetchone()
        return self._task(row) if row else None

    def tasks(self) -> list[ServiceTask]:
        return [self._task(row) for row in self.db.execute(
            "SELECT * FROM runtime_tasks ORDER BY created_at DESC"
        )]

    def finish(self, task_id: str, *, result: str, verification: str = "verified") -> None:
        self.db.execute(
            "UPDATE runtime_tasks SET status='COMPLETED', completed_at=?, result=?, "
            "verification_status=?, error=NULL WHERE task_id=?",
            (_now(), result, verification, task_id),
        )
        self.db.commit()

    def fail(self, task_id: str, error: str, *, retry: bool, max_retries: int) -> None:
        task = self.get(task_id)
        if task is None:
            raise KeyError(task_id)
        if retry and task.retry_count < max_retries:
            self.db.execute(
                "UPDATE runtime_tasks SET status='WAITING', retry_count=retry_count+1, "
                "error=?, verification_status='unknown' WHERE task_id=?",
                (error, task_id),
            )
        else:
            self.db.execute(
                "UPDATE runtime_tasks SET status='FAILED', completed_at=?, error=?, "
                "verification_status='failed' WHERE task_id=?",
                (_now(), error, task_id),
            )
        self.db.commit()

    def recover_interrupted(self) -> int:
        cursor = self.db.execute(
            "UPDATE runtime_tasks SET status='WAITING', error=?, "
            "verification_status='unknown' WHERE status='RUNNING'",
            ("Interrupted by a previous runtime process; safe recovery required",),
        )
        self.db.commit()
        return cursor.rowcount

    def upsert_agent(self, agent_id: str, name: str, status: str) -> None:
        self.db.execute(
            "INSERT INTO runtime_agents(agent_id,name,status,started_at,updated_at) VALUES(?,?,?,?,?) "
            "ON CONFLICT(agent_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at",
            (agent_id, name, status, _now(), _now()),
        )
        self.db.commit()

    def agents(self) -> list[dict[str, object]]:
        return [dict(row) for row in self.db.execute(
            "SELECT agent_id,name,status,started_at,updated_at FROM runtime_agents ORDER BY agent_id"
        )]

    def event(self, event: str, *, task_id: str | None = None, agent_id: str | None = None,
              status: str | None = None, duration: float | None = None, error: str | None = None) -> None:
        self.db.execute(
            "INSERT INTO runtime_events(created_at,event,task_id,agent_id,status,duration,error) "
            "VALUES(?,?,?,?,?,?,?)",
            (_now(), event, task_id, agent_id, status, duration, error),
        )
        self.db.commit()

    def events(self, limit: int = 50) -> list[dict[str, object]]:
        return [dict(row) for row in self.db.execute(
            "SELECT * FROM runtime_events ORDER BY id DESC LIMIT ?", (limit,)
        )]

    @staticmethod
    def _task(row: sqlite3.Row) -> ServiceTask:
        return ServiceTask(
            row["task_id"], row["description"], row["priority"], row["status"],
            row["created_at"], row["started_at"], row["completed_at"],
            row["assigned_agent"], row["retry_count"], row["result"], row["error"],
            row["verification_status"],
        )


class PersistentAgentRuntime:
    """Single-worker service loop that remains alive while the queue is empty."""

    def __init__(
        self,
        root: Path,
        executor: Callable[[ServiceTask], Awaitable[str]],
        *,
        poll_interval: float = 1.0,
        heartbeat_interval: float = 5.0,
        task_timeout: float = 1800.0,
        max_retries: int = 3,
    ):
        self.root = root
        self.store = PersistentRuntimeStore(root / "data/runtime/service.sqlite3")
        self.executor = executor
        self.poll_interval = max(0.1, poll_interval)
        self.heartbeat_interval = max(1.0, heartbeat_interval)
        self.task_timeout = max(1.0, task_timeout)
        self.max_retries = max(0, max_retries)
        self.runtime_id = str(uuid.uuid4())
        self.agent_id = "runtime-worker"
        self.state = "STARTING"
        self.started_at = _now()
        self._wake = asyncio.Event()
        self._stopping = False
        self._heartbeat_task: asyncio.Task[None] | None = None

    def submit(self, description: str, priority: int = 0) -> str:
        if not description.strip() or len(description) > 50_000:
            raise ValueError("Task description must contain 1..50000 characters")
        if not -100 <= priority <= 100:
            raise ValueError("Task priority must be between -100 and 100")
        task_id = self.store.submit(description, priority)
        self.store.event("TASK_CREATED", task_id=task_id, status="PENDING")
        self._wake.set()
        return task_id

    def stop(self) -> None:
        self._stopping = True
        self.store.request_stop()
        self._wake.set()

    def snapshot(self) -> dict[str, object]:
        tasks = self.store.tasks()
        meta = self.store.meta()
        return {
            "runtime_id": self.runtime_id,
            "state": self.state,
            "uptime_seconds": max(0, _now() - self.started_at),
            "last_heartbeat": meta.get("last_heartbeat"),
            "heartbeat_age_seconds": (
                max(0, _now() - float(meta["last_heartbeat"]))
                if meta.get("last_heartbeat") else None
            ),
            "active_agents": self.store.agents(),
            "queued_tasks": sum(task.status in {"PENDING", "WAITING"} for task in tasks),
            "running_tasks": sum(task.status == "RUNNING" for task in tasks),
            "completed_tasks": sum(task.status == "COMPLETED" for task in tasks),
            "failed_tasks": sum(task.status == "FAILED" for task in tasks),
            "retry_count": sum(task.retry_count for task in tasks),
            "stop_requested": bool(meta.get("stop_requested", False)),
        }

    async def run_forever(self) -> None:
        self.store.claim_runtime(self.runtime_id)
        self.store.clear_stop()
        recovered = self.store.recover_interrupted()
        self.store.upsert_agent(self.agent_id, "Persistent Runtime Worker", "READY")
        self.store.event("RUNTIME_STARTED", agent_id=self.agent_id,
                         error=f"Recovered {recovered} interrupted task(s)" if recovered else None)
        self.state = "READY"
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        try:
            while not self._stopping and not self.store.meta().get("stop_requested", False):
                self.state = "EXECUTING"
                task = self.store.claim(self.agent_id)
                if task is None:
                    self.state = "IDLE"
                    await self._wait_for_work()
                    continue
                started = _now()
                self.store.upsert_agent(self.agent_id, "Persistent Runtime Worker", "BUSY")
                self.store.event("TASK_STARTED", task_id=task.task_id, agent_id=self.agent_id, status="RUNNING")
                try:
                    result = await asyncio.wait_for(self.executor(task), self.task_timeout)
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    self.store.fail(task.task_id, str(error), retry=True, max_retries=self.max_retries)
                    self.store.event("TASK_FAILED", task_id=task.task_id, agent_id=self.agent_id,
                                     status="WAITING" if self.store.get(task.task_id).status == "WAITING" else "FAILED",
                                     duration=_now() - started, error=str(error))
                else:
                    self.store.finish(task.task_id, result=str(result))
                    self.store.event("TASK_COMPLETED", task_id=task.task_id, agent_id=self.agent_id,
                                     status="COMPLETED", duration=_now() - started)
                finally:
                    self.store.upsert_agent(self.agent_id, "Persistent Runtime Worker", "READY")
                self.state = "READY"
        finally:
            self.state = "STOPPING"
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                await asyncio.gather(self._heartbeat_task, return_exceptions=True)
            self.store.upsert_agent(self.agent_id, "Persistent Runtime Worker", "STOPPED")
            self.store.set_meta("runtime_state", self.state)
            self.store.set_meta("last_state", self.state)
            self.store.event("RUNTIME_STOPPED", agent_id=self.agent_id)
            self.store.close()

    async def run_once(self) -> bool:
        """Process at most one task, preserving the same safety transitions."""
        self.store.claim_runtime(self.runtime_id)
        self.store.clear_stop()
        self.store.recover_interrupted()
        self.store.upsert_agent(self.agent_id, "Persistent Runtime Worker", "READY")
        task = self.store.claim(self.agent_id)
        if task is None:
            self.store.upsert_agent(self.agent_id, "Persistent Runtime Worker", "IDLE")
            return False
        started = _now()
        self.store.upsert_agent(self.agent_id, "Persistent Runtime Worker", "BUSY")
        try:
            result = await asyncio.wait_for(self.executor(task), self.task_timeout)
        except Exception as error:
            self.store.fail(task.task_id, str(error), retry=True, max_retries=self.max_retries)
            self.store.event("TASK_FAILED", task_id=task.task_id, agent_id=self.agent_id,
                             status=self.store.get(task.task_id).status, duration=_now() - started,
                             error=str(error))
        else:
            self.store.finish(task.task_id, result=str(result))
            self.store.event("TASK_COMPLETED", task_id=task.task_id, agent_id=self.agent_id,
                             status="COMPLETED", duration=_now() - started)
        finally:
            self.store.upsert_agent(self.agent_id, "Persistent Runtime Worker", "STOPPED")
        return True

    async def _wait_for_work(self) -> None:
        try:
            await asyncio.wait_for(self._wake.wait(), timeout=self.poll_interval)
            self._wake.clear()
        except asyncio.TimeoutError:
            pass

    async def _heartbeat_loop(self) -> None:
        while True:
            self.store.set_meta("last_heartbeat", _now())
            self.store.set_meta("runtime_state", self.state)
            await asyncio.sleep(self.heartbeat_interval)


def service_health(root: Path, *, stale_after: float = 30.0) -> dict[str, object]:
    store = PersistentRuntimeStore(root / "data/runtime/service.sqlite3")
    try:
        meta = store.meta()
        heartbeat = float(meta["last_heartbeat"]) if meta.get("last_heartbeat") else None
        age = _now() - heartbeat if heartbeat else None
        active = meta.get("runtime_state") in {"STARTING", "READY", "IDLE", "EXECUTING"}
        return {
            "healthy": bool(heartbeat and age is not None and age <= stale_after
                            and active and not meta.get("stop_requested", False)),
            "last_heartbeat": _iso(heartbeat),
            "heartbeat_age_seconds": age,
            "runtime_state": meta.get("runtime_state", "UNKNOWN"),
            "stop_requested": bool(meta.get("stop_requested", False)),
            "agents": store.agents(),
        }
    finally:
        store.close()


async def run_persistent_service(root: Path, executor: Callable[[ServiceTask], Awaitable[str]]) -> None:
    runtime = PersistentAgentRuntime(root, executor)
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, runtime.stop)
        except (NotImplementedError, AttributeError):
            signal.signal(signum, lambda *_: runtime.stop())
    await runtime.run_forever()


def runtime_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python run.py runtime")
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="Run the persistent runtime until stopped")
    start.add_argument("--once", action="store_true", help="Process one queued task, then stop")
    submit = commands.add_parser("submit", help="Persist a task for the runtime")
    submit.add_argument("description")
    submit.add_argument("--priority", type=int, default=0)
    for name in ("status", "tasks", "agents", "health", "stop", "restart"):
        commands.add_parser(name)
    return parser


async def run_runtime_cli(root: Path, arguments: list[str]) -> int:
    options = runtime_parser().parse_args(arguments)
    store = PersistentRuntimeStore(root / "data/runtime/service.sqlite3")
    try:
        if options.command == "submit":
            task_id = store.submit(options.description, options.priority)
            store.event("TASK_CREATED", task_id=task_id, status="PENDING")
            print(task_id)
            return 0
        if options.command == "status":
            print(json.dumps(_status_snapshot(store), indent=2))
            return 0
        if options.command == "tasks":
            print(json.dumps([task.snapshot() for task in store.tasks()], indent=2))
            return 0
        if options.command == "agents":
            print(json.dumps(store.agents(), indent=2))
            return 0
        if options.command == "health":
            health = service_health(root)
            print(json.dumps(health, indent=2))
            return 0 if health["healthy"] else 1
        if options.command == "stop":
            store.request_stop()
            print("Stop requested")
            return 0
        if options.command == "restart":
            store.request_stop()
            print("Restart requested; start the runtime again after it exits")
            return 0

        from app.bootstrap import Application
        from app.config.settings import load_settings
        from app.runtime.task_manager import TaskManager

        application = Application(root, load_settings())
        try:
            manager = TaskManager(application.providers.names)

            async def execute(task: ServiceTask) -> str:
                runtime_task = manager.create(task.description)
                return await application.runtime.run(runtime_task)

            runtime = PersistentAgentRuntime(root, execute)
            if options.once:
                await runtime.run_once()
            else:
                loop = asyncio.get_running_loop()
                for signum in (signal.SIGINT, signal.SIGTERM):
                    try:
                        loop.add_signal_handler(signum, runtime.stop)
                    except (NotImplementedError, AttributeError):
                        signal.signal(signum, lambda *_: runtime.stop())
                await runtime.run_forever()
            return 0
        finally:
            await application.close()
    finally:
        store.close()


def _status_snapshot(store: PersistentRuntimeStore) -> dict[str, object]:
    tasks = store.tasks()
    meta = store.meta()
    heartbeat = float(meta["last_heartbeat"]) if meta.get("last_heartbeat") else None
    return {
        "state": meta.get("runtime_state", "UNKNOWN"),
        "last_heartbeat": _iso(heartbeat),
        "tasks": {
            "pending": sum(task.status in {"PENDING", "WAITING"} for task in tasks),
            "running": sum(task.status == "RUNNING" for task in tasks),
            "completed": sum(task.status == "COMPLETED" for task in tasks),
            "failed": sum(task.status == "FAILED" for task in tasks),
        },
        "agents": store.agents(),
        "events": store.events(10),
    }
