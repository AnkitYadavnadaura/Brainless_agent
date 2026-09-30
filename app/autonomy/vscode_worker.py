"""Controlled coordination bridge for VS Code and local coding agents.

Browser providers remain the planner and authority. This module only executes
explicit, bounded worker actions after a validated plan has selected them.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class WorkerAvailability:
    vscode: str | None
    codex: str | None
    copilot: str | None
    python: str | None
    git: str | None


class VscodeWorker:
    """Run safe repository work and coordinate local coding agents."""

    def __init__(self, workspace: Path, *, timeout: float = 900) -> None:
        self.workspace = workspace.resolve()
        if not self.workspace.is_dir():
            raise ValueError("VS Code workspace must be an existing directory")
        if not 10 <= timeout <= 3600:
            raise ValueError("VS Code worker timeout must be between 10 and 3600 seconds")
        self.timeout = timeout

    def discover(self) -> WorkerAvailability:
        return WorkerAvailability(
            vscode=self._which(("code", "code.cmd")),
            codex=self._which(("codex", "codex.cmd")),
            copilot=self._which(("copilot", "copilot.cmd")),
            python=self._which(("python", "python.exe")),
            git=self._which(("git", "git.exe")),
        )

    async def open_workspace(self) -> dict[str, str]:
        executable = self.discover().vscode
        if executable is None:
            raise RuntimeError("VS Code CLI was not found")
        result = await self._run([executable, "--reuse-window", str(self.workspace)])
        if result["returncode"] != 0:
            raise RuntimeError("VS Code failed to open workspace: " + result["stderr"][-1000:])
        return {"workspace": str(self.workspace), "executable": executable}

    async def open_file(self, relative_path: str) -> dict[str, str]:
        path = self._workspace_path(relative_path)
        if not path.is_file():
            raise FileNotFoundError(f"Workspace file does not exist: {relative_path}")
        executable = self._require_vscode()
        result = await self._run([executable, "--reuse-window", str(path)])
        if result["returncode"] != 0:
            raise RuntimeError("VS Code failed to open file: " + result["stderr"][-1000:])
        return {"workspace": str(self.workspace), "file": str(path), "executable": executable}

    async def list_extensions(self) -> list[str]:
        executable = self._require_vscode()
        result = await self._run([executable, "--list-extensions"])
        if result["returncode"] != 0:
            raise RuntimeError("VS Code failed to list extensions: " + result["stderr"][-1000:])
        return [line.strip() for line in result["stdout"].splitlines() if line.strip()]

    async def install_extension(self, extension_id: str) -> dict[str, Any]:
        self._validate_extension_id(extension_id)
        executable = self._require_vscode()
        return await self._run([executable, "--install-extension", extension_id])

    async def uninstall_extension(self, extension_id: str) -> dict[str, Any]:
        self._validate_extension_id(extension_id)
        executable = self._require_vscode()
        return await self._run([executable, "--uninstall-extension", extension_id])

    async def validate(self, command: str = "python -m pytest -q") -> dict[str, Any]:
        parts = command.split()
        allowed = {
            "python": ("python", "python.exe"),
            "pytest": ("pytest", "pytest.exe"),
            "git": ("git", "git.exe"),
            "npm": ("npm", "npm.cmd"),
        }
        if not parts or parts[0] not in allowed:
            raise ValueError("Validation must start with an allow-listed executable")
        executable = self._which(allowed[parts[0]])
        if executable is None:
            raise RuntimeError(f"Validation executable is unavailable: {parts[0]}")
        result = await self._run([executable, *parts[1:]])
        return result

    async def delegate(self, worker: str, prompt: str) -> dict[str, Any]:
        """Invoke an installed coding-agent CLI with a single explicit prompt.

        The browser leader must authorize this call by selecting the worker in
        its plan. The prompt is passed as an argument, never through a shell.
        """
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 20_000:
            raise ValueError("Worker prompt must contain 1..20000 characters")
        names = {
            "codex": ("codex", "codex.cmd"),
            "copilot": ("copilot", "copilot.cmd"),
        }
        if worker not in names:
            raise ValueError("Worker must be codex or copilot")
        executable = self._which(names[worker])
        if executable is None:
            raise RuntimeError(f"{worker} CLI was not found")
        return await self._run([executable, prompt])

    def _require_vscode(self) -> str:
        executable = self.discover().vscode
        if executable is None:
            raise RuntimeError("VS Code CLI was not found")
        return executable

    def _workspace_path(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Workspace path is required")
        path = (self.workspace / relative_path).resolve()
        if path != self.workspace and self.workspace not in path.parents:
            raise ValueError("Workspace path escapes the repository")
        return path

    @staticmethod
    def _validate_extension_id(extension_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,127}", extension_id):
            raise ValueError("Invalid VS Code extension identifier")

    def write_coordination_packet(self, task_id: str, objective: str,
                                  plan: dict[str, Any]) -> Path:
        if not task_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
                              for char in task_id):
            raise ValueError("Task ID contains unsupported characters")
        packet_dir = self.workspace / "data" / "vscode-coordination"
        packet_dir.mkdir(parents=True, exist_ok=True)
        packet = packet_dir / f"{task_id}.json"
        packet.write_text(json.dumps({
            "task_id": task_id,
            "objective": objective,
            "authority": "browser-leader",
            "workers": ["browser-leader", "browser-team", "vscode-copilot", "codex", "vscode-agent"],
            "plan": plan,
            "status": "planned",
        }, indent=2, sort_keys=True), encoding="utf-8")
        return packet

    async def _run(self, command: list[str]) -> dict[str, Any]:
        process = await asyncio.create_subprocess_exec(
            *command, cwd=str(self.workspace),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), self.timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError(f"Worker command timed out: {command[0]}")
        return {
            "command": command,
            "returncode": process.returncode,
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
        }

    @staticmethod
    def _which(names: tuple[str, ...]) -> str | None:
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return None
