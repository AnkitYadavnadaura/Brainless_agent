import asyncio
import json
import re
import threading
import time
from types import SimpleNamespace

import pytest

from app.browser.native_console import (
    NativeConsoleIntervention,
    NativeConsoleTransport,
    NativeLaunchError,
    NativeTransportError,
    WindowsDesktopBackend,
    _console_accessible,
    _accessible_page,
    _marker_title,
)


MARKER = "brainless-fleet-0123456789abcdef"


@pytest.mark.parametrize('provider,label', [('chatgpt', 'Chat with ChatGPT'), ('gemini', 'Enter a prompt for Gemini')])
def test_current_website_accessible_composer_labels_are_recognized(provider, label):
    snapshot = {'nodes': [{'id': 1, 'name': label, 'type': 'ControlType.Edit', 'enabled': True,
                           'offscreen': False, 'value': ''}]}
    state = _accessible_page(snapshot, provider)
    assert state['ready'] and state['composer']['name'] == label


@pytest.mark.parametrize('hit,covered,changed,expected', [
    (2, False, False, True), (1, False, False, False), (20, False, False, False),
    (2, True, False, False), (2, False, True, False)])
def test_focus_click_requires_inert_visible_caption_and_original_identity(hit, covered, changed, expected):
    backend = WindowsDesktopBackend.__new__(WindowsDesktopBackend)
    clicks = []
    def rectangle(hwnd, pointer):
        pointer._obj.left, pointer._obj.top = 0, 0
        pointer._obj.right, pointer._obj.bottom = 1000, 800
        return 1
    def hit_test(*args):
        args[-1]._obj.value = hit
        return 1
    backend.user32 = SimpleNamespace(GetWindowRect=rectangle, SendMessageTimeoutW=hit_test)
    backend.identity = lambda hwnd: (201 if changed else 200, 'browser')
    backend.point_in_window = lambda *args: not covered
    backend.click = lambda x, y: clicks.append((x, y))
    backend._focus_caption(101, (200, 'browser'))
    assert bool(clicks) is expected
    assert len(clicks) <= 1


def test_focus_restores_non_topmost_state_if_caption_activation_fails(monkeypatch):
    backend = WindowsDesktopBackend.__new__(WindowsDesktopBackend)
    order = []
    backend.user32 = SimpleNamespace(ShowWindow=lambda *args: None, SetForegroundWindow=lambda hwnd: 0,
        GetWindowLongW=lambda *args: 0, SetWindowPos=lambda hwnd, target, *args: order.append(target))
    backend.foreground = lambda: 7
    backend.identity = lambda hwnd: (200, 'browser')
    def failed(*args):
        raise RuntimeError('Activation failed')
    backend._focus_caption = failed
    monkeypatch.setattr('app.browser.native_console.subprocess.run', lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError):
        backend.focus(101)
    assert order == [-1, -2]


def test_focus_waits_for_foreground_activation_before_returning(monkeypatch):
    backend = WindowsDesktopBackend.__new__(WindowsDesktopBackend)
    state = {"foreground": 7, "checks": 0, "fallback": 0}
    backend.user32 = SimpleNamespace(
        ShowWindow=lambda *args: None,
        SetForegroundWindow=lambda hwnd: 1,
    )
    backend.identity = lambda hwnd: (200, "browser")

    def foreground():
        state["checks"] += 1
        if state["checks"] >= 2:
            state["foreground"] = 101
        return state["foreground"]

    backend.foreground = foreground
    monkeypatch.setattr(
        "app.browser.native_console.subprocess.run",
        lambda *args, **kwargs: state.update(fallback=state["fallback"] + 1),
    )

    backend.focus(101)

    assert state["foreground"] == 101
    assert state["fallback"] == 0


def test_focus_attaches_input_to_foreground_and_browser_threads_when_windows_denies_focus():
    backend = WindowsDesktopBackend.__new__(WindowsDesktopBackend)
    state = {"foreground": 7, "attached": set(), "calls": []}

    def attach(source, target, attach):
        if attach:
            state["attached"].add((source, target))
        else:
            state["attached"].discard((source, target))
        return True

    backend.user32 = SimpleNamespace(
        ShowWindow=lambda *args: None,
        SetForegroundWindow=lambda hwnd: (
            state.update(foreground=hwnd) if state["attached"] else None
        ),
        BringWindowToTop=lambda hwnd: state["calls"].append(("bring", hwnd)),
        GetWindowThreadProcessId=lambda hwnd, _pid: {7: 70, 101: 1010}[hwnd],
        AttachThreadInput=attach,
    )
    backend.kernel32 = SimpleNamespace(GetCurrentThreadId=lambda: 500)
    backend.identity = lambda hwnd: (200, "browser")
    backend.foreground = lambda: state["foreground"]
    backend._wait_for_foreground = lambda hwnd, identity, timeout=0.75: (
        state["foreground"] == hwnd
    )

    assert backend._activate_with_attached_input(101, (200, "browser"))
    assert state["calls"] == [("bring", 101)]
    assert state["attached"] == set()


class Desktop:
    def __init__(self):
        self.titles = {7: "Personal mail - Google Chrome"}
        self.current = 7
        self.clipboard = "private previous clipboard"
        self.trace = []
        self.ready = True
        self.respond = True
        self.result = {"text": "completed", "count": 2}
        self.foreign_clipboard = None
        self.steal_after = None
        self.next_hwnd = 100
        self.focus_works = True
        self.spawn_existing_only = False
        self.identity_changed = False

    def windows(self):
        return self.titles.copy()

    def spawn(self, argv):
        self.trace.append(("spawn", tuple(argv)))
        if not self.spawn_existing_only:
            self.titles[self.next_hwnd] = MARKER + " - Google Chrome"
            self.next_hwnd += 1

    def identity(self, hwnd):
        return (200 if not self.identity_changed else 201, "browser") if hwnd in self.titles else None

    def focus(self, hwnd):
        self.trace.append(("focus", hwnd))
        if self.focus_works:
            self.current = hwnd

    def foreground(self):
        return self.current

    def hotkey(self, *keys):
        self.trace.append(("keys", self.current, keys))
        if keys == ("enter",) and "__fleet_nonce=" in self.clipboard:
            if self.respond:
                nonce = re.search(r'__fleet_nonce="([a-f0-9]+)"', self.clipboard).group(1)
                self.clipboard = json.dumps({"brainless_nonce": nonce, "ok": True, "value": self.result})
            if self.foreign_clipboard is not None:
                self.clipboard = self.foreign_clipboard
        if keys == self.steal_after:
            self.current = 7

    def console_ready(self, hwnd, family):
        self.trace.append(("ready", hwnd, family))
        return self.ready

    def clipboard_read(self):
        return self.clipboard

    def clipboard_write(self, value):
        self.clipboard = value
        self.trace.append(("clipboard_write",))

    def point_in_window(self, hwnd, x, y):
        return 0 <= x < 800 and 0 <= y < 600

    def click(self, x, y):
        self.trace.append(("click", self.current, x, y))

    def close(self, hwnd):
        self.trace.append(("close", hwnd))
        self.titles.pop(hwnd)


def transport(backend=None):
    return NativeConsoleTransport(backend or Desktop(), launch_timeout=0.02,
                                  result_timeout=0.02, settle_seconds=0, poll_seconds=0.001)


async def owned(t):
    return await t.launch(["browser.exe", "--new-window", "data:text/html,marker"], MARKER)


@pytest.mark.asyncio
async def test_gmail_navigation_and_owned_operation_use_only_a_claimed_window():
    t = transport()
    hwnd = await owned(t)
    navigations = []
    t._navigate = lambda *arguments: navigations.append(arguments)

    await t.navigate_gmail(hwnd)
    result = await t.run_owned_operation(hwnd, lambda target, value: (target, value), "safe")

    assert navigations == [(hwnd, "https://mail.google.com/", False, None)]
    assert result == (hwnd, "safe")
    assert t.backend.current == hwnd
    with pytest.raises(NativeTransportError, match="no longer an owned"):
        await t.run_owned_operation(999, lambda *_: None)


@pytest.mark.asyncio
async def test_launch_adopts_only_new_exact_marker_and_close_preserves_personal_windows():
    t = transport()
    t.backend.titles[8] = MARKER + " - Google Chrome"
    hwnd = await owned(t)
    assert hwnd == 100
    assert t.backend.current == 7
    await t.close(hwnd)
    assert set(t.backend.titles) == {7, 8}
    with pytest.raises(NativeTransportError, match="owned"):
        await t.close(7)


@pytest.mark.asyncio
async def test_launch_never_adopts_existing_window_even_with_matching_title():
    t = transport()
    t.backend.titles[7] = MARKER + " - Google Chrome"
    t.backend.spawn_existing_only = True
    with pytest.raises(NativeTransportError, match="not identified"):
        await owned(t)
    assert not t._owned
    assert not any(row[0] == "focus" for row in t.backend.trace)


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', ['before_spawn', 'spawn'])
async def test_failed_launch_without_process_can_be_retried(stage):
    t = transport()
    windows, spawn = t.backend.windows, t.backend.spawn

    def fail(*args):
        raise OSError('Unavailable desktop' if stage == 'before_spawn' else 'Executable not found')

    setattr(t.backend, 'windows' if stage == 'before_spawn' else 'spawn', fail)
    with pytest.raises(NativeLaunchError) as failure:
        await owned(t)
    assert failure.value.launched is False
    assert failure.value.submitted is False
    assert not t._pending_launches and not t._owned
    assert t.backend.trace == []
    t.backend.windows, t.backend.spawn = windows, spawn
    assert await owned(t) == 100


@pytest.mark.asyncio
async def test_late_launch_recovery_uses_one_read_only_probe_and_original_window_set():
    t = transport()
    t.backend.titles[8] = MARKER + ' - Google Chrome'
    t.backend.spawn_existing_only = True
    with pytest.raises(NativeLaunchError) as failure:
        await owned(t)
    assert failure.value.launched is True
    assert await t.recover_launch(MARKER) is None
    t.backend.titles[100] = MARKER + ' - Google Chrome'
    before = t.backend.trace.copy()
    snapshots = []

    def windows():
        snapshots.append(True)
        return t.backend.titles.copy()

    t.backend.windows = windows
    assert await t.recover_launch(MARKER) == 100
    assert len(snapshots) == 1
    assert t.backend.trace == before and t.backend.current == 7
    assert set(t._owned) == {100}
    t.backend.titles[101] = MARKER + ' - Google Chrome'
    assert await t.recover_launch(MARKER) is None
    assert len(snapshots) == 1
    assert set(t._owned) == {100}


@pytest.mark.asyncio
async def test_uncertain_spawn_keeps_evidence_and_prevents_duplicate_launch():
    t = transport()
    spawn = t.backend.spawn

    def uncertain_spawn(argv):
        spawn(argv)
        raise RuntimeError('Process started but adapter acknowledgement failed')

    t.backend.spawn = uncertain_spawn
    with pytest.raises(NativeLaunchError) as failure:
        await owned(t)
    assert failure.value.launched is True
    with pytest.raises(NativeLaunchError, match='unresolved'):
        await owned(t)
    assert sum(row[0] == 'spawn' for row in t.backend.trace) == 1
    assert await t.recover_launch(MARKER) == 100


@pytest.mark.asyncio
async def test_post_spawn_inspection_failure_does_not_permit_relaunch():
    t = transport()
    windows = t.backend.windows

    def fail_after_spawn():
        if t.backend.trace:
            raise OSError('Inspection failed after process launch')
        return windows()

    t.backend.windows = fail_after_spawn
    with pytest.raises(NativeLaunchError) as failure:
        await owned(t)
    assert failure.value.launched is True
    assert MARKER in t._pending_launches
    with pytest.raises(OSError):
        await t.recover_launch(MARKER)
    assert MARKER in t._pending_launches
    t.backend.windows = windows
    assert await t.recover_launch(MARKER) == 100


@pytest.mark.asyncio
async def test_ambiguous_launch_retains_evidence_until_exactly_one_new_marker_remains():
    t = transport()
    spawn = t.backend.spawn

    def ambiguous_spawn(argv):
        spawn(argv)
        t.backend.titles[101] = MARKER + ' - Google Chrome'

    t.backend.spawn = ambiguous_spawn
    with pytest.raises(NativeLaunchError, match='Multiple'):
        await owned(t)
    trace = t.backend.trace.copy()
    assert await t.recover_launch(MARKER) is None
    assert not t._owned and MARKER in t._pending_launches
    t.backend.titles[101] = MARKER + ' - personal page - Google Chrome'
    assert await t.recover_launch(MARKER) == 100
    assert t.backend.trace == trace
    assert set(t.backend.titles) == {7, 100, 101}


@pytest.mark.asyncio
@pytest.mark.parametrize('invalid_identity', [None, (0, 'browser'), (200, ''), (True, 'browser'), (200,), 'browser'])
async def test_late_launch_does_not_adopt_unverified_window_identity(invalid_identity):
    t = transport()
    t.backend.spawn_existing_only = True
    with pytest.raises(NativeLaunchError):
        await owned(t)
    t.backend.titles[100] = MARKER
    identity = t.backend.identity
    t.backend.identity = lambda hwnd: invalid_identity
    assert await t.recover_launch(MARKER) is None
    assert not t._owned and MARKER in t._pending_launches
    t.backend.identity = identity
    assert await t.recover_launch(MARKER) == 100


@pytest.mark.asyncio
@pytest.mark.parametrize('state', ['alive', 'closed', 'reused'])
async def test_window_health_is_read_only_and_retains_cleanup_ownership(state):
    t = transport()
    hwnd = await owned(t)
    if state == 'closed':
        t.backend.titles.pop(hwnd)
    elif state == 'reused':
        t.backend.identity_changed = True
    trace = t.backend.trace.copy()
    assert await t.window_alive(hwnd) is (state == 'alive')
    assert await t.window_alive(7) is False
    assert hwnd in t._owned
    assert t.backend.trace == trace
    await t.close(hwnd)
    assert hwnd not in t._owned
    if state != 'alive':
        assert t.backend.trace == trace


@pytest.mark.asyncio
async def test_window_health_propagates_inspection_error_without_losing_ownership():
    t = transport()
    hwnd = await owned(t)

    def unavailable(hwnd):
        raise OSError('Cannot inspect window')

    t.backend.identity = unavailable
    trace = t.backend.trace.copy()
    with pytest.raises(OSError, match='Cannot inspect'):
        await t.window_alive(hwnd)
    assert hwnd in t._owned and t.backend.trace == trace


@pytest.mark.parametrize('option', ['launch_timeout', 'result_timeout', 'settle_seconds', 'poll_seconds'])
@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf'), -0.1, True, '1', 10 ** 1000])
def test_native_operation_budgets_reject_unbounded_or_invalid_values(option, value):
    with pytest.raises(ValueError, match=option):
        NativeConsoleTransport(Desktop(), **{option: value})


@pytest.mark.parametrize('option', ['launch_timeout', 'result_timeout', 'poll_seconds'])
def test_native_operation_deadlines_and_poll_interval_must_be_positive(option):
    with pytest.raises(ValueError, match=option):
        NativeConsoleTransport(Desktop(), **{option: 0})


@pytest.mark.asyncio
async def test_close_retains_ownership_until_window_actually_disappears():
    t = transport()
    hwnd = await owned(t)
    close = t.backend.close
    t.backend.close = lambda handle: None  # e.g. a before-unload dialog
    with pytest.raises(NativeTransportError, match='did not close'):
        await t.close(hwnd)
    assert hwnd in t._owned and hwnd in t.backend.titles
    t.backend.close = close
    await t.close(hwnd)
    assert hwnd not in t._owned


@pytest.mark.asyncio
async def test_close_of_already_closed_or_reused_window_never_targets_new_owner():
    t = transport()
    hwnd = await owned(t)
    t.backend.identity_changed = True
    await t.close(hwnd)
    assert hwnd not in t._owned
    assert not any(row[0] == 'close' for row in t.backend.trace)


@pytest.mark.parametrize("title,expected", [
    (MARKER, True), (MARKER + " - Google Chrome", True),
    (MARKER + " — Mozilla Firefox", True),
    ("prefix " + MARKER + " - Google Chrome", False),
    (MARKER + "different - Google Chrome", False),
    (MARKER + " - unrelated page - Google Chrome", False),
    (MARKER + " - Text Editor", False),
])
def test_marker_title_is_not_a_substring_match(title, expected):
    assert _marker_title(title, MARKER) is expected


@pytest.mark.parametrize('profile', ['Profile 1', 'Profile 2', 'Personal 2', 'Work - Team'])
def test_edge_profile_title_and_invisible_brand_character_are_recognized(profile):
    title = MARKER + ' - ' + profile + ' - Microsoft\u200b Edge'
    assert _marker_title(title, MARKER)
    assert not _marker_title('other ' + title, MARKER)
    assert not _marker_title(title.replace(MARKER, MARKER + 'suffix'), MARKER)


@pytest.mark.parametrize('sep1,sep2', [
    (' - ', ' — '), (' — ', ' - '), (' \u2013 ', ' — '), (' — ', ' \u2013 ')
])
def test_edge_profile_title_mixed_separators_are_recognized(sep1, sep2):
    title = MARKER + sep1 + 'Profile 1' + sep2 + 'Microsoft\u200b Edge'
    assert _marker_title(title, MARKER)
    assert not _marker_title('other ' + title, MARKER)


@pytest.mark.asyncio
async def test_uncertain_console_tab_does_not_quarantine_its_sibling():
    t = transport()
    hwnd = await owned(t)
    t.backend.respond = False
    with pytest.raises(NativeConsoleIntervention):
        await t.evaluate(hwnd, 'chromium', '({ok:true})', tab_index=1)
    assert t._is_uncertain(hwnd, 1) and not t._is_uncertain(hwnd, 2)
    t.backend.respond = True
    await t.navigate(hwnd, 'https://gemini.google.com/app', tab_index=2)
    assert await t.evaluate(hwnd, 'chromium', '({ok:true})', tab_index=2) == t.backend.result
    trace = list(t.backend.trace)
    with pytest.raises(NativeConsoleIntervention):
        await t.navigate(hwnd, 'https://chatgpt.com/', tab_index=1)
    assert t.backend.trace == trace
    await t.close(hwnd)
    assert not t._uncertain_tabs


@pytest.mark.asyncio
async def test_evaluate_selects_tab_atomically_and_restores_clipboard():
    t = transport()
    hwnd = await owned(t)
    assert await t.evaluate(hwnd, "chromium", "({count:2})", tab_index=2) == t.backend.result
    assert t.backend.clipboard == "private previous clipboard"
    keys = [row[2] for row in t.backend.trace if row[0] == "keys"]
    assert keys == [("ctrl", "2"), ("ctrl", "shift", "j"), ("ctrl", "v"), ("enter",), ("ctrl", "shift", "j")]
    assert not t._uncertain


@pytest.mark.asyncio
async def test_unverified_console_never_pastes_or_submits_any_script():
    t = transport()
    hwnd = await owned(t)
    t.backend.ready = False
    with pytest.raises(NativeConsoleIntervention, match="no script was pasted") as failure:
        await t.evaluate(hwnd, "chromium", "({ok:true})")
    assert failure.value.submitted is False
    assert not any(row[0] == "clipboard_write" for row in t.backend.trace)
    assert not any(row[0] == "keys" and row[2] in {("ctrl", "v"), ("enter",)} for row in t.backend.trace)


@pytest.mark.asyncio
async def test_timeout_pauses_without_self_xss_bypass_or_replay():
    t = transport()
    hwnd = await owned(t)
    t.backend.respond = False
    with pytest.raises(NativeConsoleIntervention, match="not be replayed") as failure:
        await t.evaluate(hwnd, "firefox", "({ok:true})")
    assert failure.value.submitted is True
    trace = t.backend.trace.copy()
    with pytest.raises(NativeConsoleIntervention, match="unknown outcome"):
        await t.evaluate(hwnd, "firefox", "({ok:true})")
    assert t.backend.trace == trace
    assert t.backend.clipboard == "private previous clipboard"
    assert sum(row[0] == "keys" and row[2] == ("enter",) for row in trace) == 1
    assert not any("allow pasting" in str(row) for row in trace)


@pytest.mark.asyncio
async def test_unrelated_clipboard_changes_are_preserved_and_nonce_must_match():
    t = transport()
    hwnd = await owned(t)
    foreign = json.dumps({"brainless_nonce": "someone-else", "ok": True, "value": {"fake": True}})
    t.backend.foreign_clipboard = foreign
    with pytest.raises(NativeConsoleIntervention):
        await t.evaluate(hwnd, "chromium", "({ok:true})")
    assert t.backend.clipboard == foreign


@pytest.mark.asyncio
async def test_focus_must_match_before_each_input_and_stops_after_paste():
    t = transport()
    hwnd = await owned(t)
    t.backend.steal_after = ("ctrl", "v")
    with pytest.raises(NativeTransportError, match="focus changed") as failure:
        await t.evaluate(hwnd, "chromium", "({ok:true})")
    assert failure.value.submitted is False
    assert not any(row[0] == "keys" and row[1] == 7 for row in t.backend.trace)
    assert not any(row[0] == "keys" and row[2] == ("enter",) for row in t.backend.trace)


@pytest.mark.asyncio
async def test_reused_handle_never_gets_focused():
    t = transport()
    hwnd = await owned(t)
    t.backend.identity_changed = True
    with pytest.raises(NativeTransportError, match="owned"):
        await t.evaluate(hwnd, "chromium", "({ok:true})")
    assert not any(row[0] == "focus" for row in t.backend.trace)


@pytest.mark.asyncio
async def test_navigation_only_provider_sites_and_owned_clicks():
    t = transport()
    hwnd = await owned(t)
    for url in ("javascript:alert(1)", "file:///secrets", "https://chatgpt.com.evil.test", "https://x:password@chatgpt.com", "https://chatgpt.com:444"):
        with pytest.raises(ValueError):
            await t.navigate(hwnd, url)
    await t.navigate(hwnd, "https://gemini.google.com/app", True, tab_index=1)
    assert t.backend.clipboard == "private previous clipboard"
    await t.click(hwnd, 50, 50)
    with pytest.raises(NativeTransportError, match="outside"):
        await t.click(hwnd, 1000, 50)
    with pytest.raises(ValueError):
        await t.hotkey(hwnd, "alt", "f4")


@pytest.mark.asyncio
async def test_global_lock_serializes_separate_transport_instances():
    entered = threading.Event()
    release = threading.Event()
    operations = []
    first, second = transport(), transport()
    def long_operation():
        operations.append("first-start")
        entered.set()
        assert release.wait(2)
        operations.append("first-end")
    task1 = asyncio.create_task(first._serialized(long_operation))
    await asyncio.to_thread(entered.wait, 1)
    task2 = asyncio.create_task(second._serialized(lambda: operations.append("second")))
    await asyncio.sleep(0.02)
    assert operations == ["first-start"]
    release.set()
    await asyncio.gather(task1, task2)
    assert operations == ["first-start", "first-end", "second"]


@pytest.mark.asyncio
async def test_cancelled_operation_finishes_before_releasing_input_lane():
    entered = threading.Event()
    release = threading.Event()
    t = transport()
    task = asyncio.create_task(t._serialized(lambda: (entered.set(), release.wait(2))))
    await asyncio.to_thread(entered.wait, 1)
    task.cancel()
    await asyncio.sleep(0.01)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['evaluate', 'close'])
@pytest.mark.parametrize('fail', [False, True])
async def test_repeated_cancellation_drains_native_operation_before_returning(operation, fail):
    t = transport()
    hwnd = await owned(t)
    entered, release, completed = threading.Event(), threading.Event(), threading.Event()
    original = t.backend.hotkey if operation == 'evaluate' else t.backend.close

    def blocked(*args):
        if operation == 'evaluate' and args != ('enter',):
            return original(*args)
        entered.set()
        try:
            assert release.wait(3), 'Test did not release the native worker'
            if fail:
                raise RuntimeError('Native acknowledgement failed')
            return original(*args)
        finally:
            completed.set()

    if operation == 'evaluate':
        t.backend.hotkey = blocked
        task = asyncio.create_task(t.evaluate(hwnd, 'chromium', '({ok:true})'))
    else:
        t.backend.close = blocked
        task = asyncio.create_task(t.close(hwnd))
    next_operation = None
    try:
        assert await asyncio.to_thread(entered.wait, 1)
        next_operation = asyncio.create_task(transport()._serialized(lambda: completed.is_set()))
        for _ in range(3):
            task.cancel()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert not task.done(), 'Cancellation returned while native input was still running'
            assert not next_operation.done()
            assert hwnd in t._owned
    finally:
        release.set()
        # Always drain test workers even when a regression assertion fails.
        await asyncio.gather(task, *([next_operation] if next_operation else []), return_exceptions=True)

    with pytest.raises(asyncio.CancelledError):
        await task
    assert completed.is_set() and await next_operation
    assert t.backend.clipboard == 'private previous clipboard'
    if operation == 'close':
        assert (hwnd in t._owned) is fail
        assert (hwnd in t.backend.titles) is fail
    else:
        assert (hwnd in t._uncertain) is fail


@pytest.mark.parametrize("items,expected", [
    ([{"name": "Console prompt", "type": "ControlType.Edit"}], True),
    ([{"name": "Console input", "type": "ControlType.Document"}], True),
    ([{"name": "Message ChatGPT", "type": "ControlType.Edit"}], False),
    ([{"name": "Address and search bar", "type": "ControlType.Edit"}], False),
    ([{"name": "Console prompt", "type": "ControlType.Button"}], False),
    ([], False),
])
def test_console_accessibility_checks_focused_control(items, expected):
    assert _console_accessible(items) is expected


def accessibility_nodes(prompt='', answer='Old answer'):
    return [
        dict(id=0, parent=-1, name='Conversation', type='ControlType.Document', runtime_id='root', enabled=True),
        dict(id=1, parent=0, name='Ask anything', type='ControlType.Edit', runtime_id='composer',
             enabled=True, rect=[20, 400, 500, 80], value=prompt),
        dict(id=2, parent=0, name='Send prompt', type='ControlType.Button', runtime_id='send',
             enabled=True, rect=[600, 420, 50, 40]),
        dict(id=3, parent=0, name='You said:', type='ControlType.Group', runtime_id='user', enabled=True),
        dict(id=4, parent=3, name='User text must not become an answer', type='ControlType.Text'),
        dict(id=5, parent=0, name='ChatGPT said:', type='ControlType.Group', runtime_id='assistant', enabled=True),
        dict(id=6, parent=5, name=answer, type='ControlType.Text'),
    ]


class AccessibleDesktop(Desktop):
    def __init__(self):
        super().__init__()
        self.page_url = 'https://chatgpt.com/'
        self.nodes = accessibility_nodes()
        self.focused_id = None
        self.covered = False
        self.fail_send = False
        self.paste_changes_focus = False
        self.ignore_paste = False

    def accessibility_snapshot(self, hwnd):
        self.trace.append(('snapshot', hwnd))
        return {'url': self.page_url, 'nodes': [dict(node) for node in self.nodes]}

    def control_at(self, hwnd, x, y, runtime_id):
        return not self.covered and runtime_id == ('send' if x > 550 else 'composer')

    def focused_control(self, hwnd, runtime_id):
        return self.focused_id == runtime_id

    def click(self, x, y):
        super().click(x, y)
        self.focused_id = 'send' if x > 550 else 'composer'
        if self.focused_id == 'send' and self.fail_send:
            raise RuntimeError('Input sent but acknowledgement failed')

    def hotkey(self, *keys):
        super().hotkey(*keys)
        if keys == ('ctrl', 'v') and not self.ignore_paste:
            self.nodes[1]['value'] = self.clipboard
        if self.paste_changes_focus and keys == ('ctrl', 'a'):
            self.focused_id = 'address'


async def native_bind(t, hwnd):
    return await t.native_action(hwnd, 'chatgpt', 'bind', owner='test-owner', tab_index=1)


def test_accessibility_extracts_explicit_assistant_group_without_user_text():
    result = _accessible_page({'url': 'https://chatgpt.com', 'nodes': accessibility_nodes()}, 'chatgpt')
    assert result['text'] == 'Old answer'
    assert result['count'] == 1 and result['ready']
    nodes = accessibility_nodes()
    nodes[5]['type'] = 'ControlType.Text'  # A prompt containing the label is not a response group.
    assert _accessible_page({'nodes': nodes}, 'chatgpt')['count'] == 0
    assert _accessible_page({'nodes': nodes, 'truncated': True}, 'chatgpt')['error'] == 'accessibility_incomplete'


@pytest.mark.asyncio
async def test_native_path_pastes_and_clicks_observed_controls_without_console():
    t = transport(AccessibleDesktop())
    hwnd = await owned(t)
    assert (await native_bind(t, hwnd))['bound']
    prompt = 'Literal data: "); window.shouldNotExecute=true; //'
    prepared = await t.native_action(hwnd, 'chatgpt', 'prepare', owner='test-owner', tab_index=1,
                                    prompt=prompt, request='request-one')
    assert prepared['prepared'] and prepared['text'] == 'Old answer'
    assert t.backend.nodes[1]['value'] == prompt
    assert t.backend.clipboard == 'private previous clipboard'
    sent = await t.native_action(hwnd, 'chatgpt', 'submit', owner='test-owner', tab_index=1, request='request-one')
    assert sent['submitted']
    assert (await t.native_action(hwnd, 'chatgpt', 'submit', owner='test-owner', tab_index=1, request='request-one'))['duplicate']
    assert sum(row[0] == 'click' and row[-2] > 550 for row in t.backend.trace) == 1
    assert not any(row[0] == 'keys' and ('shift' in row[2] or row[2] == ('enter',)) for row in t.backend.trace)


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['covered', 'paste_changes_focus', 'ignore_paste'])
async def test_native_input_does_not_send_if_control_or_content_cannot_be_verified(fault):
    t = transport(AccessibleDesktop())
    hwnd = await owned(t)
    await native_bind(t, hwnd)
    setattr(t.backend, fault, True)
    if fault == 'ignore_paste':
        result = await t.native_action(hwnd, 'chatgpt', 'prepare', owner='test-owner', tab_index=1,
                                       prompt='Prompt', request='one')
        assert result['error'] == 'input_mismatch'
    else:
        with pytest.raises(NativeTransportError):
            await t.native_action(hwnd, 'chatgpt', 'prepare', owner='test-owner', tab_index=1,
                                  prompt='Prompt', request='one')
    assert not any(row[0] == 'click' and row[-2] > 550 for row in t.backend.trace)
    assert not any(row[0] == 'keys' and row[2] == ('ctrl', 'v') for row in t.backend.trace) or fault == 'ignore_paste'
    assert t.backend.clipboard == 'private previous clipboard'


@pytest.mark.asyncio
async def test_native_unknown_send_is_latched_and_never_clicked_twice():
    t = transport(AccessibleDesktop())
    hwnd = await owned(t)
    await native_bind(t, hwnd)
    await t.native_action(hwnd, 'chatgpt', 'prepare', owner='test-owner', tab_index=1, prompt='Prompt', request='one')
    t.backend.fail_send = True
    with pytest.raises(NativeTransportError) as failure:
        await t.native_action(hwnd, 'chatgpt', 'submit', owner='test-owner', tab_index=1, request='one')
    assert failure.value.submitted is True
    t.backend.fail_send = False
    assert (await t.native_action(hwnd, 'chatgpt', 'submit', owner='test-owner', tab_index=1, request='one'))['duplicate']
    assert sum(row[0] == 'click' and row[-2] > 550 for row in t.backend.trace) == 1


@pytest.mark.asyncio
async def test_native_rechecks_provider_url_and_prompt_before_send():
    t = transport(AccessibleDesktop())
    hwnd = await owned(t)
    await native_bind(t, hwnd)
    await t.native_action(hwnd, 'chatgpt', 'prepare', owner='test-owner', tab_index=1, prompt='Prompt', request='one')
    t.backend.nodes[1]['value'] = 'Changed by owner'
    assert (await t.native_action(hwnd, 'chatgpt', 'submit', owner='test-owner', tab_index=1, request='one'))['error'] == 'input_mismatch'
    t.backend.page_url = 'https://chatgpt.com/c/different-chat'
    assert (await t.native_action(hwnd, 'chatgpt', 'submit', owner='test-owner', tab_index=1, request='one'))['error'] == 'wrong_tab'
    t.backend.page_url = 'https://chatgpt.com.evil.test/'
    assert (await t.native_action(hwnd, 'chatgpt', 'submit', owner='test-owner', tab_index=1, request='one'))['error'] == 'wrong_origin'
    assert not any(row[0] == 'click' and row[-2] > 550 for row in t.backend.trace)


@pytest.mark.asyncio
async def test_native_does_not_clear_uncertain_console_execution():
    t = transport(AccessibleDesktop())
    hwnd = await owned(t)
    t._uncertain.add(hwnd)
    with pytest.raises(NativeConsoleIntervention, match='uncertain'):
        await native_bind(t, hwnd)
    assert not any(row[0] in {'snapshot', 'click'} for row in t.backend.trace)


@pytest.mark.asyncio
async def test_semantic_composer_focus_and_send_do_not_depend_on_parent_hit_testing():
    backend = AccessibleDesktop()
    backend.covered = True  # Simulates a UIA hit test returning the containing group.
    def focus(hwnd, runtime_id):
        backend.focused_id = runtime_id
        return True
    invoked = []
    def invoke(hwnd, runtime_id):
        invoked.append(runtime_id)
        return True
    backend.focus_composer, backend.invoke_send = focus, invoke
    t = transport(backend)
    hwnd = await owned(t)
    await native_bind(t, hwnd)
    await t.native_action(hwnd, 'chatgpt', 'prepare', owner='test-owner', tab_index=1, prompt='Prompt', request='one')
    assert (await t.native_action(hwnd, 'chatgpt', 'submit', owner='test-owner', tab_index=1, request='one'))['submitted']
    assert (await t.native_action(hwnd, 'chatgpt', 'submit', owner='test-owner', tab_index=1, request='one'))['duplicate']
    assert invoked == ['send'] and not any(row[0] == 'click' for row in backend.trace)


@pytest.mark.asyncio
async def test_semantic_send_exception_retains_unknown_outcome_without_second_invocation():
    backend = AccessibleDesktop()
    def invoke(hwnd, runtime_id):
        raise NativeTransportError('Invoke acknowledgement lost')
    backend.invoke_send = invoke
    t = transport(backend)
    hwnd = await owned(t)
    await native_bind(t, hwnd)
    await t.native_action(hwnd, 'chatgpt', 'prepare', owner='test-owner', tab_index=1, prompt='Prompt', request='one')
    with pytest.raises(NativeTransportError) as failure:
        await t.native_action(hwnd, 'chatgpt', 'submit', owner='test-owner', tab_index=1, request='one')
    assert failure.value.submitted is True
    assert (await t.native_action(hwnd, 'chatgpt', 'submit', owner='test-owner', tab_index=1, request='one'))['duplicate']


@pytest.mark.asyncio
async def test_chatgpt_temporary_url_becomes_pinned_canonical_conversation():
    t = transport(AccessibleDesktop())
    hwnd = await owned(t)
    await native_bind(t, hwnd)
    await t.native_action(hwnd, 'chatgpt', 'prepare', owner='test-owner', tab_index=1, prompt='Prompt', request='one')
    await t.native_action(hwnd, 'chatgpt', 'submit', owner='test-owner', tab_index=1, request='one')
    temporary = 'https://chatgpt.com/c/WEB:12345678-1234-1234-1234-123456789abc'
    canonical = 'https://chatgpt.com/c/87654321-1234-1234-1234-123456789abc'
    for url in (temporary, canonical, canonical + '?model=auto'):
        t.backend.page_url = url
        assert 'error' not in await t.native_action(hwnd, 'chatgpt', 'observe', owner='test-owner', tab_index=1)
    t.backend.page_url = 'https://chatgpt.com/c/22222222-1234-1234-1234-123456789abc'
    assert (await t.native_action(hwnd, 'chatgpt', 'observe', owner='test-owner', tab_index=1))['error'] == 'wrong_tab'


def test_anonymous_composer_with_visible_login_button_is_not_ready():
    nodes = accessibility_nodes()
    nodes.append(dict(id=7, parent=0, name='Log in', type='ControlType.Button', enabled=True))
    assert _accessible_page({'nodes': nodes}, 'chatgpt')['error'] == 'login'


def test_repair_prompt_mentioning_captcha_is_not_a_challenge():
    nodes = accessibility_nodes()
    nodes.append(dict(id=7, parent=0, name='Diagnose failures without bypassing authentication, CAPTCHA or permissions.',
                      type='ControlType.Text'))
    assert _accessible_page({'nodes': nodes}, 'chatgpt')['ready']
    nodes[-1]['name'] = 'Verify you are human.'
    assert _accessible_page({'nodes': nodes}, 'chatgpt')['error'] == 'challenge'


def test_current_chatgpt_answer_group_requires_adjacent_response_action_controls():
    nodes = accessibility_nodes()
    nodes[5]['name'] = 'Answer body'
    nodes.extend([
        dict(id=7, parent=0, name='Response actions', type='ControlType.Group'),
        dict(id=8, parent=7, name='Copy response', type='ControlType.Button'),
        dict(id=9, parent=7, name='Rate response', type='ControlType.Button')])
    result = _accessible_page({'nodes': nodes}, 'chatgpt')
    assert result['text'] == 'Old answer' and result['count'] == 1
    nodes.pop()  # A user message mentioning response actions isn't an assistant turn.
    assert _accessible_page({'nodes': nodes}, 'chatgpt')['count'] == 0


def test_gemini_accessibility_only_author_label_requires_own_feedback_controls():
    nodes = [
        dict(id=0, parent=-1, name='', type='ControlType.Group'),
        dict(id=1, parent=0, name='', type='ControlType.Group'),
        dict(id=2, parent=1, name='', type='ControlType.Group'),
        dict(id=3, parent=1, name='', type='ControlType.Group'),
        dict(id=4, parent=2, name='Gemini said', type='ControlType.Text', offscreen=True),
        dict(id=5, parent=3, name='Actual answer', type='ControlType.Text'),
        dict(id=6, parent=0, name='Good response', type='ControlType.Button'),
        dict(id=7, parent=0, name='Bad response', type='ControlType.Button'),
        dict(id=8, parent=-1, name='User message must not become an answer', type='ControlType.Text')]
    result = _accessible_page({'nodes': nodes}, 'gemini')
    assert result['count'] == 1 and result['text'] == 'Actual answer'
    nodes[4]['offscreen'] = False
    assert _accessible_page({'nodes': nodes}, 'gemini')['count'] == 0
    nodes[4]['offscreen'] = True
    nodes[7]['parent'] = -1  # Feedback from a different turn cannot authenticate this one.
    assert _accessible_page({'nodes': nodes}, 'gemini')['count'] == 0


def test_long_reply_keeps_offscreen_text_in_nested_reading_order():
    nodes = accessibility_nodes()
    nodes[5]['offscreen'] = True
    nodes[6].update(name='{', offscreen=True)
    nodes.extend([
        dict(id=7, parent=5, name='', type='ControlType.Group', offscreen=True),
        dict(id=8, parent=5, name='}', type='ControlType.Text'),
        dict(id=9, parent=7, name='"part": "terrain"', type='ControlType.Text', offscreen=True)])
    result = _accessible_page({'nodes': nodes}, 'chatgpt')
    assert result['count'] == 1
    assert json.loads(result['text']) == {'part': 'terrain'}


def test_current_chatgpt_scrolled_reply_footer_still_identifies_answer():
    nodes = accessibility_nodes()
    nodes[5].update(name='Answer body', offscreen=True)
    nodes[6]['offscreen'] = True
    nodes.extend([
        dict(id=7, parent=0, name='Response actions', type='ControlType.Group', offscreen=True),
        dict(id=8, parent=7, name='Copy response', type='ControlType.Button', offscreen=True),
        dict(id=9, parent=7, name='Rate response', type='ControlType.Button', offscreen=True)])
    result = _accessible_page({'nodes': nodes}, 'chatgpt')
    assert result['count'] == 1 and result['text'] == 'Old answer'


def test_chatgpt_flattened_history_does_not_hide_a_new_turn():
    nodes = accessibility_nodes()[:5]
    nodes.extend([
        dict(id=5, parent=0, name='Old answer', type='ControlType.Text', offscreen=True),
        dict(id=6, parent=0, name='Response actions', type='ControlType.Group', offscreen=True),
        dict(id=7, parent=0, name='', type='ControlType.Group'),
        dict(id=8, parent=0, name='Response actions', type='ControlType.Group'),
        dict(id=9, parent=6, name='Copy response', type='ControlType.Button', offscreen=True),
        dict(id=10, parent=6, name='Rate response', type='ControlType.Button', offscreen=True),
        dict(id=11, parent=7, name='New answer', type='ControlType.Text'),
        dict(id=12, parent=8, name='Copy response', type='ControlType.Button'),
        dict(id=13, parent=8, name='Rate response', type='ControlType.Button')])
    result = _accessible_page({'nodes': nodes}, 'chatgpt')
    assert result['count'] == 2 and result['text'] == 'New answer'
    result = _accessible_page({'nodes': [n for n in nodes if n['id'] not in {7, 8, 11, 12, 13}]}, 'chatgpt')
    assert result['count'] == 1 and result['text'] == 'Old answer'


@pytest.mark.asyncio
@pytest.mark.parametrize('focused,value', [(False, ''), (True, 'wrong URL')])
async def test_navigation_requires_address_focus_and_exact_url_before_enter(focused, value):
    backend = Desktop()
    backend.address_bar = lambda hwnd: {'owned': True, 'address_focused': focused, 'address_value': value}
    t = transport(backend)
    hwnd = await owned(t)
    with pytest.raises(NativeTransportError, match='Address bar'):
        await t.navigate(hwnd, 'https://chatgpt.com/c/saved', tab_index=1)
    assert not any(row[0] == 'keys' and row[2] == ('enter',) for row in backend.trace)
    assert backend.clipboard == 'private previous clipboard'


@pytest.mark.asyncio
async def test_copy_response_preserves_json_escaping_and_restores_clipboard():
    backend = AccessibleDesktop()
    backend.nodes[5]['name'] = 'Answer'
    backend.nodes.extend([
        dict(id=7, parent=0, name='Response actions', type='ControlType.Group'),
        dict(id=8, parent=7, name='Copy response', type='ControlType.Button', runtime_id='answer-copy'),
        dict(id=9, parent=7, name='Rate response', type='ControlType.Button')])
    raw = '```json\n' + json.dumps({'name': 'The "quoted" building'}) + '\n```'
    def copy(hwnd, runtime_id):
        assert runtime_id == 'answer-copy'
        backend.clipboard = raw
        return True
    backend.copy_response = copy
    t = transport(backend)
    hwnd = await owned(t)
    await native_bind(t, hwnd)
    state = await t.native_action(hwnd, 'chatgpt', 'read_response', owner='test-owner', tab_index=1)
    assert state['text'] == raw and state['copied_response']
    assert backend.clipboard == 'private previous clipboard'
    assert not any(row[0] == 'keys' and row[2] == ('enter',) for row in backend.trace)


@pytest.mark.asyncio
@pytest.mark.parametrize('matches', [True, False])
async def test_response_correlation_requires_exact_copy_message_hash(matches):
    import hashlib
    backend = AccessibleDesktop()
    backend.nodes[4]['id'] = 7
    backend.nodes.extend([
        dict(id=4, parent=0, name='Your message actions', type='ControlType.Group'),
        dict(id=8, parent=4, name='Copy message', type='ControlType.Button', runtime_id='copy-user'),
        dict(id=9, parent=4, name='Edit message', type='ControlType.Button')])
    prompt = 'Exact original request'
    def copy(hwnd, runtime_id):
        assert runtime_id == 'copy-user'
        backend.clipboard = prompt if matches else 'Different request'
        return True
    backend.copy_message = copy
    t = transport(backend)
    hwnd = await owned(t)
    await native_bind(t, hwnd)
    result = await t.native_action(hwnd, 'chatgpt', 'read_response', owner='test-owner', tab_index=1,
                                   prompt_hash=hashlib.sha256(prompt.encode()).hexdigest())
    assert result['request_verified'] is matches
    assert backend.clipboard == 'private previous clipboard'
    assert not any(row[0] == 'keys' and row[2] == ('enter',) for row in backend.trace)
