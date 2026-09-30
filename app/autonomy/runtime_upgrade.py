"""Atomic, verified runtime upgrade channel.

An upgrade is data until it is staged, hash-verified, health-checked, and
activated for the next process start. This module never executes downloaded
code and never changes the current process in place.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True, slots=True)
class UpgradeManifest:
    version: str
    artifact: str
    sha256: str


class RuntimeUpgradeManager:
    def __init__(self, root: Path, *, trusted_versions: frozenset[str] = frozenset()) -> None:
        self.root = root.resolve()
        self.staging = self.root / "staging"
        self.versions = self.root / "versions"
        self.pointer = self.root / "active.json"
        self.staging.mkdir(parents=True, exist_ok=True)
        self.versions.mkdir(parents=True, exist_ok=True)
        self.trusted_versions = trusted_versions

    def stage(self, manifest: UpgradeManifest, artifact: Path,
              health_check: Callable[[Path], bool]) -> Path:
        self._validate_manifest(manifest, artifact)
        target = self.staging / manifest.version
        if target.exists():
            shutil.rmtree(target)
        target.mkdir()
        copied = target / Path(manifest.artifact).name
        shutil.copyfile(artifact, copied)
        if not health_check(target):
            shutil.rmtree(target)
            raise ValueError("Staged runtime failed health check")
        return target

    def activate(self, manifest: UpgradeManifest) -> None:
        staged = self.staging / manifest.version
        if not staged.is_dir():
            raise ValueError("Runtime version is not staged")
        active = self._read_active()
        if active is not None:
            (self.versions / active["version"]).mkdir(exist_ok=True)
        temporary = self.pointer.with_suffix(".tmp")
        temporary.write_text(json.dumps({"version": manifest.version}, sort_keys=True), encoding="utf-8")
        temporary.replace(self.pointer)

    def rollback(self, version: str) -> None:
        if not (self.staging / version).is_dir() and not (self.versions / version).is_dir():
            raise ValueError("Requested rollback version is unavailable")
        temporary = self.pointer.with_suffix(".tmp")
        temporary.write_text(json.dumps({"version": version}, sort_keys=True), encoding="utf-8")
        temporary.replace(self.pointer)

    def active_version(self) -> str | None:
        active = self._read_active()
        return str(active["version"]) if active else None

    def _validate_manifest(self, manifest: UpgradeManifest, artifact: Path) -> None:
        if self.trusted_versions and manifest.version not in self.trusted_versions:
            raise ValueError("Runtime version is not trusted by policy")
        if not manifest.version.strip() or Path(manifest.artifact).name != manifest.artifact:
            raise ValueError("Invalid runtime artifact identity")
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        if digest.casefold() != manifest.sha256.casefold():
            raise ValueError("Runtime artifact hash mismatch")

    def _read_active(self) -> dict[str, str] | None:
        if not self.pointer.exists():
            return None
        value = json.loads(self.pointer.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("version"), str):
            raise ValueError("Corrupt active runtime pointer")
        return value
