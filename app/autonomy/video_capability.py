"""Trusted local video capability backed by an installed FFmpeg executable."""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

from app.agents.tools import RiskLevel, ToolSpec
from app.autonomy.capability_lifecycle import CapabilityCandidate


def build_ffmpeg_video_tool(candidate: CapabilityCandidate, workspace: Path):
    """Build a repository-scoped video adapter; no shell string is ever parsed."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("FFmpeg is not installed or is not available on PATH")
    root = workspace.resolve()

    async def edit(arguments: dict[str, Any]) -> str:
        input_path = _safe_path(root, arguments["input"])
        output_path = _safe_path(root, arguments["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [ffmpeg, "-y", "-i", str(input_path)]
        if arguments.get("trim_start") is not None:
            command.extend(["-ss", str(float(arguments["trim_start"]))])
        if arguments.get("duration") is not None:
            command.extend(["-t", str(float(arguments["duration"]))])
        command.append(str(output_path))
        process = await asyncio.create_subprocess_exec(
            *command, cwd=str(root), stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg failed with exit code {process.returncode}: "
                               f"{stderr.decode(errors='replace')[-500:]}")
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise RuntimeError("FFmpeg did not produce a valid output file")
        return str(output_path)

    return edit


def health_check_ffmpeg(spec: ToolSpec, workspace: Path) -> bool:
    return spec.tool_id == "video.edit" and shutil.which("ffmpeg") is not None and workspace.is_dir()


def video_candidate() -> CapabilityCandidate:
    return CapabilityCandidate(
        capability_id="video.edit",
        version="1.0.0",
        tool_id="video.edit",
        name="Local FFmpeg video editor",
        description="Trim and transcode video inside the capability sandbox",
        required_permissions=frozenset({"filesystem.read", "filesystem.write"}),
        risk=RiskLevel.MEDIUM,
        input_schema=("input", "output"),
        output_schema="path",
        source="trusted-catalog",
        builder_key="ffmpeg-video",
        health_check_key="ffmpeg-video",
    )


def _safe_path(root: Path, value: object) -> Path:
    path = (root / str(value)).resolve()
    if path != root and root not in path.parents:
        raise ValueError("Video paths must remain inside the capability sandbox")
    return path
