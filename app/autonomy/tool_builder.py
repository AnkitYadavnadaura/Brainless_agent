"""Staged construction of small, inspectable CLI tools.

The agent may propose a wrapper, but only this builder writes it. Generated
source is data until a caller explicitly validates and promotes the tool.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ToolDraft:
    tool_id: str
    executable: str
    arguments: tuple[str, ...]
    path: Path
    status: str


class ToolBuilder:
    """Build allow-listed wrappers from discovered executables."""

    _SAFE = re.compile(r"^[A-Za-z0-9_.:/@+=,-]+$")

    def __init__(self, root: Path, allowed_executables: set[str] | None = None) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.allowed_executables = allowed_executables or set()

    def stage(self, tool_id: str, executable: str, arguments: list[str]) -> ToolDraft:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,80}", tool_id):
            raise ValueError("Tool id is invalid")
        if executable not in self.allowed_executables:
            raise ValueError("Executable was not discovered and allow-listed")
        if any(not isinstance(arg, str) or not self._SAFE.fullmatch(arg) for arg in arguments):
            raise ValueError("Tool arguments contain unsupported characters")
        path = self.root / (tool_id + ".json")
        path.write_text(json.dumps({
            "tool_id": tool_id, "executable": executable,
            "arguments": arguments, "status": "staged",
        }, indent=2), encoding="utf-8")
        return ToolDraft(tool_id, executable, tuple(arguments), path, "staged")

    def promote(self, draft: ToolDraft) -> ToolDraft:
        if draft.status != "staged" or draft.path.resolve().parent != self.root:
            raise ValueError("Only a staged local draft can be promoted")
        data = json.loads(draft.path.read_text(encoding="utf-8"))
        if data.get("status") != "staged":
            raise ValueError("Tool draft is not staged")
        data["status"] = "active"
        draft.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return ToolDraft(draft.tool_id, draft.executable, draft.arguments, draft.path, "active")
