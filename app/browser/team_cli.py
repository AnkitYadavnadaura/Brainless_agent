"""Command-line composition for installed-profile website collaboration."""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
import uuid

from app.browser.fleet_discovery import BrowserInventory, discover_browsers, managed_leader_profile


def _wait_seconds(value):
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1800:
        raise argparse.ArgumentTypeError('wait-ready must be between 0 and 1800 seconds')
    return number


def _timeout(value):
    number = float(value)
    if not math.isfinite(number) or not 30 <= number <= 900:
        raise argparse.ArgumentTypeError('timeout must be between 30 and 900 seconds')
    return number


def parser():
    result = argparse.ArgumentParser(prog='python run.py browser-team',
        description='Use installed browser profiles as a ChatGPT + Gemini website team.')
    commands = result.add_subparsers(dest='command', required=True)
    inventory = commands.add_parser('inventory', help='Count browsers and profiles without opening them')
    inventory.add_argument('--json', action='store_true', help='Print structured inventory')
    opened = commands.add_parser('open', help='Open ChatGPT and Gemini in every discovered profile')
    status = commands.add_parser('status', help='Read saved team progress without opening browsers')
    status.add_argument('--session', help='Filter to a named task session')
    board = commands.add_parser('board', help='Read the latest shared task board')
    board.add_argument('--session', required=True)
    message = commands.add_parser('message', help='Tag a participant on the active board for its next turn')
    message.add_argument('--session', required=True)
    message.add_argument('--to', required=True, help='Exact participant ID, or * for all')
    message.add_argument('text')
    recover = commands.add_parser('recover', help='Read outstanding replies from saved chats without resending')
    recover.add_argument('--session', required=True, help='Session shown by the status command')
    recover.add_argument('--timeout', type=_timeout, default=180)
    recover.add_argument('--setup', action='store_true', help='Wait for manual login/console setup first')
    recover.add_argument('--close-on-exit', action='store_true')
    run = commands.add_parser('run', help='Ask the team to solve a task and review one another')
    run.add_argument('task', nargs='?', help='Task text; omitted text is read from the terminal')
    run.add_argument('--session', help='Stable session name; defaults to a hash of the task')
    run.add_argument('--work-mode', choices=('parts', 'review'), default='parts',
                     help='Divide into coordinated parts (default), or independently review the whole request')
    run.add_argument('--recheck-signins', action='store_true',
                     help='Reinspect tabs previously excluded as signed out after you sign in manually')
    run.add_argument('--rounds', type=int, choices=(1, 2, 3), default=2,
                     help='Proposal/review rounds before synthesis (default: 2)')
    run.add_argument('--parallelism', type=int, choices=range(1, 17), default=4,
                     metavar='1..16', help='Concurrent website requests; desktop input stays serialized')
    run.add_argument('--timeout', type=_timeout, default=180,
                     help='Seconds per participant request (30..900; default: 180)')
    run.add_argument('--setup', action='store_true',
                     help='Wait after opening windows for manual login and developer-console setup')
    execution = run.add_mutually_exclusive_group()
    execution.add_argument('--execute', action='store_true',
                     help='Use the team in the existing capability/3D task workflow')
    execution.add_argument('--desktop', action='store_true',
                     help='Observe and act on desktop apps through the bounded team workflow')
    run.add_argument('--max-actions', type=int, choices=range(1, 51), default=12, metavar='1..50')
    run.add_argument('--max-minutes', type=int, choices=range(1, 31), default=10, metavar='1..30')
    run.add_argument('--close-on-exit', action='store_true',
                     help='Close only windows opened by this run after work finishes')
    doctor = commands.add_parser('doctor', help='Check each provider tab without sending a task')
    doctor.add_argument('--recheck-limits', action='store_true',
                        help='Read current readiness once after a provider usage limit resets; sends no prompt')
    smoke = commands.add_parser('smoke', help='Send a harmless nonce test through both providers and verify peer exchange')
    for command in (doctor, smoke):
        command.add_argument('--timeout', type=_timeout, default=180)
        command.add_argument('--setup', action='store_true')
        command.add_argument('--close-on-exit', action='store_true')
    for command in (run, recover, doctor, smoke):
        command.add_argument('--wait-ready', type=_wait_seconds, default=0, metavar='SECONDS',
                             help='Wait a bounded time for manual login/setup, automatically rechecking readiness')
    for command in (opened, run, recover, doctor, smoke):
        command.add_argument('--leader', choices=('chrome-profile', 'chromium', 'none'), default='chrome-profile',
                             help='Use signed-in data/browser-profile Chrome (default), isolated Chromium, or no dedicated leader')
        command.add_argument('--leader-only', action='store_true',
                             help='Open only the selected leader, useful for sign-in and diagnostics')
        command.add_argument('--profile', action='append', default=[], metavar='PROFILE_ID',
                             help='Choose a discovered profile; repeat to select several (default: all)')
        command.add_argument('--input-mode', choices=('auto', 'console', 'native'), default='auto',
                             help='Prefer native accessibility/mouse input automatically, or select a path explicitly')
    return result


def inventory_snapshot(inventory):
    return dict(browser_count=len(inventory.browsers), profile_count=len(inventory.profiles),
                participant_count=2 * len(inventory.profiles),
                browsers=[asdict(item) for item in inventory.browsers],
                profiles=[asdict(item) for item in inventory.profiles], warnings=inventory.warnings)


def saved_status(path: Path, session: str | None = None):
    """Read checkpoints without creating a store or disclosing complete task text."""
    if not path.is_file():
        return {'sessions': [], 'message': 'No saved browser-team requests yet.'}
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        columns = {row['name'] for row in connection.execute('PRAGMA table_info(team_rounds)')}
        certainty = 'submitted' if 'submitted' in columns else 'NULL'
        query = 'SELECT id, updated FROM team_sessions'
        sessions = connection.execute(query + (' WHERE id=?' if session else '') +
                                      ' ORDER BY updated DESC LIMIT 20', (session,) if session else ()).fetchall()
        result = []
        for item in sessions:
            request = connection.execute('SELECT id,status,error,created,updated FROM team_requests '
                'WHERE session_id=? ORDER BY created DESC LIMIT 1', (item['id'],)).fetchone()
            rounds = []
            if request:
                rounds = [dict(row) for row in connection.execute(
                    f'SELECT member_id,provider,round,attempt,status,error,{certainty} AS submitted FROM team_rounds '
                    'WHERE request_id=? ORDER BY updated', (request['id'],))]
            result.append(dict(session=item['id'], request=dict(request) if request else None, rounds=rounds))
        unresolved = [dict(row) for row in connection.execute(
            'SELECT DISTINCT r.member_id,r.status,q.session_id FROM team_rounds r '
            'JOIN team_requests q ON q.id=r.request_id '
            "WHERE r.status IN ('pending','uncertain') "
            f"OR (r.status IN ('blocked','denied') AND {certainty} IS NOT 0)")]
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        members = [dict(row) for row in connection.execute(
            'SELECT id,status,problem,submitted,reason,updated FROM team_members')] if 'team_members' in tables else []
        return dict(sessions=result, unresolved_submissions=unresolved, members=members)
    finally:
        connection.close()


def _save_fleet_report(fleet, path, progress):
    status = getattr(fleet, 'status', None)
    if status is None:
        return
    from app.browser.team_diagnostics import write_report
    try:
        write_report(path, dict(kind='browser_fleet', captured_at=time.time(), fleet=status()))
    except (OSError, ValueError, TypeError) as error:
        progress(f'Could not save browser recovery report: {error}')


async def run_browser_team(arguments, root: Path, *, execute_task=None, execute_desktop=None, progress=print,
                           execute_local=None, discover=None, fleet_factory=None, team_factory=None, read_input=input):
    """Factories keep command routing testable without touching the desktop."""
    options = parser().parse_args(arguments)
    root = Path(root)
    database = root / 'data/browser-team/team.sqlite3'
    fleet_report = root / 'data/browser-team/diagnostics/last-fleet.json'
    if options.command in ('board', 'message'):
        if not database.is_file():
            progress('No saved team board yet.')
            return 1
        from app.providers.collaborative import TeamStore
        from app.browser.team_board import TeamBoard
        store = TeamStore(database)
        try:
            board = TeamBoard(store.connection, database.parent / 'boards')
            request = board.latest(options.session)
            if request is None:
                progress('No saved team board for that session.')
                return 1
            if options.command == 'message':
                board.post(request, 'user', options.to, options.text)
                progress('Message queued for the recipient\'s next turn. Board: ' + str(board.path(options.session)))
            else:
                progress(json.dumps(board.snapshot(request), indent=2))
            return 0
        finally:
            store.close()
    if options.command == 'status':
        snapshot = saved_status(database, options.session)
        for label, path in (('fleet', fleet_report),
                            ('team', root / 'data/browser-team/diagnostics/last-team.json')):
            if not path.is_file():
                continue
            try:
                if path.stat().st_size > 1_000_000:
                    raise ValueError('Recovery report is too large')
                report = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(report, dict):
                    raise ValueError('Recovery report must be an object')
                snapshot['last_' + label + '_run'] = report
            except (OSError, ValueError) as error:
                snapshot[label + '_report_error'] = str(error)
        progress(json.dumps(snapshot, indent=2))
        return 0
    if options.command == 'recover':
        if not options.session.strip() or len(options.session) > 200:
            raise ValueError('Session name must contain 1..200 characters')
        snapshot = saved_status(database, options.session)
        if not snapshot['sessions']:
            progress('No saved team session matches that name.')
            return 1
    if options.command == 'run':
        task = options.task
        interactive_task = task is None
        if task is None:
            task = await asyncio.to_thread(read_input, 'Describe the task for the browser team:\n> ')
        if not task.strip() or len(task) > 50_000:
            raise ValueError('Provide a task containing 1..50000 characters')
        if options.session is not None and (not options.session.strip() or len(options.session) > 200):
            raise ValueError('Session name must contain 1..200 characters')
        if options.execute and execute_task is None:
            raise ValueError('Task execution requires the project run.py entry point')
        if options.desktop and execute_desktop is None:
            raise ValueError('Desktop execution requires the project run.py entry point')
        if interactive_task:
            # Every interactive task must first pass through the leader
            # provider. Local adapters may execute only after that provider
            # has selected and described the execution path.
            options.leader_only = True
            options.execute = True
    inventory = (discover or discover_browsers)(managed_profile=root / 'data/browser-profile')
    if options.command == 'inventory':
        snapshot = inventory_snapshot(inventory)
        if options.json:
            progress(json.dumps(snapshot, default=str, indent=2))
        else:
            progress(f"Found {snapshot['browser_count']} supported browsers, {snapshot['profile_count']} profiles "
                     f"and {snapshot['participant_count']} possible website participants.")
            for browser in inventory.browsers:
                profiles = [item for item in inventory.profiles if item.browser_id == browser.id]
                progress(f'{browser.name}: {len(profiles)} profiles')
                for profile in profiles:
                    progress(f'  {profile.name} [{profile.id}]')
            for warning in inventory.warnings:
                progress('Discovery: ' + warning)
        return 0
    selected = set(getattr(options, 'profile', []))
    profile_leader = managed_leader_profile(inventory, root / 'data/browser-profile') if options.leader == 'chrome-profile' else None
    if options.leader_only and (selected or options.leader == 'none'):
        raise ValueError('--leader-only requires a leader and cannot combine with --profile')
    if selected:
        unknown = selected - {profile.id for profile in inventory.profiles}
        if unknown:
            raise ValueError('Unknown profile IDs: ' + ', '.join(sorted(unknown)))
        profiles = [profile for profile in inventory.profiles if profile.id in selected or profile == profile_leader]
        browser_ids = {profile.browser_id for profile in profiles}
        inventory = BrowserInventory([browser for browser in inventory.browsers if browser.id in browser_ids],
                                     profiles, inventory.warnings)
    if options.leader_only:
        inventory = BrowserInventory([browser for browser in inventory.browsers
                                      if profile_leader and browser.id == profile_leader.browser_id],
                                     [profile_leader] if profile_leader else [], inventory.warnings)
    if not inventory.profiles and options.leader == 'none':
        progress('No usable browser profiles found. Start a supported installed browser once, then run inventory.')
        for warning in inventory.warnings:
            progress('Discovery: ' + warning)
        return 1
    if fleet_factory is None:
        from app.browser.fleet import BrowserFleet
        fleet_factory = BrowserFleet
    fleet = fleet_factory(root, inventory=inventory, progress=progress,
                          timeout_seconds=getattr(options, 'timeout', 180), input_mode=options.input_mode,
                          leader=options.leader != 'none',
                          leader_mode='chrome-profile' if options.leader == 'chrome-profile' else 'chromium')
    if (options.command == 'run' and not options.setup and not options.recheck_signins
            and hasattr(fleet, 'excluded_participants')):
        # Cache only an observed login requirement, never browser account names,
        # credential files, CAPTCHA or quota state. Unknown profiles get probed.
        excluded = {item['id'] for item in saved_status(database).get('members', [])
                    if item['reason'] == 'login_required'}
        fleet.excluded_participants = excluded
        if excluded:
            progress('Excluding previously signed-out tabs: ' + ', '.join(sorted(excluded)))
    team = None
    try:
        participants = await fleet.start()
        _save_fleet_report(fleet, fleet_report, progress)
        if options.command == 'open':
            progress(f'Opened {len(fleet.windows)} profile windows with {len(participants)} website tabs. '
                     'Native profile windows stay open for inspection and sign-in.')
            if getattr(fleet, '_leader_clients', []) and options.leader == 'chromium':
                await asyncio.to_thread(read_input,
                    'Sign in to ChatGPT and Gemini in Chromium. Press Enter to finish setup; '
                    'the managed Chromium window closes and saves its login profile.\n')
            return 0 if participants and not fleet.failures else 1
        if not participants:
            if getattr(fleet, 'excluded_participants', None) and not fleet.failures:
                progress('No eligible website tabs remain: known signed-out tabs were excluded. '
                         'After signing in, run with --recheck-signins.')
            else:
                progress('No profile window could be prepared. Fix the reported launch problems and try again.')
            return 1
        if options.setup:
            await asyncio.to_thread(read_input,
                'Complete login in the opened provider tabs. If using console mode, finish console setup '
                'and close developer tools. Press Enter when ready to start the team.\n')
        if team_factory is None:
            from app.providers.collaborative import CollaborativeProvider
            team_factory = CollaborativeProvider
        team = team_factory(participants, database, max_rounds=getattr(options, 'rounds', 2),
                            parallelism=getattr(options, 'parallelism', 4), timeout_seconds=options.timeout, progress=progress)
        # Keep injected/legacy provider factories compatible with the existing
        # interface while using partitioned work for normal CLI tasks.
        if hasattr(team, 'work_mode'):
            team.work_mode = getattr(options, 'work_mode', 'review')
        if options.command in ('doctor', 'smoke'):
            session = options.command + '-' + uuid.uuid4().hex
        else:
            session = options.session or 'task-' + hashlib.sha256(task.encode()).hexdigest()[:20]
        team.use_conversation_session(session)
        if options.command != 'recover':
            preflight = getattr(team, 'preflight', None)
            if preflight:
                deadline = time.monotonic() + options.wait_ready
                while True:
                    extra = {'recover_pending': True} if options.command == 'run' and hasattr(team, '_recover_startup_member') else {}
                    health = await preflight(readiness_retries=0,
                                             recheck_rate_limits=getattr(options, 'recheck_limits', False), **extra)
                    if hasattr(options, 'recheck_limits'):
                        options.recheck_limits = False
                    progress('Readiness: ' + json.dumps(team.member_status, sort_keys=True))
                    # Unsigned-in tabs are optional peers, never a startup barrier.
                    if any(status == 'ready' for status in team.member_status.values()) or time.monotonic() >= deadline:
                        break
                    await asyncio.sleep(min(3, max(0, deadline - time.monotonic())))
        if options.command == 'doctor':
            from app.browser.team_diagnostics import write_report
            health = team.status_snapshot()
            health['fleet'] = fleet.status() if hasattr(fleet, 'status') else {'failures': fleet.failures}
            path = root / 'data/browser-team/diagnostics' / (session + '.json')
            write_report(path, health)
            progress(json.dumps(health, indent=2))
            progress('Readiness report: ' + str(path))
            return 0 if not fleet.failures and health['members'] and all((member.get('health') or {}).get('status') == 'ready'
                                                  for member in health['members']) else 1
        if options.command == 'smoke':
            from app.browser.team_diagnostics import run_live_smoke
            snapshot = fleet.status() if hasattr(fleet, 'status') else {}
            report = await run_live_smoke(team, root, fleet_status=snapshot,
                driver=type(getattr(fleet, 'transport', None)).__name__, progress=progress)
            return 0 if report['status'] == 'passed' else 1
        if options.command == 'recover':
            team.use_conversation_session(options.session)
            snapshot = await team.recover_members()
            progress(json.dumps(snapshot, indent=2))
            progress('Recovery only reads prior replies. Run the task again after unresolved outcomes are cleared.')
            # Profiles that failed to launch are absent from member_status but
            # may still own outstanding submissions in this session.
            remaining = [row for row in saved_status(database, options.session)['unresolved_submissions']
                         if row['session_id'] == options.session]
            if remaining:
                progress('Still unresolved: ' + json.dumps(remaining))
            return 1 if remaining else 0
        from app.autonomy.task_analysis import analyse_task
        analysis = analyse_task(task)
        team.set_checkpoint_context({'objective': task, 'session': session, 'task_analysis': analysis})
        ready_count = sum(status == 'ready' for status in team.member_status.values())
        skipped = {ident: status for ident, status in team.member_status.items() if status != 'ready'}
        if skipped:
            progress('Skipping inactive tabs (login/challenge/uncertain/unavailable): ' + json.dumps(skipped))
        if ready_count == 0:
            progress('No ready signed-in tab. Sign in to at least one provider, or recover its pending reply.')
            return 1
        progress('Task analysis: ' + json.dumps(analysis))
        progress(f'Team session: {session}. {ready_count} active, {len(skipped)} skipped; '
                 f'{options.work_mode} mode; {options.rounds} rounds plus synthesis.')
        if options.desktop:
            result = await execute_desktop(team, task, max_actions=options.max_actions, max_minutes=options.max_minutes)
            progress(json.dumps(result, indent=2, default=str))
            return 0 if result.get('status') == 'completed' else 1
        if options.execute:
            await execute_task(team, task)
        else:
            await team.open()
            await team.send_prompt(task)
            await team.wait_for_response()
            progress('Team answer:\n\n' + await team.extract_response())
        progress('Member status: ' + json.dumps(team.member_status, sort_keys=True))
        return 0
    except (RuntimeError, OSError, ValueError) as error:
        progress(f'Browser team paused: {error}')
        progress('Saved progress: python run.py browser-team status. Resolve login or console setup in '
                 'the affected profile; uncertain submissions are retained without automatic replay.')
        return 1
    finally:
        try:
            if team is not None:
                if hasattr(team, 'status_snapshot'):
                    from app.browser.team_diagnostics import write_report
                    try:
                        write_report(root / 'data/browser-team/diagnostics/last-team.json', team.status_snapshot())
                    except (OSError, ValueError, TypeError) as error:
                        progress(f'Could not save team recovery report: {error}')
                await team.close()
        finally:
            try:
                if getattr(options, 'close_on_exit', False):
                    await fleet.close()
                elif hasattr(fleet, 'close_leader') and (options.command != 'open' or options.leader == 'chromium'):
                    await fleet.close_leader()
            finally:
                _save_fleet_report(fleet, fleet_report, progress)
