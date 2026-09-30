"""Browser-based capability discovery connected to the trusted lifecycle.

The website is used only for research and structured metadata. It cannot choose
an executable module, provide Python, or grant permissions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.agents.tools import RiskLevel
from app.autonomy.capability_lifecycle import (
    CapabilityCandidate,
    CapabilityLifecycle,
    CapabilityRecord,
    CapabilityStatus,
)


class CapabilityDiscoveryError(ValueError):
    """Raised when a website response is not safe structured metadata."""


@dataclass(frozen=True, slots=True)
class DiscoveryContext:
    goal: str
    capability_id: str
    required_tools: frozenset[str]
    required_permissions: frozenset[str]
    trusted_builders: tuple[str, ...]


class WebsiteCapabilityDiscovery:
    """Ask an authenticated chatbot webpage for a candidate, then acquire it."""

    def __init__(self, provider, lifecycle: CapabilityLifecycle) -> None:
        self.provider, self.lifecycle = provider, lifecycle

    async def discover(self, context: DiscoveryContext) -> CapabilityCandidate:
        prompt = self._prompt(context)
        prepare = getattr(self.provider, "prepare_conversation", None)
        if prepare is not None:
            prepare(prompt)
        await self.provider.open()
        await self.provider.verify_page()
        await self.provider.start_conversation()
        await self.provider.send_prompt(prompt)
        await self.provider.wait_for_response()
        return self._parse(await self.provider.extract_response(), context)

    async def discover_and_acquire(self, context: DiscoveryContext) -> CapabilityRecord:
        candidate = await self.discover(context)
        return await self.lifecycle.acquire(candidate)

    @staticmethod
    def _prompt(context: DiscoveryContext) -> str:
        schema = {
            "capability_id": context.capability_id,
            "required_tools": sorted(context.required_tools),
            "required_permissions": sorted(context.required_permissions),
            "trusted_builders": list(context.trusted_builders),
        }
        return (
            "Research a safe local solution for this computer automation capability. "
            "Return exactly one JSON object with candidate metadata only. Do not return "
            "code, shell commands, credentials, package installation commands, or a new "
            "builder. The runtime will select the executable implementation from its "
            "trusted builder catalog. The source must be a verifiable project or "
            "runtime-owned catalog entry.\n"
            f"GOAL={context.goal}\nRUNTIME_SCHEMA={json.dumps(schema, sort_keys=True)}\n"
            "JSON_FIELDS=version,tool_id,name,description,source,builder_key,"
            "health_check_key,input_schema,output_schema,risk"
        )

    def _parse(self, response: str, context: DiscoveryContext) -> CapabilityCandidate:
        try:
            data: dict[str, Any] = json.loads(response)
            if not isinstance(data, dict):
                raise TypeError("response must be an object")
            required = {"version", "tool_id", "name", "description", "source",
                        "builder_key", "health_check_key", "input_schema",
                        "output_schema", "risk"}
            if set(data) < required:
                raise ValueError("response omitted required candidate fields")
            builder_key = str(data["builder_key"])
            if builder_key not in self.lifecycle.builders:
                raise ValueError("response selected an unregistered builder")
            tool_id = str(data["tool_id"])
            if tool_id not in context.required_tools:
                raise ValueError("response changed the required tool identity")
            permissions = context.required_permissions
            return CapabilityCandidate(
                capability_id=context.capability_id,
                version=str(data["version"]),
                tool_id=tool_id,
                name=str(data["name"]),
                description=str(data["description"]),
                required_permissions=permissions,
                risk=RiskLevel(str(data["risk"])),
                input_schema=tuple(str(item) for item in data["input_schema"]),
                output_schema=str(data["output_schema"]),
                source=str(data["source"]),
                builder_key=builder_key,
                health_check_key=str(data["health_check_key"]),
                metadata={"goal": context.goal},
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise CapabilityDiscoveryError("Website returned invalid capability metadata") from error


class AutomaticCapabilityService:
    """Connect capability-gap assessment, website research, and promotion."""

    def __init__(self, broker, discovery: WebsiteCapabilityDiscovery) -> None:
        self.broker, self.discovery = broker, discovery

    async def ensure(self, goal: str) -> CapabilityRecord | None:
        assessment = self.broker.assess(goal)
        if assessment.status.value != "discovery_required":
            return None
        context = DiscoveryContext(
            goal=goal,
            capability_id=next(iter(assessment.required_tools)),
            required_tools=frozenset(assessment.required_tools),
            required_permissions=frozenset({"filesystem.read", "filesystem.write"})
            if assessment.domain == "video_editing" else frozenset(),
            trusted_builders=tuple(sorted(self.discovery.lifecycle.builders)),
        )
        candidate = await self.discovery.discover(context)
        record = await self.discovery.lifecycle.acquire(candidate)
        if record.status is not CapabilityStatus.VALIDATED:
            return record
        return await self.discovery.lifecycle.promote(candidate)
