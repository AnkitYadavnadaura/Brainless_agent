"""Durable, always-on queue for leader-browser tasks.

The supervisor deliberately treats an interrupted browser submission as
uncertain.  Such work is left for ``browser-team recover`` rather than being
replayed automatically.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import sqlite3
import time
import uuid
from typing import Awaitable, Callable

from app.browser.team_cli import run_browser_team, saved_status


def _now() -> float:
    return time.time()


@dataclass(frozen=True)
class QueuedTask:
    id: str
    task: str
    session: str
    status: str
    attempts: int
    next_attempt: float
    checkpoint: dict
    error: str | None


class SupervisorStore:
    """Small SQLite queue with atomic state transitions."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS supervisor_tasks (
            id TEXT PRIMARY KEY, task TEXT NOT NULL, session TEXT NOT NULL,
            status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt REAL NOT NULL, checkpoint TEXT NOT NULL DEFAULT '{}',
            error TEXT, created REAL NOT NULL, updated REAL NOT NULL)""")
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def enqueue(self, task: str, session: str | None = None) -> str:
        ident = str(uuid.uuid4())
        now = _now()
        self.db.execute(
            "INSERT INTO supervisor_tasks VALUES (?,?,?,?,?,?,?,?,?,?)",
            (ident, task, session or "task-" + uuid.uuid5(uuid.NAMESPACE_URL, task).hex[:20],
             "queued", 0, now, "{}", None, now, now))
        self.db.commit()
        return ident

    def get(self, ident: str) -> QueuedTask | None:
        row = self.db.execute("SELECT * FROM supervisor_tasks WHERE id=?", (ident,)).fetchone()
        return self._task(row) if row else None

    def ready(self, now: float | None = None) -> QueuedTask | None:
        row = self.db.execute(
            "SELECT * FROM supervisor_tasks WHERE status IN ('queued','retrying') "
            "AND next_attempt<=? ORDER BY created LIMIT 1", (_now() if now is None else now,)
        ).fetchone()
        return self._task(row) if row else None

    def update(self, ident: str, *, status: str, attempts: int | None = None,
               next_attempt: float | None = None, checkpoint: dict | None = None,
               error: str | None = None) -> None:
        current = self.get(ident)
        if current is None:
            raise KeyError(ident)
        self.db.execute("""UPDATE supervisor_tasks SET status=?,
            attempts=?, next_attempt=?, checkpoint=?, error=?, updated=? WHERE id=?""",
            (status, current.attempts if attempts is None else attempts,
             current.next_attempt if next_attempt is None else next_attempt,
             json.dumps(current.checkpoint if checkpoint is None else checkpoint),
             error, _now(), ident))
        self.db.commit()

    def all(self) -> list[QueuedTask]:
        return [self._task(row) for row in self.db.execute(
            "SELECT * FROM supervisor_tasks ORDER BY created DESC")]

    @staticmethod
    def _task(row: sqlite3.Row) -> QueuedTask:
        return QueuedTask(row["id"], row["task"], row["session"], row["status"],
                          row["attempts"], row["next_attempt"],
                          json.loads(row["checkpoint"] or "{}"), row["error"])


class BrowserSupervisor:
    def __init__(self, root: Path, store: SupervisorStore | None = None, *,
                 max_attempts: int = 3, base_backoff: float = 2.0,
                 poll_interval: float = 5.0,
                 runner: Callable[..., Awaitable[int]] | None = None,
                 status_reader: Callable[..., dict] | None = None):
        self.root = root
        self.store = store or SupervisorStore(root / "data/browser-team/supervisor.sqlite3")
        self.max_attempts = max(1, max_attempts)
        self.base_backoff = max(0.1, base_backoff)
        self.poll_interval = max(0.1, poll_interval)
        self.runner = runner or run_browser_team
        self.status_reader = status_reader or saved_status
        self._wake = asyncio.Event()
        self._stopping = False

    def enqueue(self, task: str, session: str | None = None) -> str:
        if not task.strip() or len(task) > 50_000:
            raise ValueError("Task must contain 1..50000 characters")
        ident = self.store.enqueue(task, session)
        self._wake.set()
        return ident

    def stop(self) -> None:
        self._stopping = True
        self._wake.set()

    async def run_once(self) -> bool:
        item = self.store.ready()
        if item is None:
            return False
        attempt = item.attempts + 1
        self.store.update(item.id, status="running", attempts=attempt,
                          checkpoint={"phase": "starting", "attempt": attempt})
        try:
            # Supervisor enforces a reasonable timeout for browser-team execution.
            # Tasks may wait for provider readiness; after that, work should progress
            # or fail clearly within a bounded time window.
            browser_timeout = 600  # 10 minutes per attempt
            code = await asyncio.wait_for(
                self.runner(["run", item.task, "--session", item.session],
                           self.root, progress=lambda _: None),
                timeout=browser_timeout)
            report = self.status_reader(self.root / "data/browser-team/team.sqlite3", item.session)
            unresolved = report.get("unresolved_submissions", []) if isinstance(report, dict) else []
            request = (report.get("sessions") or [{}])[0].get("request") if isinstance(report, dict) else None
            if unresolved:
                self.store.update(item.id, status="awaiting_recovery",
                                  checkpoint={"phase": "uncertain", "attempt": attempt,
                                              "session": item.session},
                                  error="Browser submission outcome is uncertain; recover before replay")
            elif code == 0 and request and request.get("status") in {"extracted", "completed"}:
                self.store.update(item.id, status="completed",
                                  checkpoint={"phase": "verified", "attempt": attempt,
                                              "session": item.session})
            elif code == 0 and not request:
                self.store.update(item.id, status="failed",
                                  checkpoint={"phase": "unverified", "attempt": attempt},
                                  error="Browser run returned success without a persisted result")
            else:
                self._failed(item, attempt, "browser team returned code %s" % code)
        except asyncio.TimeoutError:
            # Browser-team execution exceeded timeout. This typically means:
            # 1. No providers are ready (blocked by login, network, etc.)
            # 2. Provider is slow or hanging
            # 3. Complex task is taking too long
            # Classify as awaiting_recovery since we don't know if work started.
            self.store.update(item.id, status="awaiting_recovery",
                              checkpoint={"phase": "timeout", "attempt": attempt,
                                          "session": item.session},
                              error="Browser-team execution exceeded 10-minute timeout; "
                                    "check provider readiness with 'python run.py browser-team status'")
        except (OSError, RuntimeError) as error:
            # The browser may have accepted a prompt before its transport
            # failed.  Inspect the durable team record before considering a
            # retry; replaying an uncertain prompt can duplicate side effects.
            try:
                report = self.status_reader(
                    self.root / "data/browser-team/team.sqlite3", item.session)
                if report.get("unresolved_submissions"):
                    self.store.update(
                        item.id, status="awaiting_recovery",
                        checkpoint={"phase": "uncertain", "attempt": attempt,
                                    "session": item.session},
                        error="Browser transport failed after an uncertain submission")
                else:
                    self._failed(item, attempt, str(error))
            except Exception:
                self._failed(item, attempt, str(error))
        return True

    def _failed(self, item: QueuedTask, attempt: int, error: str) -> None:
        if attempt >= self.max_attempts:
            self.store.update(item.id, status="failed",
                              checkpoint={"phase": "exhausted", "attempt": attempt}, error=error)
            return
        delay = self.base_backoff * (2 ** (attempt - 1))
        self.store.update(item.id, status="retrying", next_attempt=_now() + delay,
                          checkpoint={"phase": "backoff", "attempt": attempt,
                                      "retry_at": datetime.fromtimestamp(
                                          _now() + delay, timezone.utc).isoformat()},
                          error=error)

    async def run_forever(self) -> None:
        while not self._stopping:
            if not await self.run_once():
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=self.poll_interval)
                    self._wake.clear()
                except asyncio.TimeoutError:
                    pass


def supervisor_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python run.py supervisor")
    commands = parser.add_subparsers(dest="command", required=True)
    enqueue = commands.add_parser("enqueue")
    enqueue.add_argument("task")
    enqueue.add_argument("--session")
    commands.add_parser("run")
    commands.add_parser("status")
    commands.add_parser("health", help="Check if browser team is ready to accept tasks")
    for command in (commands.choices["run"],):
        command.add_argument("--poll", type=float, default=5)
        command.add_argument("--max-attempts", type=int, default=3)
        command.add_argument("--backoff", type=float, default=2)
    return parser


async def run_supervisor_cli(root: Path, arguments: list[str]) -> int:
    options = supervisor_parser().parse_args(arguments)
    store = SupervisorStore(root / "data/browser-team/supervisor.sqlite3")
    supervisor = BrowserSupervisor(root, store, max_attempts=getattr(options, "max_attempts", 3),
                                  base_backoff=getattr(options, "backoff", 2),
                                  poll_interval=getattr(options, "poll", 5))
    try:
        if options.command == "enqueue":
            print("Queued task " + supervisor.enqueue(options.task, options.session))
            return 0
        if options.command == "status":
            print(json.dumps([asdict(t) for t in store.all()], indent=2))
            return 0
        if options.command == "health":
            # Check if browser team is ready to accept new tasks.
            try:
                report = supervisor.status_reader(root / "data/browser-team/team.sqlite3")
                members = report.get("members", [])
                ready_count = sum(1 for m in members if m.get("status") == "ready")
                blocked_count = sum(1 for m in members if m.get("status") == "blocked")
                uncertain_count = sum(1 for m in members if m.get("status") == "uncertain")
                print(json.dumps({
                    "healthy": ready_count > 0 and uncertain_count == 0 and blocked_count == 0,
                    "ready": ready_count,
                    "blocked": blocked_count,
                    "uncertain": uncertain_count,
                    "total": len(members),
                    "members": members,
                    "message": (
                        "Browser team is ready" if ready_count > 0 and uncertain_count == 0 and blocked_count == 0
                        else f"Browser team NOT ready: {ready_count} ready, {blocked_count} blocked, {uncertain_count} uncertain"
                    )
                }, indent=2))
                return 0 if ready_count > 0 and uncertain_count == 0 and blocked_count == 0 else 1
            except Exception as error:
                print(json.dumps({
                    "healthy": False,
                    "error": str(error),
                    "message": "Could not read browser team status"
                }, indent=2))
                return 1
        loop = asyncio.get_running_loop()
        for signum in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(signum, supervisor.stop)
            except (NotImplementedError, AttributeError):
                signal.signal(signum, lambda *_: supervisor.stop())
        await supervisor.run_forever()
        return 0
    finally:
        store.close()
