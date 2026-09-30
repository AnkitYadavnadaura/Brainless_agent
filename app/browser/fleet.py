"""Launch installed profiles and assemble their website-only reasoning team."""
from __future__ import annotations

import asyncio
from collections import deque
import math
import time
import uuid
from pathlib import Path
from urllib.parse import quote
from typing import TYPE_CHECKING, Any

from app.browser.fleet_discovery import discover_browsers, managed_leader_profile, profile_launch_arguments
from app.browser.native_console import NativeConsoleTransport, NativeLaunchError
from app.providers.native_website import NativeSessionStore, NativeWebsiteClient

if TYPE_CHECKING:
    from app.browser.client import BrowserClient


async def _finish_owned_operation(operation):
    """Drain desktop work despite repeated cancellation, then let callers commit.

    Returning the finished task lets ownership bookkeeping run before either
    its exception or the caller's cancellation is propagated.
    """
    task = asyncio.create_task(operation)
    cancellation = None
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError as error:
            cancellation = error
        except Exception:
            break
    return task, cancellation


class BrowserFleet:
    def __init__(self, root: Path, *, transport=None, inventory=None, progress=print,
                 timeout_seconds=180, poll_interval=2, rollover_after=20,
                 max_launch_attempts=2, input_mode='auto', retry_delay=0.5,
                 leader=False, leader_factory=None, leader_mode='chromium'):
        if leader_mode not in ('chromium', 'chrome-profile'):
            raise ValueError('Unknown leader mode')
        if input_mode not in ('auto', 'console', 'native'):
            raise ValueError('input_mode must be auto, console or native')
        if type(max_launch_attempts) is not int or not 1 <= max_launch_attempts <= 5:
            raise ValueError('max_launch_attempts must be an integer between 1 and 5')
        for name, value in (('timeout_seconds', timeout_seconds), ('poll_interval', poll_interval)):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be a finite positive number')
        if type(rollover_after) is not int or rollover_after <= 0:
            raise ValueError('rollover_after must be a positive integer')
        if type(retry_delay) not in (int, float) or not math.isfinite(retry_delay) or not 0 <= retry_delay <= 30:
            raise ValueError('retry_delay must be between 0 and 30 seconds')
        self.root = Path(root)
        # Discovery/status can be inspected without initializing desktop input.
        self.transport = transport
        self.inventory = inventory
        self.progress = progress
        self.timeout_seconds, self.poll_interval = timeout_seconds, poll_interval
        self.rollover_after = rollover_after
        self.input_mode = input_mode
        self.max_launch_attempts = max_launch_attempts
        self.retry_delay = retry_delay
        self.leader_enabled = leader
        self.leader_mode = leader_mode
        self.leader_profile_id = None
        self._leader = None
        self._leader_factory = leader_factory
        self._leader_clients = []
        self._browser_clients = []
        self.excluded_participants = set()
        self._leader_state = 'pending' if leader else 'disabled'
        self.windows: dict[str, int] = {}
        self.participants: list[NativeWebsiteClient] = []
        self._suspended_participants: dict[str, list[NativeWebsiteClient]] = {}
        self.failures: dict[str, str] = {}
        self._states: dict[str, str] = {}
        self._attempts: dict[str, int] = {}
        self._launch_markers: dict[str, str] = {}
        self._recovery_events = deque(maxlen=100)
        self._lifecycle_lock = asyncio.Lock()
        self.store = NativeSessionStore(self.root / 'data/browser-team/native-sessions.sqlite3')

    def _inventory_entries(self):
        """Defend injected/stale inventories against aliases and missing browsers."""
        if self.inventory is None:
            return {}, [], []
        installations = {}
        for browser in self.inventory.browsers:
            installations.setdefault(browser.id, browser)
        warnings = list(self.inventory.warnings)
        profiles, seen_ids, seen_paths = [], set(), set()
        for profile in self.inventory.profiles:
            path = str(Path(profile.directory).resolve()).casefold()
            if profile.id in seen_ids or path in seen_paths:
                warnings.append(f'Duplicate profile {profile.name} was skipped.')
                continue
            seen_ids.add(profile.id)
            seen_paths.add(path)
            profiles.append(profile)
        return installations, profiles, list(dict.fromkeys(warnings))

    def status(self) -> dict:
        """Return JSON-ready lifecycle state; ready means tabs opened, not signed in."""
        installations, profiles, warnings = self._inventory_entries()
        rows = []
        for profile in profiles:
            browser = installations.get(profile.browser_id)
            rows.append({
                'id': profile.id, 'browser_id': profile.browser_id,
                'browser': browser.name if browser else None, 'name': profile.name,
                'state': self._states.get(profile.id, 'pending'),
                'hwnd': self.windows.get(profile.id),
                'participant_ids': [client.id for client in self.participants
                                    if client.id in (profile.id + ':chatgpt', profile.id + ':gemini')],
                'error': self.failures.get(profile.id),
                'attempts': self._attempts.get(profile.id, 0),
            })
        return {
            'discovered': self.inventory is not None,
            'browser_count': len(installations), 'profile_count': len(profiles),
            'window_count': len(self.windows) + bool(self._leader_clients and self.leader_mode == 'chromium'), 'participant_count': len(self.participants),
            'warnings': warnings, 'failures': dict(self.failures), 'profiles': rows,
            'recovery_events': list(self._recovery_events),
            'leader': {'enabled': self.leader_enabled, 'driver': 'native' if self.leader_mode == 'chrome-profile' else 'playwright',
                       'profile_id': self.leader_profile_id,
                       'user_data_dir': str(self.root / 'data/browser-profile') if self.leader_mode == 'chrome-profile' else str(self.root / 'data/chromium-leader'),
                       'state': self._leader_state,
                       'participant_ids': [client.id for client in self._leader_clients],
                       'error': self.failures.get(self.leader_profile_id or 'chromium-leader')},
        }

    async def _start_leader(self):
        if not self.leader_enabled or self._leader_clients:
            return
        if self.leader_mode == 'chrome-profile':
            # Native launch reuses the exact Chrome user-data directory even
            # when its manual window is open. Only our new window is owned.
            if self.leader_profile_id is None:
                self._leader_state = 'failed'
                self.failures['chromium-leader'] = ('Chrome leader profile not found at ' +
                    str(self.root / 'data/browser-profile') + '. Open Chrome with this --user-data-dir first.')
                self.progress(self.failures['chromium-leader'])
            elif all(self.leader_profile_id + ':' + name in self.excluded_participants for name in ('chatgpt', 'gemini')):
                self._leader_state = 'excluded_unsigned'
            return
        if all('chromium-leader:' + name in self.excluded_participants for name in ('chatgpt', 'gemini')):
            self._leader_state = 'excluded_unsigned'
            return
        if self._leader is None:
            from app.browser.chromium_leader import ChromiumLeader
            self._leader = (self._leader_factory or ChromiumLeader)(
                self.root, timeout_seconds=self.timeout_seconds, poll_interval=self.poll_interval,
                rollover_after=self.rollover_after, progress=self.progress)
            self._leader.excluded_providers = {name for name in ('chatgpt', 'gemini')
                                               if 'chromium-leader:' + name in self.excluded_participants}
        try:
            self._leader_clients = await self._leader.start()
            self.participants[0:0] = self._leader_clients
            self._leader_state = 'ready'
            self.failures.pop('chromium-leader', None)
        except Exception as error:
            message = f'{type(error).__name__}: {error}'[:1500]
            if 'Executable doesn' in message or 'playwright install' in message:
                message = 'Chromium is missing. Run: python -m playwright install chromium'
            self.failures['chromium-leader'] = message
            self._leader_state = 'failed'
            self._record_recovery('chromium-leader', 'leader_unavailable', message)
            self.progress(f'Chromium leader unavailable: {message}. Available peers can lead instead.')

    async def browser_client(self, **options: Any) -> 'BrowserClient':
        """Create generic owned tabs alongside, not inside, provider tabs.

        This is available only for the Playwright Chromium leader. Native
        installed-profile windows intentionally remain provider-only until
        their transport gains a separate generic DOM contract.
        """
        if not self.leader_enabled or self.leader_mode != 'chromium':
            raise RuntimeError(
                'Generic BrowserClient requires an enabled Playwright Chromium leader')
        async with self._lifecycle_lock:
            await self._start_leader()
            context = getattr(self._leader, 'context', None)
            if context is None:
                raise RuntimeError('The Playwright Chromium leader is unavailable')
            from app.browser.client import BrowserClient
            from app.browser.sessions import BrowserSessionStore

            options.setdefault(
                'store',
                BrowserSessionStore(self.root / 'data/browser-sessions.sqlite3'))
            options.setdefault('browser_id', 'chromium-leader')
            client = BrowserClient(context, **options)
            self._browser_clients.append(client)
            return client

    async def close_leader(self):
        if self.leader_mode == 'chrome-profile':
            if self.leader_profile_id and self.leader_profile_id in self.windows:
                if await self._cleanup_window(self.leader_profile_id, clear_failure=True):
                    self._leader_state = 'closed'
            return
        if self._leader is None:
            return
        cleanup, cancellation = await _finish_owned_operation(self._leader.close())
        try:
            cleanup.result()
            identities = {client.id for client in self._leader_clients}
            self.participants[:] = [client for client in self.participants if client.id not in identities]
            self._leader_clients = []
            self._leader_state = 'closed'
        finally:
            if cancellation:
                raise cancellation

    def _record_recovery(self, profile_id, action, detail):
        self._recovery_events.append(dict(profile_id=profile_id, action=action,
                                          detail=detail, time=time.time()))

    def _publish_clients(self, profile, browser, hwnd):
        names = [name for name in ('chatgpt', 'gemini') if profile.id + ':' + name not in self.excluded_participants]
        clients = [NativeWebsiteClient(
            participant_id=profile.id + ':' + name, provider_name=name, hwnd=hwnd,
            family=browser.family, tab_index=index, transport=self.transport, store=self.store,
            timeout_seconds=self.timeout_seconds, poll_interval=self.poll_interval,
            rollover_after=self.rollover_after, input_mode=self.input_mode)
            for index, name in enumerate(names, 1)]
        self._discard_participants(profile.id)
        self.participants.extend(clients)
        if profile.id == self.leader_profile_id:
            for client in clients:
                client.team_role = 'leader'
            self._leader_clients = clients
            self._leader_state = 'ready'
            self.progress('Chrome profile leader: ' + str(profile.directory))
        self._states[profile.id] = 'ready'
        self.failures.pop(profile.id, None)

    def _discard_participants(self, profile_id):
        identities = {profile_id + ':chatgpt', profile_id + ':gemini'}
        self.participants[:] = [client for client in self.participants if client.id not in identities]
        self._suspended_participants.pop(profile_id, None)
        if profile_id == self.leader_profile_id:
            self._leader_clients = []

    async def _cleanup_window(self, profile_id, *, clear_failure=False):
        """Keep failed closes tracked so a retry cannot create duplicate windows."""
        self._discard_participants(profile_id)
        hwnd = self.windows.get(profile_id)
        if hwnd is None:
            return True
        closing, cancellation = await _finish_owned_operation(self.transport.close(hwnd))
        try:
            try:
                closing.result()
            except Exception as error:
                self._states[profile_id] = 'cleanup_failed'
                self.failures[profile_id] = (
                    f'Could not close owned window {hwnd}: {type(error).__name__}: {error}. '
                    'Resolve the window condition and retry cleanup before relaunching this profile.')
                self.progress(self.failures[profile_id])
                self._record_recovery(profile_id, 'cleanup_failed', self.failures[profile_id])
                return False
            self.windows.pop(profile_id, None)
            if clear_failure:
                self.failures.pop(profile_id, None)
                self._states[profile_id] = 'closed'
            return True
        finally:
            if cancellation is not None:
                raise cancellation

    async def _claim_window(self, profile_id, operation):
        # Native launch runs in a thread. Recover its returned handle even when
        # the caller cancels, so the outer cancellation cleanup can close it.
        launch, cancellation = await _finish_owned_operation(operation)
        try:
            hwnd = launch.result()
        except (Exception, asyncio.CancelledError) as error:
            if cancellation is not None:
                self._states[profile_id] = 'launch_uncertain'
                self.failures[profile_id] = (
                    f'Cancelled launch could not identify its window: {error}. '
                    'Inspect this profile manually before starting a new fleet.')
                raise cancellation
            raise
        if hwnd is not None:
            self.windows[profile_id] = hwnd
        if cancellation is not None:
            raise cancellation
        return hwnd

    async def _recover_window(self, profile_id):
        recover = getattr(self.transport, 'recover_launch', None)
        marker = self._launch_markers.get(profile_id)
        if recover is None or marker is None:
            return None
        try:
            hwnd = await self._claim_window(profile_id, recover(marker))
        except Exception as error:
            self._record_recovery(profile_id, 'launch_inspection_failed', f'{type(error).__name__}: {error}')
            return None
        if hwnd is not None:
            self._launch_markers.pop(profile_id, None)
            self._record_recovery(profile_id, 'launch_recovered', 'Identified the original launch without spawning again.')
            self.progress(f'Recovered the original window for {profile_id}.')
        return hwnd

    async def _launch_window(self, profile_id, arguments, marker):
        self._launch_markers[profile_id] = marker
        try:
            hwnd = await self._claim_window(profile_id, self.transport.launch(arguments, marker))
        except Exception as error:
            if isinstance(error, NativeLaunchError) and not error.launched:
                self._launch_markers.pop(profile_id, None)
                raise
            # A slow window may appear just after the transport's launch timeout.
            # Inspect that launch once; never start another process to find it.
            hwnd = await self._recover_window(profile_id)
            if hwnd is None:
                raise
        self._launch_markers.pop(profile_id, None)
        return hwnd

    async def _check_ready_window(self, profile, browser):
        """Return True to keep/hold this profile, False to rebuild a lost window."""
        check = getattr(self.transport, 'window_alive', None)
        hwnd = self.windows.get(profile.id)
        try:
            alive = hwnd is not None and (check is None or await check(hwnd))
            if alive:
                if self._states.get(profile.id) == 'health_unknown':
                    self.participants.extend(self._suspended_participants.pop(profile.id, []))
                    self._states[profile.id] = 'ready'
                    self.failures.pop(profile.id, None)
                return True
        except Exception as error:
            self._states[profile.id] = 'health_unknown'
            identities = {profile.id + ':chatgpt', profile.id + ':gemini'}
            suspended = [client for client in self.participants if client.id in identities]
            if suspended:
                self._suspended_participants[profile.id] = suspended
                self.participants[:] = [client for client in self.participants if client.id not in identities]
            self.failures[profile.id] = f'Window health could not be checked: {type(error).__name__}: {error}'
            self._record_recovery(profile.id, 'health_unknown', self.failures[profile.id])
            self.progress(self.failures[profile.id])
            return True
        self._discard_participants(profile.id)
        self._states[profile.id] = 'failed'
        self._record_recovery(profile.id, 'window_lost', 'Owned window closed or changed identity; rebuilding its tabs.')
        return False

    async def start(self):
        """Open each unique profile once and retry only after confirmed cleanup.

        Calling start again preserves healthy participants and retries failed
        setup. Lost owned windows are rebuilt, and uncertain launches are only
        inspected for their original marker, never replayed.
        """
        async with self._lifecycle_lock:
            if self.inventory is None:
                self.inventory = discover_browsers(managed_profile=self.root / 'data/browser-profile')
            installations, profiles, warnings = self._inventory_entries()
            if self.leader_enabled and self.leader_mode == 'chrome-profile':
                selected = managed_leader_profile(self.inventory, self.root / 'data/browser-profile')
                self.leader_profile_id = selected.id if selected else None
                profiles.sort(key=lambda profile: profile.id != self.leader_profile_id)
            self.progress(f'Found {len(installations)} browsers and {len(profiles)} profiles.')
            eligible_profiles = []
            for profile in profiles:
                if all(profile.id + ':' + name in self.excluded_participants for name in ('chatgpt', 'gemini')):
                    self._states[profile.id] = 'excluded_unsigned'
                    self.progress(f'Skipping signed-out profile: {profile.name}')
                else:
                    eligible_profiles.append(profile)
            profiles = eligible_profiles
            for warning in warnings:
                self.progress('Browser discovery: ' + warning)
            try:
                await self._start_leader()
                if profiles and self.transport is None:
                    self.transport = NativeConsoleTransport()
                for profile in profiles:
                    browser = installations.get(profile.browser_id)
                    if browser is None:
                        self._states[profile.id] = 'invalid'
                        self.failures[profile.id] = (
                            'Profile references an unavailable browser installation; rediscover installed browsers.')
                        self.progress(f'Profile {profile.name} unavailable: {self.failures[profile.id]}')
                        continue
                    if self._states.get(profile.id) in ('ready', 'health_unknown'):
                        if await self._check_ready_window(profile, browser):
                            continue
                    recovered_hwnd = None
                    if self._states.get(profile.id) == 'launch_uncertain':
                        recovered_hwnd = await self._recover_window(profile.id)
                        if recovered_hwnd is None:
                            continue
                    # A previous failed close must finish before launching again.
                    if (recovered_hwnd is None and profile.id in self.windows
                            and not await self._cleanup_window(profile.id)):
                        continue
                    for attempt in range(self.max_launch_attempts):
                        marker = 'Brainless-Team-' + uuid.uuid4().hex
                        marker_url = 'data:text/html,' + quote(
                            '<!doctype html><title>' + marker + '</title><p>Browser team starting</p>', safe='')
                        stage = 'validate'
                        try:
                            if recovered_hwnd is None:
                                arguments = profile_launch_arguments(browser, profile, [marker_url])
                                stage = 'launch'
                                self._states[profile.id] = 'starting'
                                self._attempts[profile.id] = self._attempts.get(profile.id, 0) + 1
                                hwnd = await self._launch_window(profile.id, arguments, marker)
                            else:
                                hwnd, recovered_hwnd = recovered_hwnd, None
                            stage = 'navigation'
                            names = [name for name in ('chatgpt', 'gemini')
                                     if profile.id + ':' + name not in self.excluded_participants]
                            for index, name in enumerate(names, 1):
                                url = 'https://chatgpt.com/' if name == 'chatgpt' else 'https://gemini.google.com/app'
                                if index == 1:
                                    await self.transport.navigate(hwnd, url, tab_index=1)
                                else:
                                    await self.transport.navigate(hwnd, url, new_tab=True)
                            self._publish_clients(profile, browser, hwnd)
                            self.progress(f'Opened {browser.name} / {profile.name}: ' + ' + '.join(names))
                            break
                        except Exception as error:
                            message = f'{stage}: {type(error).__name__}: {error}'
                            safe_launch_retry = (stage == 'launch' and isinstance(error, NativeLaunchError)
                                                 and not error.launched)
                            if stage == 'launch' and not safe_launch_retry:
                                self._states[profile.id] = 'launch_uncertain'
                                message += ('. Window creation could not be confirmed; inspect this profile '
                                            'manually before starting a new fleet. Launch will not be repeated.')
                            else:
                                self._states[profile.id] = 'invalid' if stage == 'validate' else 'failed'
                            self.failures[profile.id] = message
                            self._record_recovery(profile.id, self._states[profile.id], message)
                            self.progress(f'Profile {browser.name} / {profile.name} unavailable: {message}')
                            if stage == 'validate' or (stage == 'launch' and not safe_launch_retry):
                                break
                            if not await self._cleanup_window(profile.id):
                                break
                            if attempt + 1 < self.max_launch_attempts:
                                self.progress(f'Retrying {browser.name} / {profile.name} after confirmed safe cleanup.')
                                await asyncio.sleep(self.retry_delay)
            except asyncio.CancelledError:
                cleanup, _ = await _finish_owned_operation(self._close_locked())
                cleanup.result()
                raise
            if self.leader_profile_id and self.leader_profile_id in self.failures:
                self._leader_state = self._states.get(self.leader_profile_id, 'failed')
            return self.participants

    async def _close_locked(self):
        try:
            for client in self._browser_clients:
                await client.close()
            self._browser_clients.clear()
            await self.close_leader()
        finally:
            for profile_id in list(self.windows):
                if await self._cleanup_window(profile_id, clear_failure=True):
                    self._states[profile_id] = 'closed'

    async def close(self):
        """Close only owned windows, retaining failed cleanup for a later retry."""
        async with self._lifecycle_lock:
            cleanup, cancellation = await _finish_owned_operation(self._close_locked())
            try:
                cleanup.result()
            finally:
                if cancellation is not None:
                    raise cancellation
