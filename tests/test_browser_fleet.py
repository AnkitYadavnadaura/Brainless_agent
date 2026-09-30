import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.browser.fleet import BrowserFleet
from app.browser.fleet_discovery import BrowserInstallation, BrowserInventory, BrowserProfile
from app.browser.native_console import NativeLaunchError


class FakeTransport:
    """An owned-window transport with deterministic launch/setup/close failures."""

    def __init__(self):
        self.trace = []
        self.open_windows = set()
        self.navigation_count = 0
        self.launch_count = 0
        self.fail_navigation = set()
        self.fail_launch = set()
        self.fail_close = set()
        self.launch_entered = None
        self.launch_release = None
        self.navigation_entered = None
        self.navigation_release = None

    async def launch(self, arguments, marker):
        self.launch_count += 1
        hwnd = 100 + self.launch_count
        self.trace.append(('launch', hwnd, arguments, marker))
        if self.launch_entered is not None:
            self.launch_entered.set()
            await self.launch_release.wait()
        if self.launch_count in self.fail_launch:
            raise RuntimeError('Window could not be identified')
        self.open_windows.add(hwnd)
        return hwnd

    async def navigate(self, hwnd, url, new_tab=False, *, tab_index=None):
        assert hwnd in self.open_windows
        self.navigation_count += 1
        self.trace.append(('navigate', hwnd, url, new_tab, tab_index))
        if self.navigation_entered is not None:
            self.navigation_entered.set()
            await self.navigation_release.wait()
        if self.navigation_count in self.fail_navigation:
            raise RuntimeError('Desktop focus changed')

    async def close(self, hwnd):
        assert hwnd in self.open_windows
        self.trace.append(('close', hwnd))
        if hwnd in self.fail_close:
            raise RuntimeError('Window still open')
        self.open_windows.remove(hwnd)


def inventory(root, count=2):
    browser = BrowserInstallation('chrome', 'Google Chrome', 'chromium',
                                  root / 'chrome.exe', root / 'User Data')
    profiles = [BrowserProfile(f'profile-{index}', browser.id, f'Person {index}',
                              browser.user_data_dir / f'Profile {index}', f'Profile {index}')
                for index in range(count)]
    return BrowserInventory([browser], profiles, ['Example discovery warning'])


def fleet(root, transport, *, discovered=None, **kwargs):
    return BrowserFleet(root, transport=transport, inventory=discovered or inventory(root),
                        progress=lambda message: None, retry_delay=0, **kwargs)


@pytest.mark.asyncio
async def test_known_signed_out_profiles_never_launch_and_partial_profile_keeps_eligible_provider(tmp_path):
    transport = FakeTransport()
    team = fleet(tmp_path, transport)
    team.excluded_participants = {'profile-0:chatgpt', 'profile-0:gemini', 'profile-1:chatgpt'}
    try:
        clients = await team.start()
        assert [client.id for client in clients] == ['profile-1:gemini']
        assert clients[0].tab_index == 1 and transport.launch_count == 1
        navigation = [row for row in transport.trace if row[0] == 'navigate']
        assert len(navigation) == 1 and navigation[0][2] == 'https://gemini.google.com/app'
        assert team._states['profile-0'] == 'excluded_unsigned'
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_managed_chromium_leads_without_native_profiles_and_is_closed(tmp_path):
    clients = [SimpleNamespace(id='chromium-leader:chatgpt', team_role='leader')]
    calls = []
    class Leader:
        def __init__(self, *args, **kwargs):
            pass
        async def start(self):
            calls.append('start')
            return clients
        async def close(self):
            calls.append('close')
    team = BrowserFleet(tmp_path, inventory=BrowserInventory([], [], []), leader=True,
                        leader_factory=Leader, progress=lambda _: None)
    assert await team.start() == clients
    await team.start()
    assert calls == ['start'] and team.status()['leader']['state'] == 'ready'
    await team.close()
    assert calls == ['start', 'close'] and not team.participants
    assert team.status()['leader']['state'] == 'closed'


@pytest.mark.asyncio
async def test_signed_in_app_chrome_profile_is_leader_without_duplicate_or_isolated_launch(tmp_path):
    transport = FakeTransport()
    discovered = inventory(tmp_path, count=1)
    profile_root = tmp_path / 'data/browser-profile'
    (profile_root / 'Default').mkdir(parents=True)
    (profile_root / 'Local State').write_text(json.dumps({'profile': {'last_used': 'Default'}}))
    leader = BrowserProfile('app-profile', 'chrome', 'App Chrome', profile_root / 'Default', 'Default')
    discovered.profiles.append(leader)
    def forbidden(*args, **kwargs):
        pytest.fail('Must not create another Chromium profile')
    team = fleet(tmp_path, transport, discovered=discovered, leader=True,
                 leader_mode='chrome-profile', leader_factory=forbidden)
    try:
        clients = await team.start()
        assert [client.id for client in clients[:2]] == ['app-profile:chatgpt', 'app-profile:gemini']
        assert all(client.team_role == 'leader' for client in clients[:2])
        assert transport.launch_count == 2
        launch = next(row for row in transport.trace if row[0] == 'launch')
        assert '--user-data-dir=' + str(profile_root) in launch[2]
        assert '--profile-directory=Default' in launch[2]
        assert team.status()['window_count'] == 2 and team.status()['leader']['driver'] == 'native'
        await team.close_leader()
        assert len(transport.open_windows) == 1 and all(client.id.startswith('profile-0:') for client in team.participants)
        await team.start()
        assert transport.launch_count == 3 and len(team._leader_clients) == 2
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_chrome_profile_leader_uses_its_own_signin_cache(tmp_path):
    discovered = inventory(tmp_path, count=0)
    root = tmp_path / 'data/browser-profile'
    (root / 'Default').mkdir(parents=True)
    discovered.profiles.append(BrowserProfile('app-profile', 'chrome', 'App', root / 'Default', 'Default'))
    team = fleet(tmp_path, FakeTransport(), discovered=discovered, leader=True, leader_mode='chrome-profile')
    team.excluded_participants = {'chromium-leader:chatgpt', 'chromium-leader:gemini', 'app-profile:gemini'}
    try:
        assert [client.id for client in await team.start()] == ['app-profile:chatgpt']
        assert team.participants[0].team_role == 'leader'
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_failed_leader_does_not_prevent_native_peers_starting(tmp_path):
    class Leader:
        def __init__(self, *args, **kwargs):
            pass
        async def start(self):
            raise OSError('Chromium profile is locked')
        async def close(self):
            pass
    transport = FakeTransport()
    team = fleet(tmp_path, transport, leader=True, leader_factory=Leader)
    await team.start()
    assert len(team.participants) == 4 and transport.launch_count == 2
    assert team.status()['leader']['state'] == 'failed'
    assert 'chromium-leader' in team.failures
    await team.close()
    assert not transport.open_windows


@pytest.mark.asyncio
async def test_opens_both_providers_once_for_each_unique_profile(tmp_path):
    discovered = inventory(tmp_path)
    discovered.profiles.extend([discovered.profiles[0], replace(discovered.profiles[1], id='alias')])
    transport = FakeTransport()
    team = fleet(tmp_path, transport, discovered=discovered)
    first, second = await asyncio.gather(team.start(), team.start())
    assert first is second is team.participants
    assert transport.launch_count == 2
    assert {client.id for client in team.participants} == {
        'profile-0:chatgpt', 'profile-0:gemini', 'profile-1:chatgpt', 'profile-1:gemini'}
    assert [(row[2], row[3], row[4]) for row in transport.trace if row[0] == 'navigate'] == [
        ('https://chatgpt.com/', False, 1), ('https://gemini.google.com/app', True, None)] * 2
    status = team.status()
    assert (status['browser_count'], status['profile_count'], status['window_count'],
            status['participant_count']) == (1, 2, 2, 4)
    assert all(row['state'] == 'ready' and len(row['participant_ids']) == 2 for row in status['profiles'])
    assert any('Duplicate' in warning for warning in status['warnings'])
    assert json.loads(json.dumps(status)) == status


@pytest.mark.asyncio
async def test_partial_window_is_closed_before_retry_and_success_clears_failure(tmp_path):
    transport = FakeTransport()
    transport.fail_navigation = {2}
    team = fleet(tmp_path, transport, discovered=inventory(tmp_path, 1))
    await team.start()
    assert transport.launch_count == 2
    assert transport.open_windows == {102}
    assert [row[0] for row in transport.trace] == [
        'launch', 'navigate', 'navigate', 'close', 'launch', 'navigate', 'navigate']
    assert len(team.participants) == 2
    assert not team.failures
    assert team.status()['profiles'][0]['attempts'] == 2


@pytest.mark.asyncio
async def test_later_start_retries_failed_profile_while_preserving_healthy_clients(tmp_path):
    transport = FakeTransport()
    transport.fail_navigation = {3}
    team = fleet(tmp_path, transport, max_launch_attempts=1)
    await team.start()
    healthy = list(team.participants)
    assert transport.open_windows == {101}
    assert team.status()['profiles'][1]['state'] == 'failed'
    await team.start()
    assert team.participants[:2] == healthy
    assert transport.launch_count == 3
    assert transport.open_windows == {101, 103}
    assert not team.failures


@pytest.mark.asyncio
async def test_failed_cleanup_blocks_duplicate_launch_until_close_succeeds(tmp_path):
    transport = FakeTransport()
    transport.fail_navigation = {2}
    transport.fail_close = {101}
    team = fleet(tmp_path, transport, discovered=inventory(tmp_path, 1))
    await team.start()
    await team.start()
    assert transport.launch_count == 1
    assert team.windows == {'profile-0': 101}
    assert not team.participants
    assert team.status()['profiles'][0]['state'] == 'cleanup_failed'
    assert 'retry cleanup before relaunching' in team.failures['profile-0']
    transport.fail_close.clear()
    await team.start()
    assert transport.launch_count == 2
    assert transport.open_windows == {102}
    assert team.status()['profiles'][0]['state'] == 'ready'


@pytest.mark.asyncio
async def test_uncertain_launch_is_not_repeated_and_other_profiles_continue(tmp_path):
    transport = FakeTransport()
    transport.fail_launch = {1}
    team = fleet(tmp_path, transport)
    await team.start()
    await team.start()
    assert transport.launch_count == 2
    assert len(team.participants) == 2
    failed = team.status()['profiles'][0]
    assert failed['state'] == 'launch_uncertain'
    assert failed['hwnd'] is None
    assert 'Launch will not be repeated' in failed['error']


@pytest.mark.asyncio
async def test_close_retains_failed_window_for_cleanup_and_can_restart_afterwards(tmp_path):
    transport = FakeTransport()
    team = fleet(tmp_path, transport)
    await team.start()
    transport.fail_close = {101}
    await team.close()
    assert team.windows == {'profile-0': 101}
    assert not team.participants
    assert [row['state'] for row in team.status()['profiles']] == ['cleanup_failed', 'closed']
    transport.fail_close.clear()
    await team.close()
    await team.close()
    assert not team.windows and not team.failures
    assert not transport.open_windows
    await team.start()
    assert len(team.participants) == 4
    assert transport.open_windows == {103, 104}


@pytest.mark.asyncio
async def test_cancelled_launch_waits_for_owned_handle_and_closes_window(tmp_path):
    transport = FakeTransport()
    transport.launch_entered, transport.launch_release = asyncio.Event(), asyncio.Event()
    team = fleet(tmp_path, transport, discovered=inventory(tmp_path, 1))
    starting = asyncio.create_task(team.start())
    await transport.launch_entered.wait()
    starting.cancel()
    await asyncio.sleep(0)
    assert not starting.done()
    transport.launch_release.set()
    with pytest.raises(asyncio.CancelledError):
        await starting
    assert not transport.open_windows
    assert not team.windows and not team.participants
    assert [row[0] for row in transport.trace] == ['launch', 'close']


@pytest.mark.asyncio
async def test_cancelled_navigation_cleans_partial_window(tmp_path):
    transport = FakeTransport()
    transport.navigation_entered, transport.navigation_release = asyncio.Event(), asyncio.Event()
    team = fleet(tmp_path, transport, discovered=inventory(tmp_path, 1))
    starting = asyncio.create_task(team.start())
    await transport.navigation_entered.wait()
    starting.cancel()
    with pytest.raises(asyncio.CancelledError):
        await starting
    assert not transport.open_windows and not team.windows and not team.participants


@pytest.mark.asyncio
async def test_client_construction_failure_does_not_publish_half_profile(tmp_path, monkeypatch):
    from app.browser import fleet as module

    original = module.NativeWebsiteClient

    def client(**kwargs):
        if kwargs['provider_name'] == 'gemini':
            raise RuntimeError('Invalid participant configuration')
        return original(**kwargs)

    monkeypatch.setattr(module, 'NativeWebsiteClient', client)
    transport = FakeTransport()
    team = fleet(tmp_path, transport, discovered=inventory(tmp_path, 1), max_launch_attempts=1)
    await team.start()
    assert not team.participants and not team.windows and not transport.open_windows
    assert 'Invalid participant configuration' in team.failures['profile-0']


@pytest.mark.asyncio
async def test_missing_installation_is_reported_without_stopping_other_profiles(tmp_path):
    discovered = inventory(tmp_path)
    discovered.profiles[0] = replace(discovered.profiles[0], browser_id='missing')
    transport = FakeTransport()
    team = fleet(tmp_path, transport, discovered=discovered)
    await team.start()
    assert transport.launch_count == 1
    assert len(team.participants) == 2
    assert team.status()['profiles'][0]['state'] == 'invalid'
    assert 'rediscover' in team.failures['profile-0']


@pytest.mark.asyncio
async def test_empty_inventory_needs_no_desktop_backend(tmp_path, monkeypatch):
    def unexpected_backend():
        pytest.fail('Empty fleet must not initialize desktop automation')

    monkeypatch.setattr('app.browser.fleet.NativeConsoleTransport', unexpected_backend)
    team = BrowserFleet(tmp_path, inventory=BrowserInventory([], [], []), progress=lambda message: None)
    assert await team.start() == []
    await team.close()
    assert team.status()['window_count'] == 0


@pytest.mark.parametrize('attempts', [0, 6, True, 1.5])
def test_launch_retries_are_bounded(tmp_path, attempts):
    with pytest.raises(ValueError, match='max_launch_attempts'):
        BrowserFleet(tmp_path, max_launch_attempts=attempts)


@pytest.mark.asyncio
async def test_definitely_unstarted_process_is_retried_within_budget(tmp_path):
    transport = FakeTransport()
    launch = transport.launch
    calls = 0

    async def transient_launch(arguments, marker):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise NativeLaunchError('Process temporarily unavailable', launched=False)
        return await launch(arguments, marker)

    transport.launch = transient_launch
    team = fleet(tmp_path, transport, discovered=inventory(tmp_path, 1))
    await team.start()
    assert calls == 2 and transport.open_windows == {101}
    assert not team.failures and len(team.participants) == 2
    assert team.status()['profiles'][0]['attempts'] == 2
    assert team.status()['recovery_events'][0]['action'] == 'failed'


@pytest.mark.asyncio
async def test_permanent_spawn_failure_stops_at_attempt_budget(tmp_path):
    transport = FakeTransport()
    calls = 0

    async def unavailable(arguments, marker):
        nonlocal calls
        calls += 1
        raise NativeLaunchError('Executable unavailable', launched=False)

    transport.launch = unavailable
    team = fleet(tmp_path, transport, discovered=inventory(tmp_path, 1), max_launch_attempts=3)
    assert await team.start() == []
    assert calls == 3 and not transport.open_windows
    assert team.status()['profiles'][0]['state'] == 'failed'


@pytest.mark.asyncio
@pytest.mark.parametrize('immediate', [True, False])
async def test_late_window_is_adopted_without_relaunch(tmp_path, immediate):
    transport = FakeTransport()
    transport.fail_launch = {1}
    seen_markers = []
    appeared = immediate

    async def recover(marker):
        seen_markers.append(marker)
        if appeared:
            transport.open_windows.add(101)
            return 101
        return None

    transport.recover_launch = recover
    team = fleet(tmp_path, transport, discovered=inventory(tmp_path, 1))
    await team.start()
    if not immediate:
        assert not team.participants
        appeared = True
        await team.start()
    assert transport.launch_count == 1 and transport.open_windows == {101}
    assert len(set(seen_markers)) == 1
    assert len(team.participants) == 2 and not team.failures
    assert any(event['action'] == 'launch_recovered' for event in team.status()['recovery_events'])


@pytest.mark.asyncio
async def test_recovery_probe_failure_keeps_launch_uncertain(tmp_path):
    transport = FakeTransport()
    transport.fail_launch = {1}

    async def unavailable(marker):
        raise OSError('Window enumeration unavailable')

    transport.recover_launch = unavailable
    team = fleet(tmp_path, transport, discovered=inventory(tmp_path, 1))
    await team.start()
    await team.start()
    assert transport.launch_count == 1 and not team.participants
    assert team.status()['profiles'][0]['state'] == 'launch_uncertain'


@pytest.mark.asyncio
async def test_closed_window_is_rebuilt_and_healthy_profile_is_preserved(tmp_path):
    transport = FakeTransport()

    async def alive(hwnd):
        return hwnd in transport.open_windows

    async def close(hwnd):
        transport.open_windows.discard(hwnd)

    transport.window_alive, transport.close = alive, close
    team = fleet(tmp_path, transport)
    await team.start()
    healthy = team.participants[2:]
    transport.open_windows.remove(101)
    await team.start()
    assert transport.launch_count == 3 and transport.open_windows == {102, 103}
    assert team.participants[:2] == healthy and len(team.participants) == 4
    assert not team.failures
    assert team.status()['recovery_events'][0]['action'] == 'window_lost'


@pytest.mark.asyncio
async def test_failed_health_inspection_neither_closes_nor_duplicates_window(tmp_path):
    transport = FakeTransport()
    readable = False

    async def alive(hwnd):
        if not readable:
            raise OSError('Window identity temporarily unavailable')
        return True

    transport.window_alive = alive
    team = fleet(tmp_path, transport, discovered=inventory(tmp_path, 1))
    await team.start()
    originals = list(team.participants)
    for client in originals:
        client.use_conversation_session('active-project')
        client.set_checkpoint_context({'objective': 'Keep the active task'})
    await team.start()
    assert team.status()['profiles'][0]['state'] == 'health_unknown'
    assert not team.participants and transport.open_windows == {101}
    assert not any(row[0] == 'close' for row in transport.trace)
    readable = True
    await team.start()
    assert transport.launch_count == 1 and transport.navigation_count == 2
    assert len(team.participants) == 2 and not team.failures
    assert team.participants == originals
    assert all(client.session == 'active-project' for client in team.participants)


@pytest.mark.asyncio
async def test_cancelled_late_adoption_closes_the_owned_window(tmp_path):
    transport = FakeTransport()
    transport.fail_launch = {1}
    entered, release = asyncio.Event(), asyncio.Event()

    async def recover(marker):
        entered.set()
        await release.wait()
        transport.open_windows.add(101)
        return 101

    transport.recover_launch = recover
    team = fleet(tmp_path, transport, discovered=inventory(tmp_path, 1))
    starting = asyncio.create_task(team.start())
    await entered.wait()
    starting.cancel()
    await asyncio.sleep(0)
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await starting
    assert not transport.open_windows and not team.windows and not team.participants


@pytest.mark.parametrize('options', [
    {'timeout_seconds': float('nan')}, {'timeout_seconds': 0}, {'timeout_seconds': True},
    {'poll_interval': float('inf')}, {'poll_interval': -1}, {'poll_interval': '2'},
    {'rollover_after': False}, {'rollover_after': 1.5},
    {'retry_delay': -1}, {'retry_delay': float('inf')}, {'retry_delay': 31},
])
def test_invalid_configuration_fails_before_creating_runtime_data(tmp_path, options):
    with pytest.raises(ValueError):
        BrowserFleet(tmp_path, **options)
    assert not (tmp_path / 'data').exists()


@pytest.mark.asyncio
async def test_repeated_cancel_does_not_abandon_launch_or_cleanup(tmp_path):
    transport = FakeTransport()
    transport.launch_entered, transport.launch_release = asyncio.Event(), asyncio.Event()
    team = fleet(tmp_path, transport, discovered=inventory(tmp_path, 1))
    starting = asyncio.create_task(team.start())
    await transport.launch_entered.wait()
    starting.cancel()
    await asyncio.sleep(0)
    starting.cancel()
    await asyncio.sleep(0)
    transport.launch_release.set()
    with pytest.raises(asyncio.CancelledError):
        await starting
    assert not transport.open_windows and not team.windows
    assert transport.launch_count == 1


@pytest.mark.asyncio
async def test_cancelled_close_commits_cleanup_and_allows_restart(tmp_path):
    transport = FakeTransport()
    team = fleet(tmp_path, transport)
    await team.start()
    entered, release = asyncio.Event(), asyncio.Event()
    close = transport.close

    async def slow_close(hwnd):
        entered.set()
        await release.wait()
        await close(hwnd)

    transport.close = slow_close
    closing = asyncio.create_task(team.close())
    await entered.wait()
    closing.cancel()
    await asyncio.sleep(0)
    closing.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await closing
    assert not team.windows and not transport.open_windows
    assert not team.participants and not team.failures
    await team.start()
    assert transport.open_windows == {103, 104} and len(team.participants) == 4
