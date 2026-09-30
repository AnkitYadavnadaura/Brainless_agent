import asyncio
import hashlib
import json
import shutil
import sqlite3
import subprocess
from types import SimpleNamespace

import pytest

import app.providers.native_website as native
from app.browser.native_console import NativeConsoleIntervention, NativeTransportError
from app.providers.base_provider import UserInterventionRequired
from app.providers.native_website import DOM_PROGRAM, NativeClientError, NativeSessionStore, NativeWebsiteClient


class FakeTransport:
    """No desktop calls: execute only the fixed program's JSON protocol."""

    def __init__(self, clock):
        self.clock = clock
        self.actions = []
        self.navigations = []
        self.queues = {}
        self.url = 'https://chatgpt.com/'
        self.count = 1
        self.text = 'Historic answer'
        self.selector = "[data-message-author-role='assistant']"
        self.after_submit = None
        self.before_submit = None

    def queue(self, action, *responses):
        self.queues.setdefault(action, []).extend(responses)

    async def navigate(self, hwnd, url, *, tab_index):
        self.navigations.append((hwnd, url, tab_index))
        self.url = url
        if url.endswith('/') or url.endswith('/app'):
            self.count, self.text = 0, ''

    def state(self, **extra):
        return dict(url=self.url, ready=True, busy=False, selector=self.selector,
                    count=self.count, text=self.text, snapshots={self.selector: {'count': self.count}}, **extra)

    async def evaluate(self, hwnd, family, script, *, tab_index):
        prefix = '(' + DOM_PROGRAM + ')('
        assert script.startswith(prefix) and script.endswith(')')
        payload = json.loads(script[len(prefix):-1])
        self.actions.append((hwnd, family, tab_index, payload))
        self.clock.value += 1.1
        action = payload['action']
        queue = self.queues.get(action)
        if queue:
            response = queue.pop(0)
            if isinstance(response, BaseException):
                raise response
            if response is not None:
                return response
        if action == 'bind':
            return {'bound': True, 'url': self.url}
        if action == 'observe':
            return self.state()
        if action == 'prepare':
            return self.state(prepared=True)
        if action == 'submit':
            if self.before_submit:
                self.before_submit(payload)
            self.count += 1
            self.text = 'New completed answer'
            self.url = 'https://chatgpt.com/c/canonical-chat'
            if self.after_submit:
                self.after_submit()
            return {'submitted': True, 'url': self.url}
        raise AssertionError(action)

    def calls(self, action):
        return [row[3] for row in self.actions if row[3]['action'] == action]


@pytest.fixture
def client(tmp_path, monkeypatch):
    clock = SimpleNamespace(value=0.0)
    monkeypatch.setattr(native, 'time', SimpleNamespace(monotonic=lambda: clock.value, time=lambda: 1234))
    transport = FakeTransport(clock)
    return NativeWebsiteClient(participant_id='chrome-default-chatgpt', provider_name='chatgpt',
                               hwnd=42, family='chromium', tab_index=1, transport=transport,
                               store=NativeSessionStore(tmp_path / 'native.sqlite3'),
                               timeout_seconds=6, poll_interval=.001)


def restart(client):
    return NativeWebsiteClient(participant_id=client.id, provider_name=client.provider_name,
                               hwnd=client.hwnd, family=client.family, tab_index=client.tab_index,
                               transport=client.transport, store=client.store, timeout_seconds=6,
                               poll_interval=.001, rollover_after=client.rollover_after)


@pytest.mark.asyncio
async def test_coordinator_recovers_native_completed_response_after_crash_gap(client, tmp_path):
    from app.providers.collaborative import CollaborativeProvider, TeamStore
    database = tmp_path / 'team.sqlite3'
    store = TeamStore(database)
    request = store.begin('default', 'Solve this task')
    store.submission(request, client, 'proposal', 1)
    store.close()
    client.set_request_context(json.dumps([request, 'proposal', 1], separators=(',', ':')))
    assert await client.ask('Solve this task') == 'New completed answer'
    # Simulate process loss after the native receipt commit but before the team
    # round was completed. The two real stores must agree on the exact request.
    team = CollaborativeProvider([restart(client)], database, progress=lambda _: None)
    try:
        team.use_conversation_session('default')
        result = await team.recover_members()
        assert result['members'][0]['status'] == 'ready'
        assert not team.store.unresolved()
        assert len(client.transport.calls('submit')) == 1
        assert not await team.is_response_complete()
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_submission_intent_precedes_send_and_prompt_stays_json_data(client):
    prompt = 'Plan safely. "); globalThis.shouldNotRun = true; //\n\\Unicode: \u2603'

    def inspect_intent(payload):
        record = client.store.get(client.id, client.session)
        receipt = json.loads(record['receipt'])
        assert record['state'] == 'pending'
        assert receipt['request'] == payload['request']
        assert receipt['prompt_hash'] == hashlib.sha256(prompt.encode()).hexdigest()

    client.transport.before_submit = inspect_intent
    assert await client.ask(prompt) == 'New completed answer'
    assert client.transport.calls('prepare')[0]['prompt'] == prompt
    assert len(client.transport.calls('submit')) == 1
    record = client.store.get(client.id, client.session)
    assert record['state'] == 'completed'
    assert record['url'] == 'https://chatgpt.com/c/canonical-chat'
    assert json.loads(record['receipt'])['turn_count'] == 1
    assert not client._pending
    assert all(row[:3] == (42, 'chromium', 1) for row in client.transport.actions)


@pytest.mark.asyncio
async def test_old_answer_text_changes_are_not_new_turns(client):
    baseline = client.transport.state(prepared=True)
    client.transport.queue('prepare', baseline)
    client.transport.after_submit = lambda: setattr(client.transport, 'count', baseline['count'])
    with pytest.raises(NativeClientError, match='timed out') as failure:
        await client.ask('test')
    assert failure.value.submitted
    assert client.store.get(client.id, client.session)['state'] == 'pending'


@pytest.mark.asyncio
@pytest.mark.parametrize('verified', [True, False])
async def test_virtualized_reply_needs_exact_user_prompt_verification(client, verified):
    client._native_mode = True
    client._pending = True
    receipt = {'baseline_count': 3, 'baseline_text': 'old answer', 'selector': 'uia:chatgpt:assistant',
               'prompt_hash': 'a' * 64, 'turn_count': 3}
    state = {'url': 'https://chatgpt.com/c/saved', 'selector': receipt['selector'], 'count': 3,
             'text': 'new answer', 'busy': False, 'user_copy': {'runtime_id': 'user'},
             'copy_response': {'runtime_id': 'answer'}}
    reads = []
    async def action(name, **kwargs):
        client.transport.clock.value += 1.1
        if name == 'read_response':
            assert kwargs['prompt_hash'] == receipt['prompt_hash']
            reads.append(name)
            return {**state, 'request_verified': verified}
        assert name == 'observe'
        return state
    client._action = action
    if verified:
        assert await client._wait_for_answer(state['url'], receipt) == 'new answer'
        assert client.store.get(client.id, client.session)['state'] == 'completed'
    else:
        with pytest.raises(NativeClientError, match='timed out'):
            await client._wait_for_answer(state['url'], receipt)
        assert client.store.get(client.id, client.session)['state'] == 'pending'
    assert reads == ['read_response']


@pytest.mark.asyncio
async def test_fallback_selector_is_compared_to_its_own_baseline(client):
    client.transport.selector = '.model-response-text'
    client.transport.queue('prepare', {
        'prepared': True, 'url': client.url, 'selector': 'message-content', 'count': 1, 'text': 'old',
        'snapshots': {'message-content': {'count': 1}, '.model-response-text': {'count': 5}},
    })
    client.transport.after_submit = lambda: setattr(client.transport, 'count', 5)
    with pytest.raises(NativeClientError, match='timed out'):
        await client.ask('test')


@pytest.mark.asyncio
async def test_growing_fallback_selector_can_produce_new_answer(client):
    client.transport.selector = '.model-response-text'
    client.transport.queue('prepare', {
        'prepared': True, 'url': client.url, 'selector': 'message-content', 'count': 10, 'text': 'old',
        'snapshots': {'message-content': {'count': 10}, '.model-response-text': {'count': 0}},
    })
    assert await client.ask('test') == 'New completed answer'


@pytest.mark.asyncio
@pytest.mark.parametrize('error', [NativeTransportError('focus changed', submitted=False),
                                  UserInterventionRequired('console setup needed')])
async def test_observation_failure_never_makes_sent_prompt_safe_to_retry(client, error):
    client.transport.queue('observe', None, error)
    with pytest.raises(type(error)) as failure:
        await client.ask('test')
    assert failure.value.submitted is True
    record = client.store.get(client.id, client.session)
    assert record['state'] == 'pending'
    assert record['url'].endswith('/c/canonical-chat')
    with pytest.raises(NativeClientError, match='pending'):
        await client.ask('test again')
    assert len(client.transport.calls('submit')) == 1


@pytest.mark.asyncio
async def test_latest_canonical_url_survives_polling_failure(client):
    client.transport.queue('observe', None,
                           dict(client.transport.state(), url='https://chatgpt.com/c/later-url'),
                           NativeTransportError('focus changed', submitted=False))
    with pytest.raises(NativeTransportError):
        await client.ask('test')
    assert client.store.get(client.id, client.session)['url'].endswith('/c/later-url')


@pytest.mark.asyncio
@pytest.mark.parametrize('rejection', [{'error': 'send_unavailable'},
                                     NativeTransportError('focus changed', submitted=False)])
async def test_confirmed_pre_send_failure_permits_retry(client, rejection):
    client.transport.queue('submit', rejection)
    with pytest.raises((NativeClientError, NativeTransportError)) as failure:
        await client.ask('test')
    assert failure.value.submitted is False
    assert not client._pending
    assert client.store.get(client.id, client.session)['state'] == 'failed'
    assert await client.ask('retry') == 'New completed answer'
    assert len(client.transport.calls('submit')) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('error_name', ['login', 'challenge', 'rate_limit'])
async def test_owner_interventions_before_send_never_create_pending_receipt(client, error_name):
    client.transport.queue('observe', {'error': error_name})
    with pytest.raises(UserInterventionRequired) as failure:
        await client.ask('test')
    assert failure.value.submitted is False
    assert not client.transport.calls('submit')
    assert client.store.get(client.id, client.session) is None


@pytest.mark.asyncio
async def test_submission_cancellation_is_durable_and_restart_does_not_replay(client):
    client.transport.queue('submit', asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await client.ask('test')
    fresh = restart(client)
    calls = len(client.transport.actions)
    with pytest.raises(NativeClientError, match='needs review'):
        await fresh.ask('test')
    assert len(client.transport.actions) == calls
    assert fresh._pending
    with pytest.raises(NativeClientError, match='before switching'):
        fresh.use_conversation_session('another-project')


@pytest.mark.asyncio
async def test_read_only_recovery_in_current_tab_never_submits_again(client):
    client.transport.queue('observe', None, NativeTransportError('focus changed', submitted=False))
    with pytest.raises(NativeTransportError):
        await client.ask('test')
    navigations = list(client.transport.navigations)
    assert await client.recover_response() == 'New completed answer'
    assert client.transport.navigations == navigations
    assert len(client.transport.calls('submit')) == 1
    assert not client._pending
    assert await client.recover_response() is None


@pytest.mark.asyncio
async def test_restart_recovers_only_saved_canonical_chat(client):
    client.transport.queue('observe', None, NativeTransportError('focus changed', submitted=False))
    with pytest.raises(NativeTransportError):
        await client.ask('test')
    fresh = restart(client)
    assert await fresh.recover_response() == 'New completed answer'
    assert client.transport.navigations[-1][1] == 'https://chatgpt.com/c/canonical-chat'
    assert len(client.transport.calls('submit')) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('phase', ['bind', 'observe'])
async def test_recovery_never_accepts_a_reply_from_another_conversation(client, phase):
    client.transport.queue('observe', None, NativeTransportError('focus changed', submitted=False))
    with pytest.raises(NativeTransportError):
        await client.ask('test')
    fresh = restart(client)
    client.transport.queue(phase, {**client.transport.state(), 'bound': True, 'url': 'https://chatgpt.com/',
                                   'text': 'Unrelated response', 'count': 100})
    with pytest.raises(NativeClientError, match='conversation'):
        await fresh.recover_response()
    record = client.store.get(client.id, client.session)
    assert record['state'] == 'pending' and record['url'].endswith('/c/canonical-chat')
    assert len(client.transport.calls('submit')) == 1


@pytest.mark.asyncio
async def test_completed_response_recovery_requires_exact_coordinator_round(client):
    context = '["team-request", "proposal", 1]'
    client.set_request_context(context)
    await client.ask('test')
    fresh = restart(client)
    calls = len(client.transport.actions)
    assert await fresh.recover_response() is None
    fresh.set_request_context('["different-request", "proposal", 1]')
    assert await fresh.recover_response() is None
    fresh.set_request_context(context)
    assert await fresh.recover_response() == 'New completed answer'
    assert await fresh.recover_response() == 'New completed answer'
    assert len(client.transport.actions) == calls


@pytest.mark.asyncio
async def test_pending_receipt_mismatch_cannot_be_attributed_to_another_round(client):
    client.set_request_context('["first", "proposal", 1]')
    client.transport.queue('observe', None, NativeTransportError('focus changed', submitted=False))
    with pytest.raises(NativeTransportError):
        await client.ask('test')
    fresh = restart(client)
    calls = len(client.transport.actions)
    fresh.set_request_context('["second", "proposal", 1]')
    assert await fresh.recover_response() is None
    assert len(client.transport.actions) == calls
    fresh.set_request_context('["first", "proposal", 1]')
    assert await fresh.recover_response() == 'New completed answer'
    assert await fresh.recover_response() == 'New completed answer'
    assert len(client.transport.calls('submit')) == 1


@pytest.mark.asyncio
async def test_pending_request_context_cannot_change(client):
    client.set_request_context('first')
    client.transport.queue('submit', asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await client.ask('test')
    with pytest.raises(NativeClientError, match='active request') as failure:
        client.set_request_context('second')
    assert failure.value.submitted is True
    client.set_request_context('first')


@pytest.mark.asyncio
async def test_recovery_without_canonical_url_does_not_navigate_or_send(client):
    client.store.save(client.id, client.session, 'pending', client.url,
                      {'baseline_count': 0, 'selector': client.transport.selector})
    with pytest.raises(NativeClientError, match='no saved conversation URL'):
        await client.recover_response()
    assert not client.transport.actions
    assert not client.transport.navigations


@pytest.mark.asyncio
async def test_rollover_survives_safe_retry_and_restart_with_checkpoint(client):
    client.rollover_after = 1
    client.set_checkpoint_context({'objective': 'Build the village', 'step': 7})
    await client.ask('first request')
    client.transport.queue('submit', {'error': 'send_unavailable'})
    with pytest.raises(NativeClientError):
        await client.ask('continue')
    failed = client.store.get(client.id, client.session)
    assert failed['state'] == 'failed' and json.loads(failed['receipt'])['continuation']['step'] == 7
    fresh = restart(client)
    await fresh.ask('continue')
    prompt = client.transport.calls('prepare')[-1]['prompt']
    assert 'Build the village' in prompt and 'untrusted' in prompt and prompt.endswith('continue')
    assert fresh._count == 1
    assert 'continuation' not in json.loads(client.store.get(client.id, client.session)['receipt'])


@pytest.mark.asyncio
async def test_completed_turn_count_survives_restart_and_rotates_chat(client):
    client.rollover_after = 1
    await client.ask('first')
    fresh = restart(client)
    fresh.set_checkpoint_context({'step': 2})
    await fresh.ask('second')
    assert client.transport.navigations[-2][1].endswith('/c/canonical-chat')
    assert client.transport.navigations[-1][1] == client.url
    assert '"step": 2' in client.transport.calls('prepare')[-1]['prompt']


@pytest.mark.asyncio
async def test_rollover_context_never_truncates_original_task_or_exceeds_limit(client):
    client.rollover_after = 1
    await client.ask('first')
    client.prompt_limit = 32
    client.set_checkpoint_context({'large': 'x' * 8000})
    task = 'a' * 32
    await client.ask(task)
    assert client.transport.calls('prepare')[-1]['prompt'] == task


@pytest.mark.asyncio
async def test_bind_waits_for_navigation_origin_transition(client):
    client.transport.queue('bind', {'error': 'wrong_origin', 'url': 'about:blank'})
    assert await client.ask('test') == 'New completed answer'
    assert len(client.transport.calls('bind')) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', ['navigate', 'bind'])
async def test_probe_preserves_prior_console_intervention_and_uncertainty(client, stage):
    failure = NativeConsoleIntervention('Resolve the prior uncertain console operation', submitted=True)
    if stage == 'navigate':
        async def navigate(*args, **kwargs):
            raise failure
        client.transport.navigate = navigate
    else:
        client.transport.queue('bind', failure)
    health = await client.probe()
    assert health['status'] == 'intervention'
    assert health['submitted'] is False and health['ready'] is False
    assert health['transport_submitted'] is True
    assert not client.transport.calls('prepare') and not client.transport.calls('submit')
    assert client.store.get(client.id, client.session) is None


@pytest.mark.asyncio
async def test_console_setup_probe_is_blocked_without_inventing_a_submission(client):
    client.transport.queue('bind', NativeConsoleIntervention('Console setup required; no script was pasted'))
    health = await client.probe()
    assert health['status'] == 'intervention'
    assert health['submitted'] is False and health['ready'] is False
    assert not client.transport.calls('prepare') and not client.transport.calls('submit')


@pytest.mark.asyncio
async def test_team_rejoins_after_prior_console_uncertainty_is_resolved(client, tmp_path):
    from app.providers.collaborative import CollaborativeProvider
    client.transport.queue('bind', NativeConsoleIntervention('Resolve the prior uncertain console operation', submitted=True))
    team = CollaborativeProvider([client], tmp_path / 'team.sqlite3', progress=lambda _: None)
    try:
        health = (await team.preflight(backoff_seconds=0))['members'][0]
        assert health['status'] == 'blocked' and health['reason'] == 'intervention'
        assert health['submitted'] is False
        assert health['health']['transport_submitted'] is True
        assert len(client.transport.calls('bind')) == 1
        assert (await team.preflight(backoff_seconds=0))['members'][0]['status'] == 'ready'
        assert not client.transport.calls('prepare') and not client.transport.calls('submit')
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_malformed_console_prepare_still_allows_certified_safe_retry(client):
    client.input_mode = 'console'
    async def unsupported_native(*args, **kwargs):
        return {'error': 'accessibility_unavailable'}
    client.transport.native_action = unsupported_native
    client.transport.queue('prepare', ['invalid probe response'])
    with pytest.raises(NativeClientError, match='Invalid browser probe result') as failure:
        await client.ask('test')
    assert failure.value.submitted is False
    assert not client.transport.calls('submit')
    assert await client.ask('test') == 'New completed answer'
    assert len(client.transport.calls('submit')) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['wrong_origin', 'composer_unavailable', 'accessibility_unavailable'])
async def test_auto_loading_errors_never_open_developer_console(client, failure):
    async def native_action(*args, **kwargs):
        return {'error': failure}
    client.transport.native_action = native_action
    with pytest.raises((NativeClientError, UserInterventionRequired)):
        await client._action('bind')
    assert not client.transport.actions


@pytest.mark.asyncio
@pytest.mark.parametrize('action', ['switch_native', 'reload_tab'])
async def test_peer_repair_cannot_switch_input_for_pending_prompt(client, action):
    client.store.save(client.id, client.session, 'pending', client.url, {})
    outcome = await client.repair(action)
    assert outcome['status'] == 'pending' and outcome['submitted'] is True
    assert not client.transport.navigations and not client.transport.actions
    with pytest.raises(ValueError):
        await client.repair('run_shell')


@pytest.mark.asyncio
async def test_peer_reload_preserves_conversation_and_never_sends(client):
    saved = 'https://chatgpt.com/c/existing-chat'
    client.store.save(client.id, client.session, 'completed', saved, {'turn_count': 1})
    await client.probe()
    first = len(client.transport.navigations)
    assert (await client.repair('reload_tab'))['ready']
    assert len(client.transport.navigations) == first + 1
    assert client.transport.navigations[-1][1] == saved
    assert not client.transport.calls('prepare') and not client.transport.calls('submit')


@pytest.mark.asyncio
async def test_peer_reload_refuses_a_generating_tab(client):
    await client.probe()
    client.transport.queue('observe', {'ready': True, 'busy': True})
    first = len(client.transport.navigations)
    outcome = await client.repair('reload_tab')
    assert outcome['status'] == 'pending'
    assert len(client.transport.navigations) == first


@pytest.mark.asyncio
async def test_peer_can_switch_unsent_client_to_native_and_recheck(client):
    client.input_mode = 'console'
    actions = []
    async def native_action(hwnd, provider, action, **kwargs):
        actions.append(action)
        return {'bound': True, 'ready': True, 'busy': False, 'url': client.url}
    client.transport.native_action = native_action
    outcome = await client.repair('switch_native')
    assert outcome['ready'] and outcome['input_mode'] == 'native'
    assert actions == ['bind', 'observe'] and not client.transport.calls('submit')


@pytest.mark.asyncio
async def test_malformed_native_probe_keeps_submission_pending(client):
    client._native_mode = True
    client.input_mode = 'native'
    client._pending = True
    async def invalid_native(*args, **kwargs):
        return ['invalid probe response']
    client.transport.native_action = invalid_native
    with pytest.raises(NativeClientError, match='Invalid browser probe result') as failure:
        await client._action('observe')
    assert failure.value.submitted is True and client._pending
    assert not client.transport.actions


@pytest.mark.asyncio
async def test_malformed_native_fallback_is_classified_before_reading_result(client):
    async def native_action(hwnd, provider, action, **kwargs):
        return {'bound': True} if action == 'bind' else ['invalid probe response']
    client.transport.native_action = native_action
    client.transport.queue('prepare', NativeConsoleIntervention('Console setup unavailable'))
    with pytest.raises(NativeClientError, match='Invalid browser probe result') as failure:
        await client._action('prepare', prompt='test', request='one')
    assert failure.value.submitted is False
    assert not client.transport.calls('submit')


@pytest.mark.asyncio
async def test_session_cannot_change_during_initial_navigation(client):
    original = client.transport.navigate

    async def navigate(*args, **kwargs):
        with pytest.raises(NativeClientError, match='active request'):
            client.use_conversation_session('another-project')
        await original(*args, **kwargs)

    client.transport.navigate = navigate
    await client.ask('test')
    assert client.session == 'default'
    client.set_checkpoint_context({'secret_from_project_one': 'context'})
    client.use_conversation_session('another-project')
    assert client._context == {}


@pytest.mark.parametrize('url', [None, 'https://[', 'https://chatgpt.com:bad',
                                'https://someone:secret@chatgpt.com/c/a',
                                'https://chatgpt.com.evil.test/c/a', 'javascript:alert(1)',
                                'https://chatgpt.com\n/c/a'])
def test_saved_urls_are_validated_without_parser_crashes(client, url):
    assert client._safe_url(url) == client.url


def test_checkpoint_is_detached_and_bounded_even_after_json_escaping(client):
    source = {'items': ['before']}
    client.set_checkpoint_context(source)
    source['items'].append('after')
    assert client._context['items'] == ['before']
    client.set_checkpoint_context({'items': '\u2603\\"' * 9000})
    assert len(json.dumps(client._context, ensure_ascii=True)) <= 8000


def test_session_store_closes_every_connection(tmp_path, monkeypatch):
    connections = []
    original = sqlite3.connect

    def connect(*args, **kwargs):
        result = original(*args, **kwargs)
        connections.append(result)
        return result

    monkeypatch.setattr(native.sqlite3, 'connect', connect)
    store = NativeSessionStore(tmp_path / 'native.sqlite3')
    store.save('participant', 'session', 'pending', 'https://chatgpt.com/', {})
    assert store.get('participant', 'session')['state'] == 'pending'
    assert len(connections) == 3
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match='closed'):
            connection.execute('SELECT 1')


def test_fixed_dom_program_with_offline_javascript_dom_fixture():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node is optional; needed only for the offline JavaScript fixture')
    harness = r'''
import assert from 'node:assert/strict';
const program = __DOM_PROGRAM__;
const visibleNode = text => ({innerText:text,disabled:false,
  getClientRects:()=>[{}],getAttribute:()=>null});
class Textarea {
  set value(value) { this._value=value; }
  get value() { return this._value || ''; }
  getClientRects() { return [{}]; }
  getAttribute() { return null; }
  focus() {}
  dispatchEvent() {}
}
globalThis.HTMLTextAreaElement=Textarea;
globalThis.HTMLInputElement=class {};
globalThis.InputEvent=class {};
globalThis.Event=class {};
globalThis.setTimeout=callback=>callback();
globalThis.getComputedStyle=()=>({visibility:'visible',display:'block'});
globalThis.location={origin:'https://chatgpt.com',href:'https://chatgpt.com/c/example'};
globalThis.window={name:''};
const composer=new Textarea();
let clicks=0;
const send={...visibleNode('Send'),click:()=>clicks++};
const hidden={...visibleNode('hidden answer'),getClientRects:()=>[]};
const nodes={'.input':[composer],'.send':[send],'.preferred':[visibleNode('old'),hidden],
             '.fallback':[visibleNode('older'),visibleNode('latest fallback')]};
globalThis.document={body:{innerText:'Conversation'},querySelectorAll:s=>nodes[s] || []};
const data={origin:location.origin,owner:'owned-tab',max_response:1000,
  selectors:{input:['.input'],send:['.send'],stop:['.stop'],response:['.preferred','.fallback']}};
assert.equal((await program({...data,origin:'https://evil.test',action:'bind'})).error,'wrong_origin');
assert.equal(window.name,'');
assert.equal((await program({...data,action:'bind'})).bound,true);
const state=await program({...data,action:'observe'});
assert.equal(state.text,'old');
assert.deepEqual(state.snapshots,{'.preferred':{count:1},'.fallback':{count:2}});
const prompt='literal "); globalThis.INJECTED=true; //\nUnicode \u2603';
assert.equal((await program({...data,action:'prepare',request:'request-one',prompt})).prepared,true);
assert.equal(composer.value,prompt);
assert.equal(globalThis.INJECTED,undefined);
assert.equal((await program({...data,action:'submit',request:'request-one'})).submitted,true);
assert.equal((await program({...data,action:'submit',request:'request-one'})).duplicate,true);
assert.equal(clicks,1);
assert.equal((await program({...data,action:'prepare',request:'request-one',prompt})).error,'already_submitted');
window.name='someone-else';
assert.equal((await program({...data,action:'submit',request:'request-one'})).error,'wrong_tab');
assert.equal(clicks,1);
window.name=data.owner;
nodes['.preferred']=[visibleNode('x'.repeat(1001))];
assert.equal((await program({...data,action:'observe'})).error,'response_too_large');
nodes['[role="alert"], [role="dialog"]']=[visibleNode('You reached the usage limit')];
assert.equal((await program({...data,action:'observe'})).error,'rate_limit');
nodes['[role="alert"], [role="dialog"]']=[];
nodes['button,a,[role="button"]']=[visibleNode('Log in')];
assert.equal((await program({...data,action:'observe'})).error,'login');
console.log('fixed DOM fixture passed');
'''.replace('__DOM_PROGRAM__', '(' + DOM_PROGRAM + ')')
    result = subprocess.run([node, '--input-type=module'], input=harness, capture_output=True,
                            text=True, encoding='utf-8', timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'fixed DOM fixture passed'
