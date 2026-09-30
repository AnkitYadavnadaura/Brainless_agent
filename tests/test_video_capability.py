import asyncio

import pytest

from app.autonomy.video_capability import _safe_path, build_ffmpeg_video_tool


def test_video_paths_cannot_escape_sandbox(tmp_path):
    with pytest.raises(ValueError):
        _safe_path(tmp_path, "../outside.mp4")


def test_video_builder_requires_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setattr("app.autonomy.video_capability.shutil.which", lambda _: None)
    candidate = type("Candidate", (), {})()
    with pytest.raises(RuntimeError, match="FFmpeg"):
        build_ffmpeg_video_tool(candidate, tmp_path)
