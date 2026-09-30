"""Transactional project, revision, request and checkpoint history for village work."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator


def project_id(objective: str) -> str:
    """Retain the existing village directory identity, including its exact text."""
    _text(objective, "Objective")
    return hashlib.sha256(objective.encode()).hexdigest()[:20]


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class VillageProjectStore:
    """Use independent, short connections so another CLI can enqueue during a build."""

    project_id = staticmethod(project_id)

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS village_projects (
                    id TEXT PRIMARY KEY,
                    objective TEXT NOT NULL,
                    latest_revision INTEGER REFERENCES village_revisions(id),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS village_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL REFERENCES village_projects(id),
                    text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    revision_id INTEGER REFERENCES village_revisions(id),
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS village_revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL REFERENCES village_projects(id),
                    objective TEXT NOT NULL,
                    parent_id INTEGER REFERENCES village_revisions(id),
                    request_id INTEGER REFERENCES village_requests(id),
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    plan_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS village_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL REFERENCES village_projects(id),
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS village_checkpoints (
                    revision_id INTEGER PRIMARY KEY REFERENCES village_revisions(id),
                    project_id TEXT NOT NULL REFERENCES village_projects(id),
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS modelling_session (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    project_id TEXT NOT NULL REFERENCES village_projects(id)
                );
                CREATE INDEX IF NOT EXISTS village_requests_queue
                    ON village_requests(project_id, status, id);
                CREATE INDEX IF NOT EXISTS village_revisions_project
                    ON village_revisions(project_id, id);
                CREATE INDEX IF NOT EXISTS village_events_project
                    ON village_events(project_id, id);
            """)

    @contextmanager
    def _connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys = ON")
            if write:
                db.execute("BEGIN IMMEDIATE")
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _project(db: sqlite3.Connection, identity: str) -> sqlite3.Row:
        row = db.execute("SELECT * FROM village_projects WHERE id=?", (identity,)).fetchone()
        if row is None:
            raise ValueError(f"Unknown village project: {identity}")
        return row

    @staticmethod
    def _revision(db: sqlite3.Connection, identity: int, owner: str | None = None) -> dict[str, Any]:
        row = db.execute("SELECT * FROM village_revisions WHERE id=?", (identity,)).fetchone()
        if row is None or (owner is not None and row["project_id"] != owner):
            raise ValueError("Unknown revision or revision belongs to another project")
        return VillageProjectStore._revision_dict(row)

    @staticmethod
    def _revision_dict(row: sqlite3.Row) -> dict[str, Any]:
        revision = dict(row)
        plan = revision.pop("plan_json")
        revision["plan"] = json.loads(plan) if plan is not None else None
        return revision

    @staticmethod
    def _request(db: sqlite3.Connection, identity: int, owner: str | None = None) -> sqlite3.Row:
        row = db.execute("SELECT * FROM village_requests WHERE id=?", (identity,)).fetchone()
        if row is None or (owner is not None and row["project_id"] != owner):
            raise ValueError("Unknown request or request belongs to another project")
        return row

    def ensure_project(self, objective: str) -> dict[str, Any]:
        identity = project_id(objective)
        with self._connection(write=True) as db:
            db.execute("INSERT OR IGNORE INTO village_projects(id,objective,latest_revision,created_at) "
                       "VALUES (?,?,NULL,?)", (identity, objective, _now()))
            row = self._project(db, identity)
            if row["objective"] != objective:
                raise ValueError("Village project identity collision")
            return dict(row)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self._connection() as db:
            row = db.execute("SELECT * FROM village_projects WHERE id=?", (project_id,)).fetchone()
            return dict(row) if row is not None else None

    def select_project(self, project_id: str) -> None:
        with self._connection(write=True) as db:
            self._project(db,project_id)
            db.execute('INSERT INTO modelling_session(singleton,project_id) VALUES(1,?) '
                       'ON CONFLICT(singleton) DO UPDATE SET project_id=excluded.project_id',(project_id,))

    def selected_project(self) -> dict[str, Any] | None:
        with self._connection() as db:
            row=db.execute('SELECT p.* FROM village_projects p JOIN modelling_session s ON p.id=s.project_id WHERE s.singleton=1').fetchone()
            return dict(row) if row else None

    def enqueue(self, project_id: str, text: str) -> dict[str, Any]:
        _text(text, "Update request")
        now = _now()
        with self._connection(write=True) as db:
            self._project(db, project_id)
            cursor = db.execute("INSERT INTO village_requests "
                                "(project_id,text,status,revision_id,error,created_at,updated_at) "
                                "VALUES (?,?,'pending',NULL,NULL,?,?)", (project_id, text, now, now))
            return dict(self._request(db, cursor.lastrowid))

    def requests(self, project_id: str, status: str | None = None) -> list[dict[str, Any]]:
        with self._connection() as db:
            self._project(db, project_id)
            if status is None:
                rows = db.execute("SELECT * FROM village_requests WHERE project_id=? ORDER BY id", (project_id,))
            else:
                rows = db.execute("SELECT * FROM village_requests WHERE project_id=? AND status=? ORDER BY id",
                                  (project_id, status))
            return [dict(row) for row in rows]

    def update_request(self, request_id: int, status: str, revision_id: int | None = None,
                       error: str | None = None) -> dict[str, Any]:
        _text(status, "Request status")
        with self._connection(write=True) as db:
            request = self._request(db, request_id)
            if revision_id is not None:
                self._revision(db, revision_id, request["project_id"])
            db.execute("UPDATE village_requests SET status=?,revision_id=?,error=?,updated_at=? WHERE id=?",
                       (status, revision_id, error, _now(), request_id))
            return dict(self._request(db, request_id))

    def create_revision(self, project_id: str, objective: str, parent_id: int | None,
                        request_id: int | None = None, plan: dict[str, Any] | None = None) -> dict[str, Any]:
        _text(objective, "Revision objective")
        if plan is not None and not isinstance(plan, dict):
            raise ValueError("Revision plan must be a JSON object")
        serialized = json.dumps(plan, sort_keys=True, allow_nan=False) if plan is not None else None
        now = _now()
        with self._connection(write=True) as db:
            self._project(db, project_id)
            if parent_id is not None:
                self._revision(db, parent_id, project_id)
            if request_id is not None:
                self._request(db, request_id, project_id)
            cursor = db.execute("INSERT INTO village_revisions "
                                "(project_id,objective,parent_id,request_id,status,result,error,plan_json,created_at,updated_at) "
                                "VALUES (?,?,?,?,'pending',NULL,NULL,?,?,?)",
                                (project_id, objective, parent_id, request_id, serialized, now, now))
            return dict(self._revision(db, cursor.lastrowid))

    def revisions(self, project_id: str) -> list[dict[str, Any]]:
        with self._connection() as db:
            self._project(db, project_id)
            return [self._revision_dict(row) for row in db.execute(
                "SELECT * FROM village_revisions WHERE project_id=? ORDER BY id", (project_id,))]

    def update_revision(self, revision_id: int, status: str, result: str | None = None,
                        error: str | None = None) -> dict[str, Any]:
        _text(status, "Revision status")
        with self._connection(write=True) as db:
            revision = self._revision(db, revision_id)
            db.execute("UPDATE village_revisions SET status=?,result=?,error=?,updated_at=? WHERE id=?",
                       (status, result, error, _now(), revision_id))
            if status in {"completed", "needs_attention"}:
                db.execute("UPDATE village_projects SET latest_revision=? WHERE id=?",
                           (revision_id, revision["project_id"]))
            return dict(self._revision(db, revision_id))

    def append_event(self, project_id: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        _text(kind, "Event kind")
        if not isinstance(payload, dict):
            raise ValueError("Event payload must be a JSON object")
        serialized = json.dumps(payload, sort_keys=True, allow_nan=False)
        now = _now()
        with self._connection(write=True) as db:
            self._project(db, project_id)
            cursor = db.execute("INSERT INTO village_events(project_id,kind,payload_json,created_at) VALUES (?,?,?,?)",
                                (project_id, kind, serialized, now))
            return dict(id=cursor.lastrowid, project_id=project_id, kind=kind,
                        payload=json.loads(serialized), created_at=now)

    def events(self, project_id: str) -> list[dict[str, Any]]:
        with self._connection() as db:
            self._project(db, project_id)
            events = []
            for row in db.execute("SELECT * FROM village_events WHERE project_id=? ORDER BY id", (project_id,)):
                event = dict(row)
                event["payload"] = json.loads(event.pop("payload_json"))
                events.append(event)
            return events

    def save_checkpoint(self, project_id: str, revision_id: int, state: dict[str, Any]) -> None:
        if not isinstance(state, dict):
            raise ValueError("Checkpoint must be a JSON object")
        serialized = json.dumps(state, sort_keys=True, allow_nan=False)
        with self._connection(write=True) as db:
            self._revision(db, revision_id, project_id)
            db.execute("INSERT INTO village_checkpoints(revision_id,project_id,state_json,updated_at) VALUES (?,?,?,?) "
                       "ON CONFLICT(revision_id) DO UPDATE SET state_json=excluded.state_json,updated_at=excluded.updated_at",
                       (revision_id, project_id, serialized, _now()))

    def load_checkpoint(self, project_id: str, revision_id: int) -> dict[str, Any] | None:
        with self._connection() as db:
            self._revision(db, revision_id, project_id)
            row = db.execute("SELECT state_json FROM village_checkpoints WHERE project_id=? AND revision_id=?",
                             (project_id, revision_id)).fetchone()
            return json.loads(row["state_json"]) if row is not None else None
