import json
from types import SimpleNamespace

import pytest

from app.browser.fleet_discovery import BrowserInstallation, BrowserInventory, BrowserProfile
from app.browser.team_cli import run_browser_team, saved_status


def inventory(root):
    browser = BrowserInstallation('browser', 'Google Chrome', 'chromium', root / 'chrome.exe', root)
    profile = BrowserProfile('profile', browser.id, 'Default', root / 'Default', 'Default')
    return BrowserInventory([browser], [profile], [])


class Member:
    def __init__(self, ident, answers):
        self.id = ident
        self.provider_name = ident
        self.prompts = []
        self.answers = iter(answers)

    async def ask(self, prompt):
        self.prompts.append(prompt)
        return next(self.answers)


class Fleet:
    def __init__(self, members):
        self.members = members
        self.windows = {'profile': 10}
        self.failures = {}
        self.closed = False
        self.started = False

    async def start(self):
        self.started = True
        return self.members

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_inventory_and_status_never_create_a_fleet_or_database(tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError('read-only command opened a browser')
    output = []
    code = await run_browser_team(['inventory', '--json'], tmp_path, progress=output.append,
        discover=lambda **_: inventory(tmp_path), fleet_factory=forbidden)
    assert code == 0
    data = json.loads(output[0])
    assert (data['browser_count'], data['profile_count'], data['participant_count']) == (1, 1, 2)
    await run_browser_team(['status'], tmp_path, discover=forbidden, fleet_factory=forbidden,
                           progress=output.append)
    assert 'No saved' in output[-1]
    assert not (tmp_path / 'data').exists()


@pytest.mark.asyncio
async def test_cli_drives_real_peer_exchange_and_saved_status(tmp_path):
    chatgpt = Member('chatgpt', ['draft A', 'improved A', 'final answer'])
    gemini = Member('gemini', ['draft B', 'improved B'])
    fleet = Fleet([chatgpt, gemini])
    output, setups = [], []
    code = await run_browser_team(['run', 'Solve the problem', '--work-mode', 'review', '--session', 'demo', '--setup', '--close-on-exit'],
        tmp_path, discover=lambda **_: inventory(tmp_path), fleet_factory=lambda *_, **__: fleet,
        progress=output.append, read_input=setups.append)
    assert code == 0 and fleet.closed and setups
    assert 'draft B' in chatgpt.prompts[1] and 'draft A' in gemini.prompts[1]
    assert 'improved B' in chatgpt.prompts[2]
    assert any('final answer' in value for value in output)
    status = saved_status(tmp_path / 'data/browser-team/team.sqlite3', 'demo')
    assert status['sessions'][0]['request']['status'] == 'extracted'
    assert len(status['sessions'][0]['rounds']) == 5
    assert 'final answer' not in json.dumps(status)


@pytest.mark.asyncio
async def test_open_keeps_windows_and_never_sends_a_prompt(tmp_path):
    member = Member('chatgpt', [])
    fleet = Fleet([member])
    code = await run_browser_team(['open'], tmp_path, discover=lambda **_: inventory(tmp_path),
        fleet_factory=lambda *_, **__: fleet, progress=lambda _: None)
    assert code == 0 and fleet.started and not fleet.closed and not member.prompts


@pytest.mark.asyncio
@pytest.mark.parametrize('flags,excluded', [([], {'signed-out'}), (['--recheck-signins'], set()), (['--setup'], set())])
async def test_run_excludes_only_confirmed_signouts_before_launch(tmp_path, flags, excluded):
    from app.providers.collaborative import TeamStore
    store = TeamStore(tmp_path / 'data/browser-team/team.sqlite3')
    store.member_state('signed-out', 'blocked', reason='login_required', submitted=False)
    store.member_state('captcha', 'blocked', reason='challenge', submitted=False)
    store.member_state('unknown', 'unavailable', reason='transient', submitted=False)
    store.close()
    fleet = Fleet([Member('healthy', ['answer'])])
    fleet.excluded_participants = set()
    start = fleet.start
    async def checked_start():
        assert fleet.excluded_participants == excluded
        return await start()
    fleet.start = checked_start
    code = await run_browser_team(['run', 'A task', '--work-mode', 'review', '--rounds', '1', *flags],
        tmp_path, discover=lambda **_: inventory(tmp_path), fleet_factory=lambda *_, **__: fleet,
        progress=lambda _: None, read_input=lambda _: '')
    assert code == 0 and fleet.started


@pytest.mark.asyncio
async def test_no_profiles_does_not_initialize_desktop(tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError('should not initialize native desktop')
    assert await run_browser_team(['run', 'task', '--leader', 'none'], tmp_path,
        discover=lambda **_: BrowserInventory([], [], []), fleet_factory=forbidden,
        progress=lambda _: None) == 1


@pytest.mark.asyncio
async def test_cli_enables_managed_leader_with_no_native_profiles(tmp_path):
    options = []
    fleet = Fleet([Member('chromium-leader:chatgpt', [])])
    def factory(root, **kwargs):
        options.append(kwargs)
        return fleet
    assert await run_browser_team(['open', '--leader-only', '--leader', 'chromium'], tmp_path,
        discover=lambda **_: BrowserInventory([], [], []), fleet_factory=factory,
        progress=lambda _: None) == 0
    assert options[0]['leader'] is True and options[0]['inventory'].profiles == []


@pytest.mark.asyncio
async def test_leader_only_rejects_profile_selection(tmp_path):
    with pytest.raises(ValueError, match='cannot combine'):
        await run_browser_team(['open', '--leader-only', '--profile', 'profile'], tmp_path,
            discover=lambda **_: inventory(tmp_path), progress=lambda _: None)


@pytest.mark.asyncio
@pytest.mark.parametrize('flags', [[], ['--leader-only'], ['--profile', 'profile']])
async def test_default_leader_keeps_signed_in_app_profile_and_open_window(tmp_path, flags):
    found = inventory(tmp_path)
    root = tmp_path / 'data/browser-profile'
    (root / 'Default').mkdir(parents=True)
    leader = BrowserProfile('app-profile', 'browser', 'App Chrome', root / 'Default', 'Default')
    found.profiles.append(leader)
    fleet = Fleet([Member('app-profile:chatgpt', [])])
    fleet._leader_clients = fleet.members
    captured = []
    def factory(root, **kwargs):
        captured.append(kwargs)
        return fleet
    async def forbidden_close():
        pytest.fail('open must retain the Chrome profile window')
    fleet.close_leader = forbidden_close
    assert await run_browser_team(['open', *flags], tmp_path, discover=lambda **_: found,
        fleet_factory=factory, progress=lambda _: None, read_input=lambda _: pytest.fail('No isolated leader setup')) == 0
    assert captured[0]['leader_mode'] == 'chrome-profile'
    profiles = captured[0]['inventory'].profiles
    assert leader in profiles and len(profiles) == (1 if '--leader-only' in flags else 2)


@pytest.mark.asyncio
async def test_recover_reads_prior_reply_without_asking_again(tmp_path):
    from app.providers.collaborative import TeamStore
    member = Member('chatgpt', [])
    store = TeamStore(tmp_path / 'data/browser-team/team.sqlite3')
    request = store.begin('recover-me', 'Old task')
    store.submission(request, member, 'proposal', 1)
    store.close()
    observed = []
    async def recover():
        observed.append(True)
        return 'Previously completed reply'
    member.recover_response = recover
    fleet = Fleet([member])
    code = await run_browser_team(['recover', '--session', 'recover-me', '--close-on-exit'], tmp_path,
        discover=lambda **_: inventory(tmp_path), fleet_factory=lambda *_, **__: fleet,
        progress=lambda _: None)
    assert code == 0 and observed and fleet.closed and not member.prompts
    status = saved_status(tmp_path / 'data/browser-team/team.sqlite3', 'recover-me')
    assert not status['unresolved_submissions']
    assert status['sessions'][0]['rounds'][0]['status'] == 'completed'


def test_status_includes_blocked_possibly_submitted_turns(tmp_path):
    from app.providers.collaborative import TeamStore
    database = tmp_path / 'team.sqlite3'
    member = Member('chatgpt', [])
    store = TeamStore(database)
    request = store.begin('demo', 'task')
    store.submission(request, member, 'proposal', 1)
    store.result(request, member.id, 'proposal', 1, 'blocked', submitted=True)
    store.close()
    assert saved_status(database)['unresolved_submissions'] == [
        {'member_id': 'chatgpt', 'status': 'blocked', 'session_id': 'demo'}]


@pytest.mark.asyncio
async def test_recovery_reports_unresolved_profile_even_when_it_could_not_launch(tmp_path):
    from app.providers.collaborative import TeamStore
    database = tmp_path / 'data/browser-team/team.sqlite3'
    missing = Member('missing-profile', [])
    store = TeamStore(database)
    request = store.begin('demo', 'Task')
    store.submission(request, missing, 'proposal', 1)
    store.close()
    fleet = Fleet([Member('healthy-profile', [])])
    fleet.failures['missing-profile'] = 'Locked browser profile'
    output = []
    code = await run_browser_team(['recover', '--session', 'demo'], tmp_path,
        discover=lambda **_: inventory(tmp_path), fleet_factory=lambda *_, **__: fleet,
        progress=output.append)
    assert code == 1
    assert any('Still unresolved' in line and 'missing-profile' in line for line in output)


@pytest.mark.asyncio
@pytest.mark.parametrize('flags', [['--timeout', 'nan'], ['--timeout', '0'], ['--rounds', '9'], ['--parallelism', '0']])
async def test_invalid_limits_are_rejected_before_discovery(tmp_path, flags):
    def forbidden(*args, **kwargs):
        raise AssertionError('invalid command reached discovery')
    with pytest.raises(SystemExit):
        await run_browser_team(['run', 'task', *flags], tmp_path, discover=forbidden)


@pytest.mark.asyncio
async def test_failed_execution_reports_pause_and_closes_owned_windows(tmp_path):
    fleet = Fleet([Member('chatgpt', [])])
    output = []
    async def execute(team, task):
        assert task == 'Build a village'
        raise RuntimeError('Blender unavailable')
    code = await run_browser_team(['run', 'Build a village', '--execute', '--close-on-exit'], tmp_path,
        discover=lambda **_: inventory(tmp_path), fleet_factory=lambda *_, **__: fleet,
        execute_task=execute, progress=output.append)
    assert code == 1 and fleet.closed
    assert any('Blender unavailable' in line for line in output)


@pytest.mark.asyncio
async def test_run_entrypoint_injects_team_without_starting_playwright(monkeypatch):
    import run
    import sys
    calls = []
    team = object()
    async def close():
        calls.append('closed')
    def application(root, settings, *, providers):
        assert providers.get('chatgpt') is team
        return SimpleNamespace(close=close)
    async def session(app, objective, followups, *, raise_on_error):
        assert objective == 'Build a village' and not followups and raise_on_error
        calls.append('executed')
    async def cli(arguments, root, *, execute_task, execute_desktop):
        await execute_task(team, 'Build a village')
        return 0
    monkeypatch.setattr(run, 'Application', application)
    monkeypatch.setattr(run, 'run_agent_session', session)
    monkeypatch.setattr('app.browser.team_cli.run_browser_team', cli)
    monkeypatch.setattr(sys, 'argv', ['run.py', 'browser-team', 'run', 'Build a village', '--execute'])
    await run.main()
    assert calls == ['executed', 'closed']


@pytest.mark.asyncio
async def test_doctor_only_probes_and_writes_health_report(tmp_path):
    member = Member('chatgpt', [])
    async def probe():
        return {'status': 'ready', 'ready': True}
    member.probe = probe
    fleet = Fleet([member])
    code = await run_browser_team(['doctor', '--close-on-exit'], tmp_path,
        discover=lambda **_: inventory(tmp_path), fleet_factory=lambda *_, **__: fleet,
        progress=lambda _: None)
    assert code == 0 and fleet.closed and not member.prompts
    reports = list((tmp_path / 'data/browser-team/diagnostics').glob('doctor-*.json'))
    assert len(reports) == 1
    assert json.loads(reports[0].read_text())['members'][0]['health']['status'] == 'ready'


@pytest.mark.asyncio
async def test_doctor_does_not_claim_readiness_without_probe_support(tmp_path):
    fleet = Fleet([Member('chatgpt', [])])
    code = await run_browser_team(['doctor'], tmp_path,
        discover=lambda **_: inventory(tmp_path), fleet_factory=lambda *_, **__: fleet,
        progress=lambda _: None)
    assert code == 1


@pytest.mark.asyncio
async def test_fleet_failure_is_saved_and_status_can_read_it_without_a_team_database(tmp_path):
    fleet = Fleet([])
    fleet.failures = {'profile': 'launch: process unavailable'}
    fleet.status = lambda: {'failures': fleet.failures, 'participant_count': 0,
                           'recovery_events': [{'action': 'failed', 'profile_id': 'profile'}]}
    output = []
    code = await run_browser_team(['open'], tmp_path, discover=lambda **_: inventory(tmp_path),
        fleet_factory=lambda *_, **__: fleet, progress=output.append)
    assert code == 1
    assert not (tmp_path / 'data/browser-team/team.sqlite3').exists()

    def forbidden(**kwargs):
        pytest.fail('Status must not discover browsers')

    assert await run_browser_team(['status'], tmp_path, discover=forbidden, progress=output.append) == 0
    snapshot = json.loads(output[-1])
    assert snapshot['sessions'] == []
    assert snapshot['last_fleet_run']['fleet']['failures'] == fleet.failures
    assert snapshot['last_fleet_run']['captured_at'] > 0


@pytest.mark.asyncio
async def test_doctor_reports_partial_fleet_even_when_available_members_are_ready(tmp_path):
    member = Member('chatgpt', [])

    async def probe():
        return {'status': 'ready', 'ready': True}

    member.probe = probe
    fleet = Fleet([member])
    fleet.failures = {'missing-profile': 'Could not launch'}
    code = await run_browser_team(['doctor'], tmp_path, discover=lambda **_: inventory(tmp_path),
        fleet_factory=lambda *_, **__: fleet, progress=lambda _: None)
    assert code == 1 and not member.prompts
    report = next((tmp_path / 'data/browser-team/diagnostics').glob('doctor-*.json'))
    assert json.loads(report.read_text())['fleet']['failures'] == fleet.failures


@pytest.mark.asyncio
async def test_corrupt_last_fleet_report_does_not_break_readonly_status(tmp_path):
    path = tmp_path / 'data/browser-team/diagnostics/last-fleet.json'
    path.parent.mkdir(parents=True)
    path.write_text('{unfinished', encoding='utf-8')
    output = []
    assert await run_browser_team(['status'], tmp_path, progress=output.append) == 0
    assert 'fleet_report_error' in json.loads(output[-1])


@pytest.mark.asyncio
async def test_report_write_failure_does_not_hide_successful_fleet_start(tmp_path, monkeypatch):
    fleet = Fleet([Member('chatgpt', [])])
    fleet.status = lambda: {'failures': {}}

    def unavailable(*args):
        raise OSError('Report directory locked')

    monkeypatch.setattr('app.browser.team_diagnostics.write_report', unavailable)
    output = []
    assert await run_browser_team(['open'], tmp_path, discover=lambda **_: inventory(tmp_path),
        fleet_factory=lambda *_, **__: fleet, progress=output.append) == 0
    assert any('Could not save browser recovery report' in line for line in output)


@pytest.mark.asyncio
async def test_unknown_profile_cannot_open_any_window(tmp_path):
    with pytest.raises(ValueError, match='Unknown profile'):
        await run_browser_team(['open', '--profile', 'wrong'], tmp_path,
            discover=lambda **_: inventory(tmp_path), fleet_factory=lambda *_, **__: pytest.fail('Must not launch'))


@pytest.mark.asyncio
async def test_desktop_route_passes_budgets_and_returns_blocked_without_false_success(tmp_path):
    fleet = Fleet([Member('chatgpt', [])])
    calls = []
    async def execute(team, task, **budgets):
        calls.append((task, budgets))
        return {'status': 'blocked', 'summary': 'Requested action requires approval'}
    code = await run_browser_team(['run', 'Open Notepad', '--desktop', '--max-actions', '4', '--max-minutes', '2'],
        tmp_path, discover=lambda **_: inventory(tmp_path), fleet_factory=lambda *_, **__: fleet,
        execute_desktop=execute, progress=lambda _: None)
    assert code == 1 and calls == [('Open Notepad', {'max_actions': 4, 'max_minutes': 2})]
    assert not fleet.members[0].prompts


@pytest.mark.asyncio
@pytest.mark.parametrize('arguments', [[], ['cli']])
async def test_normal_startup_routes_to_browser_team_not_managed_chromium(monkeypatch, arguments):
    import run
    import sys
    calls = []
    async def cli(arguments, root, **callbacks):
        calls.append(arguments)
        return 0
    monkeypatch.setattr('app.browser.team_cli.run_browser_team', cli)
    monkeypatch.setattr(run, 'Application', lambda *_, **__: pytest.fail('Legacy browser must not initialize'))
    monkeypatch.setattr(sys, 'argv', ['run.py', *arguments])
    await run.main()
    assert calls == [['run']]


def test_outer_default_and_cli_launch_maintained_project(monkeypatch):
    import importlib.util
    import subprocess
    from pathlib import Path
    outer = Path(__file__).resolve().parents[2] / 'run.py'
    spec = importlib.util.spec_from_file_location('outer_launch_for_test', outer)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    monkeypatch.setattr(subprocess, 'call', lambda argv, **kwargs: calls.append((argv, kwargs)) or 0)
    assert module.main([]) == 0
    assert module.main(['cli']) == 0
    assert all(call[0][1] == str(outer.parent / 'Brainless_agent/run.py') for call in calls)
    assert calls[0][0][2:] == [] and calls[1][0][2:] == ['cli']


def test_gui_team_worker_does_not_call_legacy_runtime(monkeypatch, tmp_path):
    import queue
    from app.gui import BrainlessWindow
    calls = []
    async def cli(arguments, root, **kwargs):
        calls.append((arguments, root))
        kwargs['progress']('Opened discovered profiles')
        return 0
    monkeypatch.setattr('app.browser.team_cli.run_browser_team', cli)
    window = BrainlessWindow.__new__(BrainlessWindow)
    window.root_path = tmp_path
    window.events = queue.Queue()
    window._run_team('Explain the task')
    assert calls == [(['run', 'Explain the task', '--wait-ready', '120'], tmp_path)]
    assert window.events.get()[0] == 'progress'
    assert window.events.get()[0] == 'complete'
