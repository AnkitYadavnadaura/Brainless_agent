import hashlib

import pytest

from app.autonomy.runtime_upgrade import RuntimeUpgradeManager, UpgradeManifest


def test_runtime_upgrade_verifies_stages_activates_and_rolls_back(tmp_path):
    artifact = tmp_path / "runtime.bin"
    artifact.write_bytes(b"trusted runtime")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manager = RuntimeUpgradeManager(tmp_path / "updates", trusted_versions=frozenset({"1.0.0", "2.0.0"}))
    first = UpgradeManifest("1.0.0", "runtime.bin", digest)
    manager.stage(first, artifact, lambda path: path.is_dir())
    manager.activate(first)
    assert manager.active_version() == "1.0.0"
    second = UpgradeManifest("2.0.0", "runtime.bin", digest)
    manager.stage(second, artifact, lambda path: path.is_dir())
    manager.activate(second)
    assert manager.active_version() == "2.0.0"
    manager.rollback("1.0.0")
    assert manager.active_version() == "1.0.0"


def test_runtime_upgrade_rejects_tampering_and_untrusted_versions(tmp_path):
    artifact = tmp_path / "runtime.bin"
    artifact.write_bytes(b"runtime")
    manager = RuntimeUpgradeManager(tmp_path / "updates", trusted_versions=frozenset({"1.0.0"}))
    with pytest.raises(ValueError, match="trusted"):
        manager.stage(UpgradeManifest("9.0.0", "runtime.bin", "0" * 64), artifact, lambda _: True)
    with pytest.raises(ValueError, match="hash"):
        manager.stage(UpgradeManifest("1.0.0", "runtime.bin", "0" * 64), artifact, lambda _: True)
