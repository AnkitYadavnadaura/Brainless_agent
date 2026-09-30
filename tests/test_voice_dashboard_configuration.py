import asyncio
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from app.dashboard.service import (
    DashboardRuntime,
    DashboardService,
    RuntimeCommandGateway,
)
from app.voice.controller import VoiceControlPlane

from tests.test_voice import runtime


def test_dashboard_configures_and_controls_voice_without_exposing_key(tmp_path):
    async def scenario():
        service_parts = runtime(tmp_path)
        original, transport, missions, events, manager, actions, operator = (
            service_parts
        )
        created = []

        def factory(config):
            created.append(config)
            original.config = config
            return original

        voice = VoiceControlPlane(factory)
        dashboard_runtime = DashboardRuntime(
            missions, events, operator, manager, actions, voice=voice
        )
        gateway = RuntimeCommandGateway(dashboard_runtime, "dashboard-token-secure")
        api_key = "assemblyai-secret-key-value"

        await gateway.execute(
            "dashboard-token-secure",
            "configure_voice",
            {
                "api_key": api_key,
                "model": "universal-3-5-pro",
                "language": "en",
                "min_confidence": 0.8,
                "mode": "voice_session",
                "collect_tasks": False,
                "task_pause_seconds": 2.5,
            },
        )
        snapshot = DashboardService(dashboard_runtime).snapshot()
        serialized = json.dumps(
            {
                "snapshot": snapshot,
                "events": [event.detail for event in events.replay()],
            }
        )
        assert snapshot["voice"]["configured"] is True
        assert api_key not in serialized
        assert created[0].api_key == api_key
        assert created[0].min_confidence == 0.8
        assert created[0].mode.value == "voice_session"
        assert created[0].collect_tasks is False
        assert created[0].task_pause_seconds == 2.5

        await gateway.execute("dashboard-token-secure", "start_voice", {})
        assert transport.connected and voice.health_check()
        await gateway.execute("dashboard-token-secure", "stop_voice", {})
        assert not transport.connected

    asyncio.run(scenario())


def test_dashboard_voice_configuration_is_validated(tmp_path):
    service, _, missions, events, manager, actions, operator = runtime(tmp_path)
    voice = VoiceControlPlane(lambda config: service)
    gateway = RuntimeCommandGateway(
        DashboardRuntime(missions, events, operator, manager, actions, voice=voice),
        "dashboard-token-secure",
    )

    with pytest.raises(ValueError, match="length"):
        asyncio.run(
            gateway.execute(
                "dashboard-token-secure",
                "configure_voice",
                {
                    "api_key": "short",
                },
            )
        )
    assert events.replay() == ()


def test_dashboard_rejects_non_finite_voice_confidence(tmp_path):
    service, _, missions, events, manager, actions, operator = runtime(tmp_path)
    voice = VoiceControlPlane(lambda config: service)
    gateway = RuntimeCommandGateway(
        DashboardRuntime(missions, events, operator, manager, actions, voice=voice),
        "dashboard-token-secure",
    )
    with pytest.raises(ValueError, match="thresholds"):
        asyncio.run(
            gateway.execute(
                "dashboard-token-secure",
                "configure_voice",
                {"api_key": "assembly-key-long-enough", "min_confidence": float("nan")},
            )
        )


@pytest.mark.parametrize("settings", [
    {"collect_tasks": "false"}, {"collect_tasks": 1}, {"collect_tasks": None},
    {"task_pause_seconds": True}, {"task_pause_seconds": 0},
    {"task_pause_seconds": 31}, {"task_pause_seconds": float("nan")},
    {"task_pause_seconds": float("inf")}, {"task_pause_seconds": "quickly"},
])
def test_dashboard_rejects_invalid_task_collection_configuration(tmp_path, settings):
    service, _, missions, events, manager, actions, operator = runtime(tmp_path)
    installed = []
    voice = VoiceControlPlane(lambda config: installed.append(config) or service)
    gateway = RuntimeCommandGateway(
        DashboardRuntime(missions, events, operator, manager, actions, voice=voice),
        "dashboard-token-secure",
    )

    with pytest.raises(ValueError, match="collection|numeric"):
        asyncio.run(gateway.execute(
            "dashboard-token-secure", "configure_voice",
            {"api_key": "assembly-key-long-enough", **settings},
        ))

    assert not installed


def test_task_collection_defaults_are_enabled_in_control_plane(tmp_path):
    service, *_ = runtime(tmp_path)
    installed = []
    voice = VoiceControlPlane(lambda config: installed.append(config) or service)
    assert voice.snapshot()["request_collection"] == {
        "active": False, "awaiting_finish": False, "part_count": 0}

    voice.configure("assembly-key-long-enough")

    assert installed[0].collect_tasks is True
    assert installed[0].task_pause_seconds == 1.5


def test_dashboard_keeps_collection_session_alive_and_renders_completion_question():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is needed for dashboard interaction validation")
    source = Path("app/dashboard/static/app.js").read_text(encoding="utf-8")
    harness = r'''
const assert = require('node:assert/strict');
const nodes = new Map(), documentEvents = new Map(), windowEvents = new Map();
function element(selector) {
  if (!nodes.has(selector)) nodes.set(selector, {
    handlers: new Map(), classList: {toggle() {}}, dataset: {},
    addEventListener(name, handler) { this.handlers.set(name, handler); },
    setAttribute() {}, showModal() {},
  });
  return nodes.get(selector);
}
global.location = {hash: '#voice'};
global.sessionStorage = {getItem() { return ''; }};
global.document = {
  querySelector: element, querySelectorAll() { return []; },
  addEventListener(name, handler) { documentEvents.set(name, handler); },
};
global.window = {addEventListener(name, handler) { windowEvents.set(name, handler); }};
'''
    checks = r'''
state.data = {voice: {
  configured: true, status: 'listening', connection: 'connected', mode: 'push_to_talk',
  collect_tasks: true, assistant_question: 'Anything else?',
  request_collection: {active: true, awaiting_finish: true, part_count: 2}, history: [],
}, overview: {active_missions: 0, pending_approvals: 0}};
const markup = voice();
assert.ok(markup.includes('Anything else?'));
assert.ok(markup.includes('2 spoken parts collected'));
assert.ok(markup.includes('Planning starts after you finish your request'));
assert.ok(markup.includes('until Stop voice or the session timeout'));
assert.ok(!markup.includes('Every finalized transcript'));
render();
assert.equal(element('#voiceStart').textContent, 'Listening');
assert.equal(element('#voiceStart').disabled, true);
const commands = [];
command = async name => commands.push(name);
element('#voiceStart').handlers.get('click')();
documentEvents.get('pointerup')?.({});
documentEvents.get('pointercancel')?.({});
assert.deepEqual(commands, ['start_voice']);
element('#voiceStop').handlers.get('click')();
assert.deepEqual(commands, ['start_voice', 'stop_voice']);
'''
    script = harness + "\neval(" + json.dumps(source + "\n" + checks) + ");"
    result = subprocess.run([node], input=script, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
