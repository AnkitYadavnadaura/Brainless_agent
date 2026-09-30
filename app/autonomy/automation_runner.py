"""Sequential execution for the declarative automation catalog."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.autonomy.automation_catalog import AutomationCatalog, AutomationDefinition
from app.safety.permissions import Permission


@dataclass(frozen=True, slots=True)
class AutomationRunResult:
    automation_id: str
    name: str
    tool_id: str
    status: str
    output: Any = None
    error: str | None = None


class AutomationRunner:
    """Run catalog entries one at a time through the normal agent boundary.

    The runner never invokes handlers directly. Missing tools, missing inputs,
    and external dependencies are reported explicitly so a batch can finish
    with an actionable status report instead of a false success.
    """

    def __init__(self, manager, catalog: AutomationCatalog | None = None) -> None:
        self.manager = manager
        self.catalog = catalog or AutomationCatalog()

    async def run_one(
        self,
        parent_agent_id: str,
        automation: AutomationDefinition,
        arguments: Mapping[str, Any] | None = None,
    ) -> AutomationRunResult:
        tool_id = next(iter(automation.tools))
        if not self.manager.tools.contains(tool_id):
            return AutomationRunResult(
                automation.automation_id, automation.name, tool_id, "blocked",
                error=f"Tool is not registered: {tool_id}",
            )

        tool = self.manager.tools.get(tool_id)
        supplied = dict(arguments or {})
        missing = sorted(set(tool.input_schema) - set(supplied))
        if missing:
            return AutomationRunResult(
                automation.automation_id, automation.name, tool_id, "needs_input",
                error=f"Missing arguments: {', '.join(missing)}",
            )

        permissions = set(tool.required_permissions)
        agent = self.manager.create_agent(
            parent_agent_id,
            f"Automation {automation.automation_id}",
            "catalog-automation",
            automation.objective,
            task=automation.automation_id,
            permissions=permissions,
            tools={tool_id},
            context={"automation_id": automation.automation_id},
        )
        try:
            async def execute(child, manager):
                return await manager.execute_tool(child.agent_id, tool_id, supplied)

            output = await self.manager.start_agent(
                parent_agent_id,
                agent.agent_id,
                execute,
            )
            return AutomationRunResult(
                automation.automation_id, automation.name, tool_id, "completed", output=output,
            )
        except Exception as error:
            return AutomationRunResult(
                automation.automation_id, automation.name, tool_id, "failed",
                error=f"{type(error).__name__}: {error}",
            )

    async def run_all(
        self,
        parent_agent_id: str,
        arguments_by_id: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> tuple[AutomationRunResult, ...]:
        arguments_by_id = arguments_by_id or {}
        results: list[AutomationRunResult] = []
        for automation in self.catalog.all():
            results.append(await self.run_one(
                parent_agent_id, automation, arguments_by_id.get(automation.automation_id),
            ))
        return tuple(results)
def all_permissions() -> set[str]:
    """Permissions suitable for the catalog parent agent."""
    return {permission.value for permission in Permission}
