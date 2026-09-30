"""Two-prompt agent selection and safe declarative creation workflow."""
from __future__ import annotations

from dataclasses import dataclass
import asyncio
import json
import ast
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, TYPE_CHECKING

from app.agents.building_blocks import AgentDefinition
from app.agents.models import Agent
from app.safety.permissions import Permission

if TYPE_CHECKING:
    from app.autonomy.models import TaskRequirements


class AgentPlanningError(ValueError):
    """A provider returned an invalid or unauthorized agent plan."""


@dataclass(frozen=True, slots=True)
class AgentSelection:
    decision: str
    agent_id: str | None


class AgentPlanningWorkflow:
    """Ask for selection first and creation only when deterministic reuse fails.

    Provider output is untrusted. The runtime independently checks reuse and
    converts a validated definition into a fixed, data-only Python artifact;
    arbitrary provider-supplied Python is never executed.
    """

    def __init__(self, provider, manager, registry, root: Path) -> None:
        self.provider, self.manager, self.registry, self.root = provider, manager, registry, root
        self._provider_lock = asyncio.Lock()
        prompt_root = root / "prompts/agents"
        self.prompt1 = (prompt_root / "prompt1_select_agent.txt").read_text(encoding="utf-8")
        self.prompt2 = (prompt_root / "prompt2_create_agent.txt").read_text(encoding="utf-8")

    async def select_or_create(self, parent_agent_id: str, task_id: str, task: str,
                               requirements: "TaskRequirements") -> tuple[Agent, bool]:
        selection = await self._select(task, requirements)
        eligible = self.registry.find(requirements)
        if selection.decision == "reuse" and eligible is not None and eligible.agent_id == selection.agent_id:
            self.manager.assign_task(parent_agent_id, eligible.agent_id, task, task_id=task_id)
            return eligible, False

        # A model cannot force creation when the authoritative registry already
        # has a suitable agent; deterministic reuse remains the least-privilege path.
        if eligible is not None:
            self.manager.assign_task(parent_agent_id, eligible.agent_id, task, task_id=task_id)
            return eligible, False
        definition = await self._define(parent_agent_id, task, requirements)
        output = self._run_definition_artifact(task_id, definition)
        agent = AgentDefinition.from_mapping(output).create(self.manager, parent_agent_id)
        self.manager.assign_task(parent_agent_id, agent.agent_id, task, task_id=task_id)
        self.registry.register(agent, requirements.capabilities)
        return agent, True

    async def _select(self, task: str, requirements: "TaskRequirements") -> AgentSelection:
        inventory = [{"agent_id": item.agent_id, "name": item.name, "role": item.role,
                      "status": item.status.value, "permissions": sorted(item.permissions),
                      "tools": sorted(item.available_tools),
                      "capabilities": sorted(self._capabilities_for(item.agent_id))}
                     for item in self.manager.list_agents() if item.parent_agent_id is not None]
        payload = {"task": task, "required_capabilities": sorted(requirements.capabilities),
                   "required_permissions": sorted(requirements.permissions),
                   "required_tools": sorted(requirements.tools), "agents": inventory}
        data = self._object(await self._ask(self.prompt1 + "\nRUNTIME_DATA=" + json.dumps(payload, sort_keys=True)))
        decision = str(data.get("decision", ""))
        agent_id = data.get("agent_id")
        if decision not in {"reuse", "create"} or (agent_id is not None and not isinstance(agent_id, str)):
            raise AgentPlanningError("Prompt 1 returned an invalid selection")
        returned = (frozenset(data.get("required_capabilities", ())),
                    frozenset(data.get("required_permissions", ())),
                    frozenset(data.get("required_tools", ())))
        expected = (requirements.capabilities, requirements.permissions, requirements.tools)
        if returned != expected:
            raise AgentPlanningError("Prompt 1 changed the runtime-required authority")
        return AgentSelection(decision, agent_id)

    async def _define(self, parent_agent_id: str, task: str,
                      requirements: "TaskRequirements") -> AgentDefinition:
        parent = self.manager.get_agent(parent_agent_id)
        parent_tools = {tool_id: {"tool_id": tool_id, "description": tool.description,
                                 "permissions": sorted(tool.required_permissions), "risk": tool.risk.value}
                        for tool_id in self.manager.tools.tool_ids
                        for tool in (self.manager.tools.get(tool_id),)
                        if tool.required_permissions.issubset(parent.permissions)}
        functions = [parent_tools[tool] for tool in sorted(requirements.tools) if tool in parent_tools]
        payload = {"task": task, "required_capabilities": sorted(requirements.capabilities),
                   "required_permissions": sorted(requirements.permissions),
                   "required_tools": sorted(requirements.tools), "registered_functions": functions}
        data = self._object(await self._ask(self.prompt2 + "\nRUNTIME_DATA=" + json.dumps(payload, sort_keys=True)))
        value = data.get("agent_definition")
        if not isinstance(value, dict) or not isinstance(data.get("python_code"), str):
            raise AgentPlanningError("Prompt 2 omitted agent_definition or python_code")
        definition = AgentDefinition.from_mapping(value)
        # Automatically grant any runtime-required permissions/tools that the
        # planner omitted but the runtime deems necessary for the task. This
        # is conservative: only add missing items requested by `requirements`.
        missing_perms = set(requirements.permissions) - set(definition.permissions)
        missing_tools = set(requirements.tools) - set(definition.tools)
        if missing_perms or missing_tools:
            merged_permissions = frozenset(set(definition.permissions) | set(requirements.permissions))
            merged_tools = frozenset(set(definition.tools) | set(requirements.tools))
            definition = AgentDefinition(definition.name, definition.role, definition.objective,
                                         definition.task, merged_permissions, merged_tools,
                                         definition.subscriptions, definition.context,
                                         definition.resource_limits, definition.allowed_applications,
                                         definition.allowed_directories, definition.risk_policy)
        # Heuristic: if the task mentions YouTube, ensure a YouTube playback
        # tool is available so the agent can perform playback autonomously.
        if any(term in (task or "").lower() for term in ("youtube", "youtube music")) and "youtube.play" not in definition.tools:
            merged_tools = frozenset(set(definition.tools) | {"youtube.play"})
            merged_permissions = frozenset(set(definition.permissions) | {Permission.BROWSER_NAVIGATE.value})
            definition = AgentDefinition(definition.name, definition.role, definition.objective,
                                         definition.task, merged_permissions, merged_tools,
                                         definition.subscriptions, definition.context,
                                         definition.resource_limits, definition.allowed_applications,
                                         definition.allowed_directories, definition.risk_policy)
        return definition

    async def _ask(self, prompt: str) -> str:
        async with self._provider_lock:
            prepare = getattr(self.provider, "prepare_conversation", None)
            if prepare is not None:
                prepare(prompt)
            await self.provider.open()
            await self.provider.verify_page()
            await self.provider.start_conversation()
            await self.provider.send_prompt(prompt)
            await self.provider.wait_for_response()
            remember = getattr(self.provider, "remember_conversation", None)
            if remember is not None:
                remember()
            try:
                return await self.provider.extract_response()
            except Exception as error:
                raise AgentPlanningError(
                    "Website planning response could not be extracted. "
                    "Check the visible ChatGPT tab for login, CAPTCHA, generation "
                    f"failure, or a changed page layout: {error}"
                ) from error

    def _capabilities_for(self, agent_id: str) -> frozenset[str]:
        try:
            return self.registry.capabilities_for(agent_id)
        except KeyError:
            return frozenset()

    def _run_definition_artifact(self, task_id: str, definition: AgentDefinition) -> dict[str, Any]:
        value = {"name": definition.name, "role": definition.role, "objective": definition.objective,
                 "task": definition.task, "permissions": sorted(definition.permissions),
                 "tools": sorted(definition.tools), "subscriptions": sorted(definition.subscriptions),
                 "context": dict(definition.context), "resource_limits": dict(definition.resource_limits),
                 "allowed_applications": sorted(definition.allowed_applications),
                 "allowed_directories": sorted(definition.allowed_directories), "risk_policy": definition.risk_policy}
        directory = self.root / "data/generated-agents"
        directory.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(character for character in task_id if character.isalnum() or character in "-_")[:100]
        path = directory / f"{safe_name or 'agent'}.py"
        # Generate this fixed program ourselves. Provider-supplied source is not
        # used, so imports/calls cannot smuggle authority around AgentManager.
        path.write_text("import json\nDEFINITION = " + repr(value) + "\nprint(json.dumps(DEFINITION))\n", encoding="utf-8")
        result = subprocess.run([sys.executable, "-I", str(path)], check=True, capture_output=True,
                                text=True, timeout=5, cwd=directory)
        return self._object(result.stdout)

    @staticmethod
    def _object(response: str) -> dict[str, Any]:
        text = (response or "").strip()
        if not text:
            raise AgentPlanningError("Provider response was empty")
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL)
        start = text.find("{")
        if start == -1:
            raise AgentPlanningError("Provider response was not exact JSON")
        depth = 0
        in_string = False
        escaped = False
        end = None
        for index in range(start, len(text)):
            character = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    in_string = False
                continue
            if character == '"':
                in_string = True
            elif character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            candidate = text[start:]
        else:
            candidate = text[start:end]
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            # Some providers return Python-style dicts using single quotes or
            # other non-JSON quoting. As a robust fallback, try ast.literal_eval
            # which safely evaluates Python literals (dicts, lists, strings).
            try:
                value = ast.literal_eval(candidate)
            except (ValueError, SyntaxError) as error:
                # As a last-resort, try to extract only the agent_definition
                # object from the full response text. Many providers return a
                # valid `agent_definition` but embed messy `python_code` that
                # breaks full-JSON parsing. Extracting the `agent_definition`
                # lets the runtime continue (python_code is advisory).
                m = re.search(r'"agent_definition"\s*:\s*\{', text)
                if m:
                    start2 = text.find('{', m.start())
                    depth2 = 0
                    in_string2 = False
                    escaped2 = False
                    end2 = None
                    for i in range(start2, len(text)):
                        ch = text[i]
                        if in_string2:
                            if escaped2:
                                escaped2 = False
                            elif ch == "\\":
                                escaped2 = True
                            elif ch == '"':
                                in_string2 = False
                            continue
                        if ch == '"':
                            in_string2 = True
                        elif ch == '{':
                            depth2 += 1
                        elif ch == '}':
                            depth2 -= 1
                            if depth2 == 0:
                                end2 = i + 1
                                break
                    if end2 is not None:
                        candidate2 = text[start2:end2]
                        try:
                            def_obj = json.loads(candidate2)
                        except Exception:
                            def_obj = None
                        if isinstance(def_obj, dict):
                            return {"agent_definition": def_obj, "python_code": ""}
                raise AgentPlanningError("Provider response was not exact JSON") from error
        if not isinstance(value, dict):
            raise AgentPlanningError("Provider response must be a JSON object")
        return value

        # NOTE: the code below is kept for historical context; unreachable
        # because of the return above. The improved fallback extraction is
        # implemented in the outer exception handler below.
