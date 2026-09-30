"""Runtime consent, durable capability scope, and suspended action lifecycle."""
import asyncio

import pytest

from app.agents.manager import AgentManager
from app.agents.models import AgentStatus
from app.agents.tools import RiskLevel, ToolRegistry, ToolSpec
from app.autonomy.approvals import ApprovalRequest, ApprovalStatus, ApprovalStore, ApprovalSystem
from app.autonomy.executor import ActionRuntime
from app.autonomy.governor import MissionContract
from app.autonomy.mode_policy import ModePolicy
from app.autonomy.models import ComputerAction, ComputerState
from app.autonomy.operator import AutonomyMode
from app.safety.permissions import ApprovalMode, ApprovalRequired, PermissionGrantStore, PermissionPolicy


class Computer:
    async def observe(self):
        return ComputerState()


def runtime_for(tmp_path, *, policy=None, risk=RiskLevel.MEDIUM, destructive=False,
                supervised=False, permissions=frozenset({"browser.navigate", "browser.read"})):
    invocations = []
    registry = ToolRegistry()
    registry.register(ToolSpec("browser.visit", "Visit browser page", "Visit", permissions, risk,
        lambda arguments: invocations.append(arguments) or "opened", ("url",), destructive=destructive))
    manager = AgentManager(registry, policy=policy or PermissionPolicy(
        grant_store=PermissionGrantStore(tmp_path / "grants.json"), require_first_use=True))
    root = manager.create_root("root", "root", "Browse", set(permissions))
    child = manager.create_agent(root.agent_id, "browser", "browser", "Browse", task="Browse",
        permissions=set(permissions), tools={"browser.visit"}, task_id="mission:objective:1")
    child.status = AgentStatus.RUNNING
    approvals = ApprovalSystem(ApprovalStore(tmp_path / "approvals.json"), manager, timeout_seconds=.2)
    runtime = ActionRuntime(manager, Computer(), approval_handler=approvals.request,
        mode_policy=ModePolicy(AutonomyMode.SUPERVISED if supervised else AutonomyMode.AUTONOMOUS))
    action = ComputerAction("browser.visit", {"url": "https://example.test"}, child.agent_id,
        child.current_task_id, "Open the requested page", sorted(permissions)[0])
    return runtime, approvals, action, invocations


def test_confirm_once_resumes_all_permissions_and_remembers_across_restart(tmp_path):
    async def scenario():
        runtime, approvals, action, invocations = runtime_for(tmp_path, supervised=True)
        notifications, resolved = [], []

        def confirm(request):
            notifications.append(request)
            assert approvals.pending() == (request,)
            approvals.decide(request.approval_id, ApprovalStatus.APPROVED, "voice", remember=True)

        approvals.on_requested, approvals.on_resolved = confirm, resolved.append
        result = await runtime.perform(action)
        assert result.success and runtime.result_for(action.action_id) is result
        assert runtime.result_for("unknown-action") is None
        assert len(notifications) == len(invocations) == 1
        request = notifications[0]
        assert request.mission_id == "mission"
        assert request.permissions == ("browser.navigate", "browser.read")
        assert request.can_remember and resolved[0].remembered
        assert approvals.pending() == ()

        # A new manager and child identity use only the exact saved tool permissions.
        restarted, approvals2, action2, invocations2 = runtime_for(tmp_path, supervised=True)
        approvals2.on_requested = lambda _: pytest.fail("Saved permission should not prompt again")
        assert (await restarted.perform(action2)).success
        assert len(invocations2) == 1
        with pytest.raises(ApprovalRequired):
            restarted.manager.policy.check(action2.agent_id, "browser.navigate", tool="browser.other")
        with pytest.raises(ApprovalRequired):
            restarted.manager.policy.check(action2.agent_id, "browser.type", tool="browser.visit")
    asyncio.run(scenario())


def test_policy_and_mode_gate_share_one_action_decision_without_remembering(tmp_path):
    async def scenario():
        runtime, approvals, action, invocations = runtime_for(tmp_path, supervised=True)
        requested = []
        def confirm(request):
            requested.append(request)
            approvals.decide(request.approval_id, ApprovalStatus.APPROVED, "voice")
        approvals.on_requested = confirm
        assert (await runtime.perform(action)).success
        assert len(requested) == len(invocations) == 1
        for permission in requested[0].permissions:
            with pytest.raises(ApprovalRequired):
                runtime.manager.policy.check(action.agent_id, permission, tool=action.action_type)
        assert not (tmp_path / "grants.json").exists()
    asyncio.run(scenario())


@pytest.mark.parametrize("saved", [False, True])
def test_hard_deny_on_any_required_permission_prevents_prompt_and_execution(tmp_path, saved):
    async def scenario():
        grants = PermissionGrantStore(tmp_path / "grants.json")
        if saved:
            grants.grant("browser.visit", ("browser.navigate", "browser.read"), "human")
        policy = PermissionPolicy({"browser.read": ApprovalMode.DENY},
            grant_store=grants, require_first_use=True)
        runtime, approvals, action, invocations = runtime_for(tmp_path, policy=policy, supervised=True)
        approvals.on_requested = lambda _: pytest.fail("Hard denial cannot be overridden by a prompt")
        result = await runtime.perform(action)
        assert not result.success and "POLICY_DENIED" in result.error
        assert invocations == [] and approvals.pending() == ()
    asyncio.run(scenario())


def test_preflight_does_not_consume_preexisting_one_shot_grants(tmp_path):
    async def scenario():
        runtime, approvals, action, invocations = runtime_for(tmp_path)
        for permission in runtime.manager.tools.get(action.action_type).required_permissions:
            runtime.manager.policy.approve_once(action.agent_id, permission, tool=action.action_type)
        approvals.on_requested = lambda _: pytest.fail("The action already has one-shot consent")
        assert (await runtime.perform(action)).success
        assert len(invocations) == 1
        with pytest.raises(ApprovalRequired):
            runtime.manager.policy.check(action.agent_id, action.permission, tool=action.action_type)
    asyncio.run(scenario())


@pytest.mark.parametrize("risk,destructive,permissions", [
    (RiskLevel.HIGH, False, frozenset({"browser.navigate"})),
    (RiskLevel.MEDIUM, True, frozenset({"browser.navigate"})),
    (RiskLevel.MEDIUM, False, frozenset({"process.execute"})),
])
def test_sensitive_actions_cannot_be_remembered(tmp_path, risk, destructive, permissions):
    async def scenario():
        runtime, approvals, action, _ = runtime_for(tmp_path, risk=risk, destructive=destructive,
            permissions=permissions, supervised=True)
        confirmed = []
        def confirm(request):
            assert not request.can_remember
            confirmed.append(approvals.decide(request.approval_id, ApprovalStatus.APPROVED, "voice", remember=True))
        approvals.on_requested = confirm
        assert (await runtime.perform(action)).success
        second = ComputerAction(action.action_type, action.arguments, action.agent_id, action.task_id,
            action.reason, action.permission)
        assert (await runtime.perform(second)).success
        assert len(confirmed) == 2 and not any(item.remembered for item in confirmed)
        assert not (tmp_path / "grants.json").exists()
    asyncio.run(scenario())


def test_denial_timeout_and_cancellation_never_leave_active_permissions(tmp_path):
    async def scenario():
        runtime, approvals, action, invocations = runtime_for(tmp_path)
        approvals.on_requested = lambda request: approvals.decide(
            request.approval_id, ApprovalStatus.DENIED, "voice", remember=True)
        assert not (await runtime.perform(action)).success
        assert approvals.pending() == () and invocations == []

        approvals.on_requested = None
        timeout_action = ComputerAction(action.action_type, action.arguments, action.agent_id,
            action.task_id, action.reason, action.permission)
        assert not await approvals.request(timeout_action)
        assert approvals.store.get(timeout_action.action_id).status is ApprovalStatus.EXPIRED

        cancelled = ComputerAction(action.action_type, action.arguments, action.agent_id,
            action.task_id, action.reason, action.permission)
        waiter = asyncio.create_task(approvals.request(cancelled))
        await asyncio.sleep(0)
        assert approvals.pending()[0].approval_id == cancelled.action_id
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert approvals.pending() == ()
        assert approvals.store.get(cancelled.action_id).status is ApprovalStatus.EXPIRED
        with pytest.raises(ValueError, match="no longer pending"):
            approvals.decide(cancelled.action_id, ApprovalStatus.APPROVED, "late voice", remember=True)
        assert not (tmp_path / "grants.json").exists()
    asyncio.run(scenario())


def test_pending_request_metadata_redacts_reason_and_never_saves_arguments(tmp_path):
    async def scenario():
        runtime, approvals, action, _ = runtime_for(tmp_path)
        action = ComputerAction(action.action_type, {"url": "https://example.test/private-query"},
            action.agent_id, action.task_id, "password is private-secret", action.permission)
        waiter = asyncio.create_task(approvals.request(action))
        await asyncio.sleep(0)
        saved = (tmp_path / "approvals.json").read_text()
        assert "private-query" not in saved and "private-secret" not in saved
        assert approvals.pending()[0].reason == "[REDACTED]"
        approvals.cancel(mission_id="different-mission")
        assert len(approvals.pending()) == 1
        approvals.cancel(mission_id="mission")
        assert not await waiter and approvals.pending() == ()
    asyncio.run(scenario())


def test_restart_expires_orphaned_pending_requests(tmp_path):
    _, approvals, action, _ = runtime_for(tmp_path)
    approvals.store.put(ApprovalRequest(action.action_id, "mission", action.task_id, action.agent_id,
        action.action_type, action.reason, "medium", action.permission))
    restarted = ApprovalSystem(approvals.store, approvals.manager)
    assert restarted.pending() == ()
    assert restarted.store.get(action.action_id).status is ApprovalStatus.EXPIRED
    with pytest.raises(ValueError):
        restarted.decide(action.action_id, ApprovalStatus.APPROVED, "stale voice", remember=True)


def test_permission_grant_store_corruption_and_revoke_fail_closed(tmp_path):
    path = tmp_path / "grants.json"
    path.write_text("not json")
    grants = PermissionGrantStore(path)
    assert not grants.allows("browser.visit", "browser.navigate")
    grants.grant("browser.visit", ("browser.navigate", "browser.read"), "voice")
    grants.revoke("browser.visit", "browser.navigate")
    assert not grants.allows("browser.visit", "browser.navigate")
    assert grants.allows("browser.visit", "browser.read")
    grants.revoke("browser.visit")
    assert not grants.allows("browser.visit", "browser.read")


@pytest.mark.parametrize("mode", [AutonomyMode.PAUSED, AutonomyMode.TAKEOVER])
def test_operator_mode_change_during_observation_prevents_approved_execution(tmp_path, mode):
    async def scenario():
        runtime, approvals, action, invocations = runtime_for(tmp_path)
        approvals.on_requested = lambda request: approvals.decide(
            request.approval_id, ApprovalStatus.APPROVED, "voice")

        class PausingComputer:
            async def observe(self):
                runtime.mode_policy.mode = mode
                return ComputerState()

        runtime.controller = PausingComputer()
        result = await runtime.perform(action)
        assert not result.success and "POLICY_DENIED" in result.error
        assert runtime.audit[-1].approval_status == "approved"
        assert runtime.audit[-1].policy_decision == "mode_deny"
        assert not invocations
    asyncio.run(scenario())


def test_governor_approval_never_overrides_paused_mode(tmp_path):
    async def scenario():
        runtime, approvals, action, invocations = runtime_for(tmp_path, risk=RiskLevel.HIGH)
        runtime.governor.register(MissionContract("mission"), {action.task_id})
        runtime.mode_policy.mode = AutonomyMode.PAUSED
        approvals.on_requested = lambda _: pytest.fail("A paused runtime cannot ask to execute")
        result = await runtime.perform(action)
        assert not result.success and "POLICY_DENIED" in result.error
        assert not invocations
    asyncio.run(scenario())
