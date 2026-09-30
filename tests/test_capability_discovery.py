import asyncio
import json

from app.agents.tools import ToolRegistry
from app.autonomy.capability_discovery import (
    CapabilityDiscoveryError,
    DiscoveryContext,
    WebsiteCapabilityDiscovery,
)
from app.autonomy.capability_lifecycle import CapabilityLifecycle, CapabilityStore


class FakeProvider:
    def __init__(self, response):
        self.response = response

    async def open(self):
        pass

    async def verify_page(self):
        pass

    async def start_conversation(self):
        pass

    async def send_prompt(self, _):
        pass

    async def wait_for_response(self):
        pass

    async def extract_response(self):
        return self.response


def context():
    return DiscoveryContext(
        "edit a video", "video_editing", frozenset({"video.edit"}),
        frozenset({"filesystem.read"}), ("trusted-video",),
    )


def test_website_metadata_is_converted_to_a_candidate_without_executing_code(tmp_path):
    lifecycle = CapabilityLifecycle(
        ToolRegistry(), CapabilityStore(tmp_path / "capabilities.db"),
        tmp_path / "sandbox",
    )
    lifecycle.register_builder("trusted-video", lambda *_: lambda _: "ok", lambda *_: True)
    response = json.dumps({
        "version": "1.0.0", "tool_id": "video.edit", "name": "Video",
        "description": "Edit video", "source": "trusted-catalog",
        "builder_key": "trusted-video", "health_check_key": "trusted-video",
        "input_schema": ["input"], "output_schema": "path", "risk": "medium",
    })
    candidate = asyncio.run(
        WebsiteCapabilityDiscovery(FakeProvider(response), lifecycle).discover(context())
    )
    assert candidate.tool_id == "video.edit"
    assert candidate.required_permissions == frozenset({"filesystem.read"})


def test_website_cannot_select_unregistered_builder_or_change_tool_identity(tmp_path):
    lifecycle = CapabilityLifecycle(
        ToolRegistry(), CapabilityStore(tmp_path / "capabilities.db"),
        tmp_path / "sandbox",
    )
    response = json.dumps({
        "version": "1.0.0", "tool_id": "process.execute", "name": "Unsafe",
        "description": "Unsafe", "source": "web", "builder_key": "unknown",
        "health_check_key": "unknown", "input_schema": [], "output_schema": "any",
        "risk": "high",
    })
    try:
        asyncio.run(
            WebsiteCapabilityDiscovery(FakeProvider(response), lifecycle).discover(context())
        )
    except CapabilityDiscoveryError:
        pass
    else:
        raise AssertionError("Untrusted website metadata was accepted")
