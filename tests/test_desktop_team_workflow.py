import asyncio
import hashlib
import json
from types import SimpleNamespace

import pytest

from app.agents.manager import AgentManager
from app.autonomy.desktop_team_controller import WindowsDesktopTeamController, TOOL_SCHEMAS
from app.autonomy.desktop_team_workflow import run_desktop_team
from app.safety.permissions import ApprovalMode, PermissionPolicy


TARGET = hashlib.sha256(b"10:edit").hexdigest()[:16]


class Desktop:
    def __init__(self):
        self.active = 10
        self.text = ""
        self.clipboard = "private clipboard"
        self.calls = []
        self.focused = False
        self.title = "Untitled - Notepad"
        self.identity_value = (1, "Notepad")

    def windows(self):
        return {10: self.title, 20: "ChatGPT - Browser"}

    def identity(self, hwnd):
        return self.identity_value if hwnd == 10 else (2, "Browser")

    def foreground(self):
        return self.active

    def focus(self, hwnd):
        self.calls.append(("focus", hwnd))
        self.active = hwnd

    def point_in_window(self, hwnd, x, y):
        return self.active == hwnd == 10 and (x, y) == (50, 25)

    def click(self, x, y):
        assert self.active == 10
        self.focused = True
        self.calls.append(("click", x, y))

    def clipboard_read(self):
        return self.clipboard

    def clipboard_write(self, value):
        self.clipboard = value

    def hotkey(self, *keys):
        assert self.active == 10
        self.calls.append(("key", keys))
        if keys == ("ctrl", "v"):
            self.text += self.clipboard

    def snapshot(self, hwnd):
        assert hwnd == 10
        return [{"runtime_id": "edit", "name": "Text editor", "role": "ControlType.Edit",
                 "text": self.text, "enabled": True, "focused": self.focused and self.active == 10,
                 "bounds": [0, 0, 100, 50]}]


class Team:
    def __init__(self, desktop, answers):
        self.desktop, self.answers = desktop, iter(answers)
        self.prompts = []
        self.contexts = []

    async def open(self):
        pass

    def set_checkpoint_context(self, context):
        self.contexts.append(context)

    async def send_prompt(self, prompt):
        self.prompts.append(prompt)
        # Every model turn uses its browser. Input must return to pinned Notepad.
        self.desktop.active = 20

    async def wait_for_response(self):
        pass

    async def extract_response(self):
        result = next(self.answers)
        if callable(result):
            result = result()
        return result if isinstance(result, str) else json.dumps(result)


def action(text="Hello"):
    return {"status": "action", "tool": "team.desktop.type", "arguments": {"target_id": TARGET, "text": text},
            "reason": "Enter the user requested note", "expected_text": [text]}


def complete(text="Hello"):
    return {"status": "completed", "summary": "The note is visible in Notepad", "evidence": [text]}


def verify(text="Hello"):
    return {"verified": True, "reason": "The exact note is present in the editor", "evidence": [text]}


def setup(answers, policy=None):
    desktop = Desktop()
    controller = WindowsDesktopTeamController(desktop, snapshot_reader=desktop.snapshot)
    app = SimpleNamespace(agent_manager=AgentManager(policy=policy))
    return desktop, controller, app, Team(desktop, answers)


@pytest.mark.asyncio
async def test_team_executes_grounded_note_after_browser_focus_change_and_verifies(tmp_path):
    desktop, controller, app, team = setup([action(), complete(), verify()])
    approvals = []
    result = await run_desktop_team(team, app, "Write Hello visibly in Notepad", tmp_path,
        max_actions=1, controller=controller, approval_handler=lambda request: approvals.append(request) or True,
        progress=lambda _: None)
    assert result["status"] == "completed" and result["action_count"] == 1
    assert desktop.text == "Hello" and desktop.clipboard == "private clipboard"
    assert len(approvals) == 1 and approvals[0].action_type == "team.desktop.type"
    assert len(team.prompts) == 3 and "Independently verify" in team.prompts[-1]
    record = json.loads(open(result["report"], encoding="utf-8").read())
    assert record["in_flight"] is None and record["actions"][0]["effect_verified"] is True
    assert not any(app.agent_manager.tools.contains(tool) for tool in TOOL_SCHEMAS)


@pytest.mark.asyncio
async def test_mutation_without_approval_is_blocked_without_click_or_input(tmp_path):
    desktop, controller, app, team = setup([action()])
    result = await run_desktop_team(team, app, "Write Hello", tmp_path, controller=controller, progress=lambda _: None)
    assert result["status"] == "blocked" and "approval" in result["summary"].lower()
    assert desktop.calls == [] and desktop.text == ""


@pytest.mark.asyncio
async def test_existing_permission_denial_is_not_bypassed_by_approval(tmp_path):
    desktop, controller, app, team = setup([action()], PermissionPolicy({"keyboard.write": ApprovalMode.DENY}))
    result = await run_desktop_team(team, app, "Write Hello", tmp_path, controller=controller,
        approval_handler=lambda _: True, progress=lambda _: None)
    assert result["status"] == "blocked" and "POLICY_DENIED" in result["summary"]
    assert not desktop.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    {"status": "action", "tool": "process.execute", "arguments": {"command": "whoami"}, "reason": "Do it", "expected_text": ["yes"]},
    {**action(), "arguments": {"target_id": "invented", "text": "Hello"}},
    complete("Imaginary complete output"),
    '{"status":"completed","status":"blocked","reason":"bad"}',
])
async def test_unsafe_or_ungrounded_output_is_rejected_before_execution(tmp_path, bad):
    desktop, controller, app, team = setup([bad])
    result = await run_desktop_team(team, app, "Task", tmp_path, controller=controller,
        max_failures=1, approval_handler=lambda _: True, progress=lambda _: None)
    assert result["status"] == "blocked" and result["action_count"] == 0
    assert not desktop.calls


@pytest.mark.asyncio
async def test_team_can_repair_a_rejected_proposal_from_new_observation(tmp_path):
    desktop, controller, app, team = setup(["not JSON", action(), complete(), verify()])
    result = await run_desktop_team(team, app, "Write Hello", tmp_path, controller=controller,
        approval_handler=lambda _: True, progress=lambda _: None)
    assert result["status"] == "completed"
    assert '"executed": false' in team.prompts[1]
    assert desktop.text == "Hello"


@pytest.mark.asyncio
async def test_rejects_target_that_changed_during_peer_reasoning(tmp_path):
    desktop, controller, app, team = setup([])
    def changed():
        desktop.text = "User typed something while the team was reasoning"
        return action()
    team.answers = iter([changed])
    result = await run_desktop_team(team, app, "Write Hello", tmp_path, controller=controller,
        max_failures=1, approval_handler=lambda _: True, progress=lambda _: None)
    assert result["status"] == "blocked" and not desktop.calls
    assert "Hello" not in desktop.text


@pytest.mark.asyncio
async def test_false_completion_verification_cannot_mark_work_complete(tmp_path):
    desktop, controller, app, team = setup([complete("Notepad"), {"verified": False, "reason": "Note absent", "evidence": []}])
    result = await run_desktop_team(team, app, "Write Hello", tmp_path, controller=controller,
        max_failures=1, progress=lambda _: None)
    assert result["status"] == "blocked" and not desktop.calls


@pytest.mark.asyncio
async def test_prior_unknown_action_is_context_only_and_never_replayed(tmp_path):
    task = "Write Hello"
    key = hashlib.sha256(task.encode()).hexdigest()[:20]
    checkpoint = tmp_path / "data/browser-team/desktop" / f"{key}.json"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text(json.dumps({"status": "running", "in_flight": action()}), encoding="utf-8")
    desktop, controller, app, team = setup([{"status": "blocked", "reason": "Inspect prior outcome first"}])
    result = await run_desktop_team(team, app, task, tmp_path, controller=controller, progress=lambda _: None)
    assert result["status"] == "blocked" and not desktop.calls
    assert '"in_flight"' in team.prompts[0]


@pytest.mark.asyncio
async def test_action_budget_stops_additional_side_effects(tmp_path):
    desktop, controller, app, team = setup([action(), action("Second")])
    result = await run_desktop_team(team, app, "Write two notes", tmp_path, controller=controller,
        max_actions=1, approval_handler=lambda _: True, progress=lambda _: None)
    assert result["status"] == "blocked" and "action budget" in result["summary"]
    assert desktop.text == "Hello"


@pytest.mark.asyncio
async def test_team_timeout_is_saved_as_blocked(tmp_path):
    desktop, controller, app, team = setup([])
    async def slow():
        await asyncio.sleep(1)
    team.wait_for_response = slow
    result = await run_desktop_team(team, app, "Task", tmp_path, controller=controller,
        max_minutes=0.001, progress=lambda _: None)
    assert result["status"] == "blocked" and "time budget" in result["summary"]
    assert not desktop.calls


@pytest.mark.asyncio
async def test_keyboard_requires_actual_target_focus(tmp_path):
    desktop, controller, app, team = setup([action()])
    desktop.click = lambda x, y: desktop.calls.append(("click", x, y))
    result = await run_desktop_team(team, app, "Write Hello", tmp_path, controller=controller,
        max_failures=1, approval_handler=lambda _: True, progress=lambda _: None)
    assert result["status"] == "blocked" and desktop.text == ""
    assert not any(call[0] == "key" for call in desktop.calls)


@pytest.mark.asyncio
async def test_shell_context_is_not_a_text_execution_channel(tmp_path):
    desktop, controller, app, team = setup([action()])
    desktop.title = "Windows PowerShell"
    result = await run_desktop_team(team, app, "Write Hello", tmp_path, controller=controller,
        max_failures=1, approval_handler=lambda _: True, progress=lambda _: None)
    assert result["status"] == "blocked" and not desktop.calls
