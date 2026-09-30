"""Runtime exploration and boundary memory for universal missions.

Exploration is read-only and bounded. It discovers what the current machine
offers before planning; it never treats a command's help text as permission
to execute that command.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sqlite3
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EnvironmentSnapshot:
    platform: str
    cwd: str
    executables: dict[str, str]
    help_text: dict[str, str]
    browser_available: bool
    blender_available: bool
    unreal_available: bool


class EnvironmentExplorer:
    """Discover local entry points without running user-supplied commands."""

    DEFAULT_EXECUTABLES = (
        "python", "git", "curl", "ffmpeg", "npm", "node", "docker",
        "sha256sum", "shasum", "certutil",
        "blender", "UnrealEditor", "chrome", "msedge",
    )

    def __init__(self, *, executables: tuple[str, ...] = DEFAULT_EXECUTABLES,
                 help_timeout: float = 2.0) -> None:
        if not 0 < help_timeout <= 10:
            raise ValueError("Help timeout must be between 0 and 10 seconds")
        self.executables, self.help_timeout = executables, help_timeout

    async def explore(self) -> EnvironmentSnapshot:
        found = {name: path for name in self.executables
                 if (path := shutil.which(name)) is not None}
        help_text: dict[str, str] = {}
        for name, path in found.items():
            if name in {"chrome", "msedge", "blender", "UnrealEditor"}:
                # GUI applications may launch a window even for --help.
                continue
            try:
                result = await asyncio.to_thread(
                    subprocess.run, [path, "--help"], capture_output=True,
                    text=True, timeout=self.help_timeout, check=False,
                )
                help_text[name] = (result.stdout or result.stderr)[:4000]
            except (OSError, subprocess.SubprocessError):
                help_text[name] = ""
        return EnvironmentSnapshot(
            platform=os.name, cwd=str(Path.cwd()), executables=found,
            help_text=help_text, browser_available=any(
                name in found for name in ("chrome", "msedge")
            ),
            blender_available="blender" in found,
            unreal_available="UnrealEditor" in found,
        )


class BoundaryMemory:
    """Durable success/failure memory used to avoid repeating known failures."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS boundaries (
            id INTEGER PRIMARY KEY, capability TEXT NOT NULL, signature TEXT NOT NULL,
            outcome TEXT NOT NULL, detail TEXT NOT NULL, created REAL NOT NULL,
            UNIQUE(capability, signature, outcome))"""
        )
        self.db.commit()

    def record(self, capability: str, signature: str, outcome: str, detail: str) -> None:
        if not all(isinstance(value, str) and value.strip()
                   for value in (capability, signature, outcome, detail)):
            raise ValueError("Boundary records require non-empty text")
        self.db.execute(
            "INSERT OR REPLACE INTO boundaries(capability,signature,outcome,detail,created) "
            "VALUES(?,?,?,?,?)", (capability, signature, outcome, detail[:2000], time.time())
        )
        self.db.commit()

    def known(self, capability: str, signature: str, outcome: str | None = None) -> tuple[dict, ...]:
        query = "SELECT capability,signature,outcome,detail,created FROM boundaries WHERE capability=? AND signature=?"
        args: list[str] = [capability, signature]
        if outcome is not None:
            query += " AND outcome=?"
            args.append(outcome)
        query += " ORDER BY created DESC"
        return tuple(dict(row) for row in self.db.execute(query, args).fetchall())

    def close(self) -> None:
        self.db.close()
