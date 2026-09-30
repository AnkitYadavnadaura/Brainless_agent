"""Sandbox-first lifecycle for discovering and promoting new capabilities.

Website reasoning may propose capability metadata, but it never supplies code or
authority.  Only runtime-owned builders can produce handlers, and promotion is
gated by validation, health checks, and an explicit policy decision.
"""
from __future__ import annotations

import inspect
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import uuid4

from app.agents.tools import RiskLevel, ToolHandler, ToolRegistry, ToolSpec


class CapabilityStatus(str, Enum):
    DISCOVERED = "discovered"
    STAGED = "staged"
    VALIDATED = "validated"
    ACTIVE = "active"
    DEGRADED = "degraded"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class CapabilityRequest:
    capability_id: str
    goal: str
    required_tools: frozenset[str]
    required_permissions: frozenset[str]
    discovery_query: str
    constraints: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CapabilityCandidate:
    capability_id: str
    version: str
    tool_id: str
    name: str
    description: str
    required_permissions: frozenset[str]
    risk: RiskLevel
    input_schema: tuple[str, ...]
    output_schema: str
    source: str
    builder_key: str
    health_check_key: str
    metadata: dict[str, str] = field(default_factory=dict)
    candidate_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True, slots=True)
class CapabilityRecord:
    candidate_id: str
    capability_id: str
    version: str
    tool_id: str
    status: CapabilityStatus
    source: str
    updated_at: str
    failure: str | None = None


Builder = Callable[[CapabilityCandidate, Path], ToolHandler]
HealthCheck = Callable[[ToolSpec, Path], bool | Awaitable[bool]]


class CapabilityStore:
    """Durable lifecycle metadata; handlers are intentionally never serialized."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS capability_versions (
            candidate_id TEXT PRIMARY KEY, capability_id TEXT NOT NULL,
            version TEXT NOT NULL, tool_id TEXT NOT NULL, status TEXT NOT NULL,
            source TEXT NOT NULL, updated_at TEXT NOT NULL, failure TEXT)"""
        )
        self.db.commit()

    def save(self, record: CapabilityRecord) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO capability_versions VALUES (?,?,?,?,?,?,?,?)",
            (record.candidate_id, record.capability_id, record.version,
             record.tool_id, record.status.value, record.source,
             record.updated_at, record.failure),
        )
        self.db.commit()

    def latest(self, capability_id: str) -> CapabilityRecord | None:
        row = self.db.execute(
            "SELECT * FROM capability_versions WHERE capability_id=? "
            "ORDER BY updated_at DESC LIMIT 1", (capability_id,)
        ).fetchone()
        return self._record(row) if row else None

    def history(self, capability_id: str) -> tuple[CapabilityRecord, ...]:
        rows = self.db.execute(
            "SELECT * FROM capability_versions WHERE capability_id=? ORDER BY updated_at",
            (capability_id,),
        ).fetchall()
        return tuple(self._record(row) for row in rows)

    @staticmethod
    def _record(row: sqlite3.Row) -> CapabilityRecord:
        return CapabilityRecord(
            row["candidate_id"], row["capability_id"], row["version"],
            row["tool_id"], CapabilityStatus(row["status"]), row["source"],
            row["updated_at"], row["failure"],
        )

    def close(self) -> None:
        self.db.close()


class CapabilityLifecycle:
    """Automates capability promotion without executing untrusted generated code."""

    def __init__(self, registry: ToolRegistry, store: CapabilityStore,
                 sandbox_root: Path, *, allow_sources: frozenset[str] = frozenset()) -> None:
        self.registry, self.store = registry, store
        self.sandbox_root = sandbox_root.resolve()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        self.allow_sources = allow_sources
        self.builders: dict[str, Builder] = {}
        self.health_checks: dict[str, HealthCheck] = {}
        self._handlers: dict[str, ToolHandler] = {}
        self._previous: dict[str, ToolSpec] = {}

    def register_builder(self, key: str, builder: Builder, health_check: HealthCheck) -> None:
        if not key.strip():
            raise ValueError("Builder key cannot be empty")
        self.builders[key] = builder
        self.health_checks[key] = health_check

    async def acquire(self, candidate: CapabilityCandidate) -> CapabilityRecord:
        try:
            self._validate_candidate(candidate)
        except Exception as error:
            return self._save(candidate, CapabilityStatus.REJECTED, str(error))
        now = self._now()
        record = CapabilityRecord(candidate.candidate_id, candidate.capability_id,
                                  candidate.version, candidate.tool_id,
                                  CapabilityStatus.DISCOVERED, candidate.source, now)
        self.store.save(record)
        try:
            workspace = self.sandbox_root / candidate.candidate_id
            workspace.mkdir(parents=True, exist_ok=False)
            builder = self.builders.get(candidate.builder_key)
            if builder is None:
                raise ValueError(f"Unknown trusted capability builder: {candidate.builder_key}")
            handler = builder(candidate, workspace)
            if not callable(handler):
                raise TypeError("Capability builder must return a callable handler")
            self._handlers[candidate.candidate_id] = handler
            record = self._save(candidate, CapabilityStatus.STAGED)
            spec = ToolSpec(
                candidate.tool_id, candidate.name, candidate.description,
                candidate.required_permissions, candidate.risk, handler,
                candidate.input_schema, candidate.output_schema,
                category=candidate.capability_id,
            )
            if not await self._health(candidate, spec, workspace):
                raise RuntimeError("Capability health check failed")
            record = self._save(candidate, CapabilityStatus.VALIDATED)
            return record
        except Exception as error:
            return self._save(candidate, CapabilityStatus.REJECTED, str(error))

    async def promote(self, candidate: CapabilityCandidate) -> CapabilityRecord:
        record = self.store.latest(candidate.capability_id)
        if record is None or record.candidate_id != candidate.candidate_id \
                or record.status is not CapabilityStatus.VALIDATED:
            raise ValueError("Only a validated candidate can be promoted")
        handler = self._handlers.get(candidate.candidate_id)
        if handler is None:
            raise RuntimeError("Validated capability handler is not loaded")
        if self.registry.contains(candidate.tool_id):
            self._previous[candidate.tool_id] = self.registry.get(candidate.tool_id)
            self.registry.unregister(candidate.tool_id)
        self.registry.register(ToolSpec(
            candidate.tool_id, candidate.name, candidate.description,
            candidate.required_permissions, candidate.risk, handler,
            candidate.input_schema, candidate.output_schema,
            category=candidate.capability_id,
        ))
        return self._save(candidate, CapabilityStatus.ACTIVE)

    async def health_check(self, candidate: CapabilityCandidate) -> bool:
        if not self.registry.contains(candidate.tool_id):
            return False
        spec = self.registry.get(candidate.tool_id)
        workspace = self.sandbox_root / candidate.candidate_id
        return await self._health(candidate, spec, workspace)

    def rollback(self, candidate: CapabilityCandidate) -> CapabilityRecord:
        if self.registry.contains(candidate.tool_id):
            self.registry.unregister(candidate.tool_id)
        previous = self._previous.pop(candidate.tool_id, None)
        if previous is not None:
            self.registry.register(previous)
        return self._save(candidate, CapabilityStatus.ROLLED_BACK)

    def _validate_candidate(self, candidate: CapabilityCandidate) -> None:
        if self.allow_sources and candidate.source not in self.allow_sources:
            raise ValueError("Capability source is not trusted by runtime policy")
        if not candidate.capability_id or not candidate.tool_id or not candidate.version:
            raise ValueError("Capability identity and version are required")
        if candidate.tool_id != candidate.capability_id and not candidate.tool_id.startswith(candidate.capability_id + "."):
            raise ValueError("Tool must belong to its declared capability")
        if any(value.strip() == "" for value in candidate.input_schema):
            raise ValueError("Input schema contains an empty field")

    async def _health(self, candidate: CapabilityCandidate, spec: ToolSpec, workspace: Path) -> bool:
        check = self.health_checks.get(candidate.health_check_key)
        if check is None:
            raise ValueError(f"Unknown trusted health check: {candidate.health_check_key}")
        result = check(spec, workspace)
        return bool(await result) if inspect.isawaitable(result) else bool(result)

    def _save(self, candidate: CapabilityCandidate, status: CapabilityStatus,
              failure: str | None = None) -> CapabilityRecord:
        record = CapabilityRecord(candidate.candidate_id, candidate.capability_id,
                                  candidate.version, candidate.tool_id, status,
                                  candidate.source, self._now(), failure)
        self.store.save(record)
        return record

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
