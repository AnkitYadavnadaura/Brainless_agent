from __future__ import annotations

import pytest

from app.autonomy.environment import BoundaryMemory, EnvironmentExplorer
from app.autonomy.tool_builder import ToolBuilder


@pytest.mark.asyncio
async def test_environment_explorer_is_bounded_and_reports_available_tools():
    snapshot = await EnvironmentExplorer(executables=("python",), help_timeout=2).explore()
    assert "python" in snapshot.executables
    assert len(snapshot.help_text["python"]) <= 4000


def test_boundary_memory_records_known_failure(tmp_path):
    memory = BoundaryMemory(tmp_path / "boundaries.db")
    try:
        memory.record("youtube_play", "recommendation", "failure", "No recommendation available")
        rows = memory.known("youtube_play", "recommendation", "failure")
        assert rows[0]["detail"] == "No recommendation available"
    finally:
        memory.close()


def test_tool_builder_only_stages_discovered_allow_listed_executables(tmp_path):
    builder = ToolBuilder(tmp_path, {"ffmpeg"})
    draft = builder.stage("extract-audio", "ffmpeg", ["-version"])
    assert draft.status == "staged"
    assert builder.promote(draft).status == "active"
    with pytest.raises(ValueError):
        builder.stage("unsafe", "powershell", ["-Command"])
