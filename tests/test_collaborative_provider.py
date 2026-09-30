import asyncio
import json
import sqlite3

import pytest

from app.providers.base_provider import ProviderError, UserInterventionRequired
from app.providers.collaborative import CollaborativeProvider, TeamStore


class Client:
    def __init__(self, ident, provider, answers):
        self.id, self.provider_name = ident, provider
        self.answers = list(answers)
        self.prompts = []
        self.sessions = []
        self.checkpoints = []
        self.requests = []

    def use_conversation_session(self, key):
        self.sessions.append(key)

    def set_checkpoint_context(self, context):
        self.checkpoints.append(context)

    def set_request_context(self, key):
        self.requests.append(json.loads(key))

    async def ask(self, prompt):
        self.prompts.append(prompt)
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        if callable(answer):
            return await answer()
        return answer


async def ask(team, text='Return JSON only: {"ok": true}'):
    team.prepare_conversation(text)
    await team.open()
    await team.verify_page()
    await team.start_conversation()
    await team.send_prompt(text)
    await team.wait_for_response()
    response = await team.extract_response()
    team.remember_conversation()
    return response


def provider(tmp_path, clients, **kwargs):
    return CollaborativeProvider(clients, tmp_path / 'team.sqlite3', progress=lambda _: None, **kwargs)


@pytest.mark.asyncio
async def test_chromium_leader_synthesizes_even_if_native_peer_is_listed_first(tmp_path):
    peer = Client('edge', 'gemini', ['peer proposal'])
    leader = Client('chromium-leader:chatgpt', 'chatgpt', ['leader proposal', 'leader final'])
    leader.team_role = 'leader'
    team = provider(tmp_path, [peer, leader], max_rounds=1)
    try:
        assert await ask(team) == 'leader final'
        assert team.leader_id == leader.id and len(peer.prompts) == 1
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_failed_leader_yields_to_ready_peer(tmp_path):
    failure = ProviderError('Disconnected')
    failure.submitted = True
    leader = Client('chromium-leader:chatgpt', 'chatgpt', [failure])
    leader.team_role = 'leader'
    peer = Client('edge', 'gemini', ['proposal', 'peer final'])
    team = provider(tmp_path, [leader, peer], max_rounds=1)
    try:
        assert await ask(team) == 'peer final'
        assert team.leader_id == peer.id
        assert len(leader.prompts) == 1 and team.member_status[leader.id] == 'uncertain'
    finally:
        await team.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('advice,expected', [('{"action":"switch_native"}', ['switch_native']),
    ('{"action":"run_shell"}', []), ('{"action":"recheck","code":"bad"}', []),
    ('{"action":"hold"}', []), ('not JSON', [])])
async def test_website_advice_can_only_invoke_a_registered_verified_repair(tmp_path, advice, expected):
    helper = Client('leader', 'chatgpt', [advice, 'proposal', 'final'])
    helper.team_role = 'leader'
    broken = Client('broken', 'gemini', ['fixed proposal'] if expected else [])
    repaired = []
    async def probe():
        return {'status': 'ready' if repaired else 'unavailable', 'ready': bool(repaired)}
    async def repair(action):
        repaired.append(action)
        return {'ready': True}
    broken.probe, broken.repair = probe, repair
    team = provider(tmp_path, [helper, broken], max_rounds=1)
    try:
        await team.preflight(readiness_retries=0)
        assert not helper.prompts  # doctor/readiness never asks the websites for advice
        assert await ask(team) == 'final'
        assert repaired == expected
        rounds = [row['round'] for row in team.store.connection.execute('SELECT round FROM team_rounds')]
        assert 'repair-1' in rounds
        assert team.member_status[broken.id] == ('ready' if expected else 'unavailable')
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_peer_repair_never_replays_unknown_submission(tmp_path):
    helper = Client('leader', 'chatgpt', ['proposal', 'final'])
    broken = Client('broken', 'gemini', [])
    async def repair(action):
        pytest.fail('Unknown submission must not be repaired by resubmission')
    broken.repair = repair
    team = provider(tmp_path, [helper, broken], max_rounds=1)
    team._set_member_status(broken.id, 'uncertain', 'Unknown submission', submitted=True)
    try:
        assert await ask(team) == 'final'
        assert not broken.prompts and len(helper.prompts) == 2
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_peer_repair_budget_stops_diagnosis_loop(tmp_path):
    helper = Client('leader', 'chatgpt', ['{"action":"hold"}', '{"action":"hold"}', 'proposal', 'final'])
    broken = [Client(f'broken-{index}', 'gemini', []) for index in range(4)]
    async def probe():
        return {'ready': False, 'status': 'unavailable'}
    async def repair(action):
        pytest.fail('Hold cannot invoke a repair')
    for member in broken:
        member.probe, member.repair = probe, repair
    team = provider(tmp_path, [helper, *broken], max_rounds=1, max_peer_repairs=2)
    try:
        assert await ask(team) == 'final'
        assert len(helper.prompts) == 4
        assert len(team._repair_attempted) == 2 and not any(member.prompts for member in broken)
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_repair_claim_requires_an_independent_successful_probe(tmp_path):
    helper = Client('leader', 'chatgpt', ['{"action":"recheck"}', 'proposal', 'final'])
    broken = Client('broken', 'gemini', [])
    async def probe():
        return {'ready': False, 'status': 'unavailable'}
    async def repair(action):
        return {'ready': True}
    broken.probe, broken.repair = probe, repair
    team = provider(tmp_path, [helper, broken], max_rounds=1)
    try:
        assert await ask(team) == 'final'
        assert team.member_status[broken.id] == 'unavailable' and not broken.prompts
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_peers_exchange_and_final_schema_is_preserved(tmp_path):
    exact = '{"ok": true, "text": "original output; no wrapper"}'
    first = Client('chrome-default-chatgpt', 'chatgpt', ['proposal-one', 'review-one', exact])
    second = Client('edge-work-gemini', 'gemini', ['proposal-two', 'review-two'])
    team = provider(tmp_path, [first, second])
    team.use_conversation_session('project1')
    team.set_checkpoint_context({'objective': 'Taj Mahal', 'step': 4})
    assert await ask(team) == exact
    assert 'proposal-two' in first.prompts[1]
    assert 'proposal-one' in second.prompts[1]
    assert 'gemini' in first.prompts[1]
    assert 'untrusted' in first.prompts[2]
    assert 'review-two' in first.prompts[2]
    assert first.sessions == ['project1']
    assert second.checkpoints[-1]['step'] == 4
    rows = team.store.connection.execute('SELECT status FROM team_rounds').fetchall()
    assert len(rows) == 5 and all(row['status'] == 'completed' for row in rows)
    assert team.store.latest('project1')['status'] == 'extracted'
    assert first.requests == [[team._request_id, stage, 1] for stage in ('proposal', 'review-1', 'synthesis')]
    await team.close()


@pytest.mark.asyncio
async def test_one_member_is_used_without_redundant_peer_loops(tmp_path):
    client = Client('one', 'chatgpt', ['{"ok":true}'])
    team = provider(tmp_path, [client])
    assert json.loads(await ask(team)) == {'ok': True}
    assert len(client.prompts) == 1
    await team.close()


@pytest.mark.asyncio
async def test_login_member_is_blocked_and_others_diagnose(tmp_path):
    locked = Client('locked', 'chatgpt', [UserInterventionRequired('Login needed')])
    healthy = Client('healthy', 'gemini', ['proposal', 'review', '{"ok":true}'])
    team = provider(tmp_path, [locked, healthy])
    assert json.loads(await ask(team))['ok']
    assert team.member_status['locked'] == 'blocked'
    assert len(locked.prompts) == 1
    assert 'Login needed' in healthy.prompts[1]
    await team.close()


@pytest.mark.asyncio
async def test_timeout_is_never_replayed_and_is_persisted(tmp_path):
    async def delay():
        await asyncio.sleep(2)
        return 'late'
    delayed = Client('delayed', 'chatgpt', [delay])
    healthy = Client('healthy', 'gemini', ['proposal', 'review', '{"ok":true}'])
    team = provider(tmp_path, [delayed, healthy], timeout_seconds=.02)
    assert await ask(team) == '{"ok":true}'
    assert len(delayed.prompts) == 1
    assert team.member_status['delayed'] == 'uncertain'
    await team.close()
    fresh = provider(tmp_path, [Client('delayed', 'chatgpt', []), Client('healthy', 'gemini', [])])
    assert fresh.member_status['delayed'] == 'uncertain'
    await fresh.close()


@pytest.mark.asyncio
async def test_only_explicit_unsubmitted_error_retries_once_after_diagnosis(tmp_path):
    failure = ProviderError('Composer was absent before input')
    failure.submitted = False
    failed = Client('failed', 'chatgpt', [failure, 'recovered', '{"ok":true}'])
    helper = Client('helper', 'gemini', ['proposal', 'diagnosis'])
    team = provider(tmp_path, [failed, helper])
    assert await ask(team) == '{"ok":true}'
    assert 'diagnosis' in failed.prompts[1]
    assert len(failed.prompts) == 3  # failed proposal, certified retry, final synthesis
    assert team.member_status['failed'] == 'ready'
    await team.close()


@pytest.mark.asyncio
async def test_ambiguous_provider_error_is_not_retried(tmp_path):
    broken = Client('broken', 'chatgpt', [ProviderError('Network interrupted')])
    team = provider(tmp_path, [broken])
    await team.send_prompt('test')
    with pytest.raises(ProviderError, match='paused'):
        await team.wait_for_response()
    assert not await team.recover_conversation()
    assert len(broken.prompts) == 1
    assert team.store.latest('default')['status'] == 'paused'
    await team.close()


@pytest.mark.asyncio
async def test_permission_denial_propagates(tmp_path):
    denied = Client('denied', 'chatgpt', [PermissionError('User denied browser action')])
    team = provider(tmp_path, [denied])
    await team.send_prompt('test')
    with pytest.raises(PermissionError, match='denied'):
        await team.wait_for_response()
    await team.close()


@pytest.mark.asyncio
async def test_rate_limit_not_retried_even_with_false_submission_flag(tmp_path):
    error = ProviderError('Rate limit reached')
    error.submitted = False
    client = Client('quota', 'chatgpt', [error])
    team = provider(tmp_path, [client])
    await team.send_prompt('test')
    with pytest.raises(ProviderError):
        await team.wait_for_response()
    assert team.member_status['quota'] == 'blocked'
    assert len(client.prompts) == 1
    await team.close()


@pytest.mark.asyncio
async def test_pending_session_guard_and_recovery_does_not_resend(tmp_path):
    ready = asyncio.Event()

    async def delayed():
        await ready.wait()
        return '{"ok":true}'

    client = Client('one', 'chatgpt', [delayed, '{"next":true}'])
    team = provider(tmp_path, [client])
    team.use_conversation_session('first')
    await team.send_prompt('first')
    with pytest.raises(ProviderError, match='pending'):
        team.use_conversation_session('second')
    with pytest.raises(ProviderError, match='pending'):
        await team.send_prompt('duplicate')
    with pytest.raises(ProviderError, match='pending'):
        await team.wait_for_response(.01)
    assert not await team.recover_conversation()
    ready.set()
    await team.wait_for_response()
    assert await team.recover_conversation()
    assert await team.extract_response() == '{"ok":true}'
    team.use_conversation_session('second')
    assert await ask(team, 'next') == '{"next":true}'
    assert len(client.prompts) == 2
    await team.close()


@pytest.mark.asyncio
async def test_crash_submission_intent_blocks_replay_and_complete_answer_recovers(tmp_path):
    db = tmp_path / 'team.sqlite3'
    store = TeamStore(db)
    request_id = store.begin('default', 'test')
    client = Client('one', 'chatgpt', [])
    store.submission(request_id, client, 'proposal', 1)
    store.close()
    team = provider(tmp_path, [client])
    with pytest.raises(ProviderError, match='available'):
        await ask(team, 'test')
    assert not client.prompts
    await team.close()


@pytest.mark.asyncio
async def test_completed_response_recovers_after_restart(tmp_path):
    client = Client('one', 'chatgpt', ['answer'])
    team = provider(tmp_path, [client])
    await team.send_prompt('test')
    await team.wait_for_response()
    await team.close()
    another = provider(tmp_path, [Client('one', 'chatgpt', [])])
    assert await ask(another, 'test') == 'answer'
    assert not another.participants[0].prompts
    await another.close()


@pytest.mark.asyncio
async def test_checkpoint_is_bounded_and_prompt_size_rejected_before_input(tmp_path):
    client = Client('one', 'chatgpt', [])
    team = provider(tmp_path, [client])
    team.set_checkpoint_context({'items': ['x' * 5000] * 100, 'next_step': 3})
    assert len(team.store.session('default')['checkpoint']) <= 8000
    with pytest.raises(ValueError, match='limit'):
        await team.send_prompt('x' * 100001)
    assert not client.prompts
    await team.close()


@pytest.mark.asyncio
async def test_default_checkpoint_restores_and_reaches_participants(tmp_path):
    first = provider(tmp_path, [Client('one', 'chatgpt', [])])
    first.set_checkpoint_context({'objective': 'Retain task context', 'next_step': 7})
    await first.close()
    client = Client('one', 'chatgpt', ['done'])
    restarted = provider(tmp_path, [client])
    assert await ask(restarted, 'continue') == 'done'
    assert client.checkpoints[-1] == {'objective': 'Retain task context', 'next_step': 7}
    assert 'Retain task context' in client.prompts[0]
    await restarted.close()


@pytest.mark.asyncio
async def test_completed_answer_recovers_even_when_all_members_are_quarantined(tmp_path):
    store = TeamStore(tmp_path / 'team.sqlite3')
    client = Client('one', 'chatgpt', [])
    old = store.begin('another-project', 'uncertain old task')
    store.submission(old, client, 'proposal', 1)
    completed = store.begin('default', 'restore this task')
    store.finish(completed, 'completed', response='durable answer')
    store.close()
    team = provider(tmp_path, [client])
    assert team.member_status['one'] == 'uncertain'
    assert await ask(team, 'restore this task') == 'durable answer'
    assert client.prompts == []
    with pytest.raises(ProviderError, match='available'):
        await team.send_prompt('a different task')
    await team.close()


@pytest.mark.asyncio
async def test_extracted_answer_is_not_resurrected_by_recovery(tmp_path):
    team = provider(tmp_path, [Client('one', 'chatgpt', ['done'])])
    assert await ask(team) == 'done'
    assert not await team.recover_conversation()
    assert not await team.is_response_complete()
    with pytest.raises(ProviderError, match='pending'):
        await team.extract_response()
    await team.close()
    await team.close()  # Cleanup can run from more than one finally block.


@pytest.mark.asyncio
async def test_prompt_budget_preserves_original_with_unicode_and_many_peers(tmp_path):
    clients = [Client(f'profile-{index}', 'chatgpt', ['proposal', 'review', 'done']) for index in range(40)]
    for client in clients:
        client.prompt_limit = 5000
    team = provider(tmp_path, clients)
    team.set_checkpoint_context({'summary': '\u2603' * 1800, 'next_step': 2})
    task = 'Keep this task unchanged: ' + '\u2603' * 2700
    responses = {client.id: '\u2603' * 6000 for client in clients}
    for stage in ('proposal', 'review', 'synthesis'):
        prompt = team._prompt(task, stage, responses)
        assert len(prompt) <= 5000
        assert prompt.endswith(task)
        if stage != 'proposal':
            data = json.loads(prompt.split('UNTRUSTED PEER DATA:\n', 1)[1].split('\nCURRENT REQUEST', 1)[0])
            assert data['omitted_peers'] + len(data['peer_responses']) == len(clients)
            assert all(item['truncated'] for item in data['peer_responses'])
    await team.close()


@pytest.mark.asyncio
async def test_native_prompt_limit_is_validated_before_any_member_input(tmp_path):
    client = Client('one', 'chatgpt', [])
    client.prompt_limit = 2000
    team = provider(tmp_path, [client])
    with pytest.raises(ValueError, match='participant prompt limit'):
        await team.send_prompt('x' * 1950)
    assert not client.prompts
    assert team.store.latest('default') is None
    await team.close()


@pytest.mark.asyncio
async def test_safe_retries_are_bounded_when_every_peer_fails_before_submission(tmp_path):
    def rejected():
        error = ProviderError('Composer missing before submission')
        error.submitted = False
        return error

    clients = [Client(name, 'chatgpt', [rejected(), rejected()]) for name in ('first', 'second')]
    team = provider(tmp_path, clients, max_rounds=3)
    await team.send_prompt('test')
    with pytest.raises(ProviderError, match='paused'):
        await team.wait_for_response()
    assert [len(client.prompts) for client in clients] == [2, 2]
    snapshot = team.status_snapshot()
    assert snapshot['request_status'] == 'paused'
    assert all(item['status'] == 'failed' and 'exhausted' in item['next_action'] for item in snapshot['members'])
    events = team.store.connection.execute("SELECT detail FROM team_events WHERE kind='safe_retry'").fetchall()
    assert len(events) == 2
    assert all(json.loads(row['detail'])['peer_answers'] == [] for row in events)
    await team.close()


@pytest.mark.asyncio
async def test_cancellation_quarantines_only_members_that_started_input(tmp_path):
    entered = asyncio.Event()

    async def never_finishes():
        entered.set()
        await asyncio.Event().wait()

    first = Client('first', 'chatgpt', [never_finishes])
    second = Client('second', 'gemini', [])
    team = provider(tmp_path, [first, second], parallelism=1)
    await team.send_prompt('test')
    await entered.wait()
    await team.close()
    assert first.prompts and not second.prompts
    restarted = provider(tmp_path, [Client('first', 'chatgpt', []), Client('second', 'gemini', [])])
    assert restarted.member_status == {'first': 'uncertain', 'second': 'ready'}
    assert restarted.status_snapshot()['request_status'] == 'paused'
    await restarted.close()


@pytest.mark.asyncio
async def test_member_recovery_confirms_only_saved_round_without_returning_new_answer(tmp_path):
    store = TeamStore(tmp_path / 'team.sqlite3')
    client = Client('one', 'chatgpt', [])
    request = store.begin('default', 'old task')
    store.submission(request, client, 'proposal', 1)
    store.finish(request, 'paused', error='interrupted')
    store.close()
    recoveries = []

    async def recover():
        recoveries.append(True)
        return 'observed old proposal'

    client.recover_response = recover
    team = provider(tmp_path, [client])
    snapshot = await team.recover_members()
    assert snapshot['members'][0]['status'] == 'ready'
    assert snapshot['request_status'] == 'paused'
    assert not snapshot['response_pending']
    assert not await team.recover_conversation()
    with pytest.raises(ProviderError, match='pending'):
        await team.extract_response()
    row = team.store.connection.execute('SELECT status,response FROM team_rounds').fetchone()
    assert dict(row) == {'status': 'completed', 'response': 'observed old proposal'}
    assert not team.store.unresolved()
    await team.recover_members()
    assert len(recoveries) == 1 and not client.prompts
    assert client.requests == [[request, 'proposal', 1]]
    await team.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('reply', ['old completed reply', None])
@pytest.mark.parametrize('prior_reason', ['', 'challenge', 'login_required'])
async def test_startup_recovers_exact_old_session_without_submitting_or_replaying(tmp_path, reply, prior_reason):
    client = Client('one', 'chatgpt', [])
    store = TeamStore(tmp_path / 'team.sqlite3')
    request = store.begin('old-project', 'old task')
    store.submission(request, client, 'part-roads-work', 1)
    store.finish(request, 'paused', error='interrupted')
    if prior_reason:
        store.member_state(client.id, 'blocked', reason=prior_reason, submitted=True)
    store.close()
    reads = []
    async def recover():
        reads.append((client.sessions[-1], client.requests[-1]))
        return reply
    client.recover_response = recover
    team = provider(tmp_path, [client])
    team.use_conversation_session('new-project')
    try:
        await team.preflight(recover_pending=True)
        await team.preflight(recover_pending=True)
        assert reads == [('old-project', [request, 'part-roads-work', 1])]
        assert not client.prompts
        if reply:
            assert client.sessions[-1] == 'new-project' and team.member_status['one'] == 'ready'
            assert not team.store.unresolved()
        else:
            assert team.member_status['one'] == 'uncertain' and team.store.unresolved() == {'one'}
        assert team.store.request(request)['status'] == 'paused'
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_native_readiness_waits_for_desktop_lane_before_starting_probe(tmp_path):
    active, peak = 0, 0
    async def probe():
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(.01)
        active -= 1
        return {'ready': True, 'status': 'ready'}
    members = [Client(str(index), 'chatgpt', []) for index in range(4)]
    for member in members:
        member.probe, member.active_input_mode = probe, 'native'
    team = provider(tmp_path, members)
    try:
        await team.preflight()
        assert peak == 1 and all(value == 'ready' for value in team.member_status.values())
    finally:
        await team.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('sessions', [('other',), ('default', 'default'), ('default', 'other')])
async def test_member_recovery_leaves_ambiguous_and_cross_session_turns_untouched(tmp_path, sessions):
    store = TeamStore(tmp_path / 'team.sqlite3')
    client = Client('one', 'chatgpt', [])
    for session in sessions:
        request = store.begin(session, 'old task')
        store.submission(request, client, 'proposal', 1)
    store.close()

    async def unexpected_recovery():
        pytest.fail('Ambiguous or cross-session receipt must not be observed')

    client.recover_response = unexpected_recovery
    team = provider(tmp_path, [client])
    snapshot = await team.recover_members()
    assert snapshot['members'][0]['status'] == 'uncertain'
    assert len(team.store.unresolved_rows()) == len(sessions)
    assert not client.prompts
    await team.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('recovered', [None, '', ProviderError('Still generating')])
async def test_incomplete_recovery_never_clears_quarantine(tmp_path, recovered):
    store = TeamStore(tmp_path / 'team.sqlite3')
    client = Client('one', 'chatgpt', [])
    request = store.begin('default', 'old task')
    store.submission(request, client, 'proposal', 1)
    store.close()

    async def recover():
        if isinstance(recovered, BaseException):
            raise recovered
        return recovered

    client.recover_response = recover
    team = provider(tmp_path, [client])
    assert (await team.recover_members())['members'][0]['status'] == 'uncertain'
    assert team.store.unresolved() == {'one'}
    assert not client.prompts
    await team.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('submitted,expected', [(True, 'uncertain'), (None, 'uncertain'), (False, 'blocked')])
async def test_authentication_failure_preserves_submission_certainty_across_restart(tmp_path, submitted, expected):
    failure = UserInterventionRequired('Login needed')
    failure.submitted = submitted
    client = Client('one', 'chatgpt', [failure])
    team = provider(tmp_path, [client])
    await team.send_prompt('task')
    with pytest.raises(ProviderError, match='paused'):
        await team.wait_for_response()
    assert team.member_status['one'] == 'blocked'
    await team.close()
    restarted = provider(tmp_path, [Client('one', 'chatgpt', [])])
    assert restarted.member_status['one'] == expected
    await restarted.close()


@pytest.mark.asyncio
async def test_certified_unsubmitted_synthesis_retries_once_with_same_round_identity(tmp_path):
    failure = ProviderError('Send button missing before synthesis submission')
    failure.submitted = False
    first = Client('first', 'chatgpt', ['proposal', 'review', failure, 'final answer'])
    second = Client('second', 'gemini', ['other proposal', 'other review'])
    team = provider(tmp_path, [first, second])
    assert await ask(team, 'task') == 'final answer'
    assert first.requests[-2:] == [[team._request_id, 'synthesis', 1], [team._request_id, 'synthesis', 2]]
    assert len(second.prompts) == 2
    await team.close()


@pytest.mark.asyncio
async def test_pending_peer_stays_in_original_chat_while_healthy_peer_switches_project(tmp_path):
    pending = Client('pending', 'chatgpt', [])
    healthy = Client('healthy', 'gemini', ['proposal', 'review', 'final answer'])
    store = TeamStore(tmp_path / 'team.sqlite3')
    request = store.begin('original', 'Earlier work')
    store.submission(request, pending, 'proposal', 1)
    store.close()
    def keep_pending_chat(key):
        if key != 'original':
            error = ProviderError('Submitted response is still pending in original chat')
            error.submitted = True
            raise error
        pending.sessions.append(key)
    pending.use_conversation_session = keep_pending_chat
    team = provider(tmp_path, [pending, healthy])
    try:
        team.use_conversation_session('new-project')
        assert healthy.sessions[-1] == 'new-project'
        assert team.member_status['pending'] == 'uncertain'
        assert await ask(team, 'New project work') == 'final answer'
        assert not pending.prompts
        assert team.store.unresolved() == {'pending'}
    finally:
        await team.close()


class ProbedClient(Client):
    def __init__(self, ident, provider, answers, health):
        super().__init__(ident, provider, answers)
        self.health = list(health)
        self.probes = 0

    async def probe(self):
        self.probes += 1
        observed = self.health.pop(0) if len(self.health) > 1 else self.health[0]
        if isinstance(observed, BaseException):
            raise observed
        return observed


@pytest.mark.asyncio
async def test_timed_out_turn_is_recovered_automatically_without_resubmission(tmp_path):
    async def timeout():
        await asyncio.sleep(10)

    client = Client('one', 'chatgpt', [timeout])
    recovered_keys = []

    async def recover():
        recovered_keys.append(client.requests[-1])
        return 'confirmed original answer'

    client.recover_response = recover
    team = provider(tmp_path, [client], timeout_seconds=.01)
    assert await ask(team, 'task') == 'confirmed original answer'
    assert len(client.prompts) == 1
    assert recovered_keys == [[team._request_id, 'proposal', 1]]
    assert not team.store.unresolved()
    event = team.store.connection.execute("SELECT detail FROM team_events WHERE kind='member_recovered'").fetchone()
    assert json.loads(event['detail'])['automatic'] is True
    await team.close()


@pytest.mark.asyncio
async def test_automatic_recovery_timeout_is_bounded_and_never_sends_again(tmp_path):
    client = Client('one', 'chatgpt', [ProviderError('Connection lost after submission')])
    recoveries = []

    async def recover():
        recoveries.append(True)
        await asyncio.sleep(10)

    client.recover_response = recover
    team = provider(tmp_path, [client], timeout_seconds=.01)
    await team.send_prompt('task')
    with pytest.raises(ProviderError, match='paused'):
        await team.wait_for_response()
    assert len(client.prompts) == len(recoveries) == 1
    assert team.store.unresolved() == {'one'}
    assert team.member_status['one'] == 'uncertain'
    await team.close()


@pytest.mark.asyncio
async def test_preflight_loading_retries_are_finite_and_dont_submit(tmp_path):
    client = ProbedClient('one', 'chatgpt', [], [{'status': 'unavailable', 'ready': False}])
    team = provider(tmp_path, [client])
    snapshot = await team.preflight(readiness_retries=2, backoff_seconds=0)
    assert client.probes == 3 and not client.prompts
    assert snapshot['members'][0]['status'] == 'unavailable'
    assert snapshot['members'][0]['health']['attempts'] == 3
    assert team.store.latest('default') is None
    client.health = [{'status': 'ready', 'ready': True}]
    assert (await team.preflight(backoff_seconds=0))['members'][0]['status'] == 'ready'
    assert client.probes == 4
    await team.close()


@pytest.mark.asyncio
async def test_preflight_pending_receipt_is_quarantined_across_restart(tmp_path):
    client = ProbedClient('one', 'chatgpt', [], [
        {'status': 'pending', 'ready': False}, {'status': 'ready', 'ready': True}])
    team = provider(tmp_path, [client])
    try:
        snapshot = await team.preflight(backoff_seconds=0)
        assert snapshot['members'][0]['status'] == 'uncertain'
        assert snapshot['members'][0]['submitted'] is True
        assert client.probes == 1 and not client.prompts
        await team.preflight(backoff_seconds=0)
        assert client.probes == 1
    finally:
        await team.close()
    restarted = provider(tmp_path, [client])
    try:
        assert (await restarted.preflight())['members'][0]['status'] == 'uncertain'
        assert client.probes == 1 and not client.prompts
    finally:
        await restarted.close()


@pytest.mark.asyncio
async def test_uncertain_console_intervention_is_not_retried_as_page_loading(tmp_path):
    from app.browser.native_console import NativeConsoleIntervention
    client = ProbedClient('one', 'chatgpt', [], [
        NativeConsoleIntervention('Resolve the prior uncertain console operation', submitted=True),
        {'status': 'ready', 'ready': True}])
    team = provider(tmp_path, [client])
    try:
        snapshot = await team.preflight(backoff_seconds=0)
        assert snapshot['members'][0]['status'] == 'blocked'
        assert snapshot['members'][0]['reason'] == 'intervention'
        assert snapshot['members'][0]['submitted'] is True
        await team.preflight(backoff_seconds=0)
        assert client.probes == 1 and not client.prompts
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_explicit_console_setup_health_rejoins_after_setup_is_completed(tmp_path):
    client = ProbedClient('one', 'chatgpt', [], [
        {'status': 'intervention', 'ready': False, 'submitted': False},
        {'status': 'ready', 'ready': True}])
    team = provider(tmp_path, [client])
    try:
        assert (await team.preflight(backoff_seconds=0))['members'][0]['status'] == 'blocked'
        assert client.probes == 1
        assert (await team.preflight(backoff_seconds=0))['members'][0]['status'] == 'ready'
        assert client.probes == 2 and not client.prompts
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_preflight_recovers_loading_without_dropping_failure_diagnostics(tmp_path):
    client = ProbedClient('one', 'chatgpt', ['done'], [
        ProviderError('Console is loading'), {'status': 'ready', 'ready': True}])
    team = provider(tmp_path, [client])
    snapshot = await team.preflight(backoff_seconds=0)
    assert snapshot['members'][0]['status'] == 'ready'
    assert snapshot['members'][0]['health']['attempts'] == 2
    assert client.probes == 2 and not client.prompts
    await team.send_prompt('task')
    await team.wait_for_response()
    assert await team.extract_response() == 'done'
    await team.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('blocked', ['login_required', 'challenge'])
async def test_preflight_rejoins_after_owner_finishes_authentication(tmp_path, blocked):
    client = ProbedClient('one', 'chatgpt', [], [
        {'status': blocked, 'ready': False, 'problem': 'Complete this profile manually'},
        {'status': 'ready', 'ready': True}])
    team = provider(tmp_path, [client])
    snapshot = await team.preflight(backoff_seconds=0)
    assert snapshot['members'][0]['status'] == 'blocked' and client.probes == 1
    assert snapshot['members'][0]['submitted'] is False
    assert (await team.preflight())['members'][0]['status'] == 'ready'
    assert client.probes == 2 and not client.prompts
    await team.close()


@pytest.mark.asyncio
async def test_unsubmitted_authentication_block_survives_restart_then_rejoins(tmp_path):
    client = ProbedClient('one', 'chatgpt', [], [{'status': 'login_required', 'ready': False}])
    team = provider(tmp_path, [client])
    await team.preflight()
    await team.close()
    signed_in = ProbedClient('one', 'chatgpt', ['done'], [{'status': 'ready', 'ready': True}])
    restarted = provider(tmp_path, [signed_in])
    assert restarted.member_status['one'] == 'blocked'
    assert await ask(restarted, 'new task after login') == 'done'
    assert signed_in.probes == 1
    await restarted.close()


@pytest.mark.asyncio
async def test_ready_probe_never_clears_ambiguous_submission(tmp_path):
    client = ProbedClient('one', 'chatgpt', [], [{'status': 'ready', 'ready': True}])
    store = TeamStore(tmp_path / 'team.sqlite3')
    request = store.begin('default', 'pending task')
    store.submission(request, client, 'proposal', 1)
    store.close()
    team = provider(tmp_path, [client])
    assert (await team.preflight())['members'][0]['status'] == 'uncertain'
    assert client.probes == 0 and not client.prompts
    assert team.store.unresolved() == {'one'}
    await team.close()


@pytest.mark.asyncio
async def test_rate_limit_remains_blocked_across_readiness_checks_and_restart(tmp_path):
    client = ProbedClient('one', 'chatgpt', [], [
        {'status': 'rate_limited', 'ready': False}, {'status': 'ready', 'ready': True}])
    team = provider(tmp_path, [client])
    await team.preflight()
    await team.preflight()
    assert client.probes == 1
    assert team.member_status['one'] == 'blocked'
    await team.close()
    restarted = provider(tmp_path, [client])
    await restarted.preflight()
    assert restarted.member_status['one'] == 'blocked' and client.probes == 1
    await restarted.close()


@pytest.mark.asyncio
async def test_unsigned_member_stays_skipped_until_next_preflight(tmp_path):
    joining = ProbedClient('joining', 'chatgpt', ['recovered answer', 'final answer'], [
        {'status': 'login_required', 'ready': False, 'problem': 'Login required'},
        {'status': 'ready', 'ready': True}])
    helper = Client('helper', 'gemini', ['proposal', 'helpful diagnosis', 'final answer'])
    team = provider(tmp_path, [joining, helper])
    assert await ask(team, 'task') == 'final answer'
    assert not joining.prompts and joining.probes == 1
    assert 'Login required' in helper.prompts[1]
    await team.preflight()
    assert team.member_status['joining'] == 'ready'
    assert joining.probes == 2
    await team.close()


@pytest.mark.asyncio
async def test_preflight_permission_denial_is_persisted_and_not_retried(tmp_path):
    client = ProbedClient('one', 'chatgpt', [], [PermissionError('Owner denied input')])
    team = provider(tmp_path, [client])
    with pytest.raises(PermissionError):
        await team.preflight()
    assert team.status_snapshot()['members'][0]['reason'] == 'denied'
    await team.preflight()
    assert client.probes == 1 and not client.prompts
    await team.close()


@pytest.mark.asyncio
async def test_second_request_probes_again_after_consuming_first_answer(tmp_path):
    client = ProbedClient('one', 'chatgpt', ['first'], [
        {'status': 'ready', 'ready': True}, {'status': 'login_required', 'ready': False}])
    team = provider(tmp_path, [client])
    assert await ask(team, 'first task') == 'first'
    with pytest.raises(ProviderError, match='available'):
        await team.send_prompt('second task')
    assert len(client.prompts) == 1 and client.probes == 2
    await team.close()


@pytest.mark.asyncio
async def test_rate_limit_can_rejoin_after_cooldown_by_read_only_probe(tmp_path):
    client = ProbedClient('one', 'chatgpt', [], [
        {'status': 'rate_limited', 'ready': False}, {'status': 'ready', 'ready': True}])
    team = provider(tmp_path, [client])
    try:
        await team.preflight()
        with team.store.connection:
            team.store.connection.execute('UPDATE team_members SET updated=updated-301 WHERE id=?', ('one',))
        await team.preflight()
        assert team.member_status['one'] == 'ready' and client.probes == 2
        assert not client.prompts
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_explicit_rate_limit_recheck_sends_no_prompt(tmp_path):
    client = ProbedClient('one', 'chatgpt', [], [
        {'status': 'rate_limited', 'ready': False}, {'status': 'ready', 'ready': True}])
    team = provider(tmp_path, [client])
    try:
        await team.preflight()
        await team.preflight(recheck_rate_limits=True)
        assert team.member_status['one'] == 'ready' and client.probes == 2
        assert not client.prompts
    finally:
        await team.close()
