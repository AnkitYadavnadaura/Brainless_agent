import json

import pytest

from app.autonomy.vscode_worker import VscodeWorker


def test_coordination_packet_is_browser_authorized(tmp_path):
    worker = VscodeWorker(tmp_path)
    packet = worker.write_coordination_packet(
        "task-1", "Add a feature", {"steps": ["edit", "test"]})

    data = json.loads(packet.read_text(encoding="utf-8"))
    assert data["authority"] == "browser-leader"
    assert "vscode-copilot" in data["workers"]
    assert data["plan"]["steps"] == ["edit", "test"]


def test_coordination_packet_rejects_path_escape(tmp_path):
    worker = VscodeWorker(tmp_path)
    with pytest.raises(ValueError):
        worker.write_coordination_packet("../escape", "bad", {})


@pytest.mark.asyncio
async def test_validation_rejects_unapproved_commands(tmp_path):
    worker = VscodeWorker(tmp_path)
    with pytest.raises(ValueError, match="allow-listed"):
        await worker.validate("powershell Remove-Item important.txt")


@pytest.mark.asyncio
async def test_delegate_rejects_unknown_worker(tmp_path):
    worker = VscodeWorker(tmp_path)
    with pytest.raises(ValueError, match="codex or copilot"):
        await worker.delegate("shell", "delete everything")


def test_workspace_path_rejects_escape(tmp_path):
    worker = VscodeWorker(tmp_path)
    with pytest.raises(ValueError, match="escapes"):
        worker._workspace_path("../outside.txt")


def test_extension_id_is_validated(tmp_path):
    worker = VscodeWorker(tmp_path)
    with pytest.raises(ValueError, match="extension"):
        worker._validate_extension_id("publisher/$(Remove-Item)")
