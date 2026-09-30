import asyncio

from app.agents.tools import RiskLevel, ToolRegistry, ToolSpec
from app.autonomy.capability_lifecycle import (
    CapabilityCandidate,
    CapabilityLifecycle,
    CapabilityStatus,
    CapabilityStore,
)


def candidate(*, version="1.0.0", source="trusted-catalog"):
    return CapabilityCandidate(
        capability_id="video.edit",
        version=version,
        tool_id="video.edit",
        name="Video editor",
        description="Edits media in an isolated workspace",
        required_permissions=frozenset({"filesystem.read", "filesystem.write"}),
        risk=RiskLevel.MEDIUM,
        input_schema=("input", "output"),
        output_schema="path",
        source=source,
        builder_key="trusted-video",
        health_check_key="trusted-video",
    )


def test_capability_lifecycle_validates_stages_promotes_and_rolls_back(tmp_path):
    registry = ToolRegistry()
    registry.register(ToolSpec(
        "video.edit", "Old editor", "old", frozenset(), RiskLevel.LOW,
        lambda _: "old",
    ))
    lifecycle = CapabilityLifecycle(
        registry, CapabilityStore(tmp_path / "capabilities.db"),
        tmp_path / "sandbox", allow_sources=frozenset({"trusted-catalog"}),
    )
    def build(_candidate, workspace):
        workspace.joinpath("manifest.json").write_text("{}", encoding="utf-8")
        return lambda arguments: arguments["output"]

    lifecycle.register_builder(
        "trusted-video",
        build,
        lambda spec, workspace: spec.tool_id == "video.edit" and workspace.is_dir(),
    )
    item = candidate()
    assert asyncio.run(lifecycle.acquire(item)).status is CapabilityStatus.VALIDATED
    assert asyncio.run(lifecycle.promote(item)).status is CapabilityStatus.ACTIVE
    assert asyncio.run(registry.invoke("video.edit", {"input": "a", "output": "b"})) == "b"
    assert lifecycle.rollback(item).status is CapabilityStatus.ROLLED_BACK
    assert asyncio.run(registry.invoke("video.edit", {})) == "old"


def test_untrusted_candidate_is_rejected_and_never_registered(tmp_path):
    registry = ToolRegistry()
    lifecycle = CapabilityLifecycle(
        registry, CapabilityStore(tmp_path / "capabilities.db"),
        tmp_path / "sandbox", allow_sources=frozenset({"trusted-catalog"}),
    )
    item = candidate(source="random-web-page")
    result = asyncio.run(lifecycle.acquire(item))
    assert result.status is CapabilityStatus.REJECTED
    assert not registry.contains(item.tool_id)


def test_failed_health_check_cannot_be_promoted(tmp_path):
    registry = ToolRegistry()
    lifecycle = CapabilityLifecycle(
        registry, CapabilityStore(tmp_path / "capabilities.db"),
        tmp_path / "sandbox",
    )
    lifecycle.register_builder(
        "trusted-video",
        lambda _candidate, _workspace: lambda _arguments: "not safe",
        lambda _spec, _workspace: False,
    )
    item = candidate()
    assert asyncio.run(lifecycle.acquire(item)).status is CapabilityStatus.REJECTED
    try:
        asyncio.run(lifecycle.promote(item))
    except ValueError:
        pass
    else:
        raise AssertionError("Rejected capability was promoted")
