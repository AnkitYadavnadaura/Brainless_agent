import asyncio
import json

import pytest

from app.autonomy.task_analysis import analyse_task
from app.browser.team_board import TeamBoard
from app.providers.collaborative import CollaborativeProvider, TeamStore
from app.providers.team_parts import validate_parts
from tests.test_collaborative_provider import ask
from app.providers.json_response import decode_json_response


def test_json_code_fence_preserves_escapes_and_rejects_surrounding_prose():
    value = {'name': 'The "quoted" building'}
    assert decode_json_response('```json\n' + json.dumps(value) + '\n```') == value
    with pytest.raises(ValueError):
        decode_json_response('Some prose\n```json\n{}\n```')


def plan():
    return {'software': 'Blender', 'assumptions': ['metres, shared world origin'], 'parts': [
        {'id': 'roads', 'task': 'Plan roads', 'depends_on': [], 'acceptance': 'road dimensions'},
        {'id': 'terrain', 'task': 'Plan terrain', 'depends_on': [], 'acceptance': 'terrain bounds'},
        {'id': 'buildings', 'task': 'Place buildings', 'depends_on': ['roads', 'terrain'], 'acceptance': 'no road overlap'}]}


@pytest.mark.parametrize('fault', ['cycle', 'unknown', 'duplicate', 'empty', 'bad_assumption'])
def test_invalid_dependency_plans_are_rejected(fault):
    value = plan()
    if fault == 'cycle':
        value['parts'][0]['depends_on'] = ['buildings']
    elif fault == 'unknown':
        value['parts'][0]['depends_on'] = ['missing']
    elif fault == 'duplicate':
        value['parts'][1]['id'] = 'roads'
    elif fault == 'empty':
        value['parts'] = []
    else:
        value['assumptions'] = 'not a list'
    with pytest.raises(ValueError):
        validate_parts(value)


class PartClient:
    provider_name = 'chatgpt'

    def __init__(self, ident, entered, both):
        self.id, self.entered, self.both = ident, entered, both
        self.prompts = []

    async def ask(self, prompt):
        self.prompts.append(prompt)
        if 'Analyse the current request and divide' in prompt:
            return json.dumps(plan())
        if 'Synthesize the best supported' in prompt:
            return '{"ordered_steps":[]}'
        data = json.loads(prompt.split('ASSIGNMENT DATA:\n')[1].split('\nCURRENT REQUEST:')[0])
        part = data['part']['id']
        if 'Solve your assigned' in prompt and part in {'roads', 'terrain'}:
            self.entered.add(part)
            if len(self.entered) == 2:
                self.both.set()
            await asyncio.wait_for(self.both.wait(), 1)
        if part == 'buildings':
            assert set(data['dependencies']) == {'roads', 'terrain'}
        messages = [{'to': 'b', 'text': 'Keep buildings away from road corridor'}] if part == 'roads' and 'Solve your assigned' in prompt else []
        return json.dumps({'result': 'Proposed ' + part, 'messages': messages})


@pytest.mark.asyncio
async def test_parts_run_concurrently_honour_dependencies_and_deliver_tagged_messages(tmp_path):
    entered, both = set(), asyncio.Event()
    a, b = PartClient('a', entered, both), PartClient('b', entered, both)
    team = CollaborativeProvider([a, b], tmp_path/'team.sqlite3', work_mode='parts', progress=lambda _: None)
    team.use_conversation_session('city')
    try:
        assert await ask(team, 'Create a city in Blender; return JSON') == '{"ordered_steps":[]}'
        assert entered == {'roads', 'terrain'}
        board = json.loads(team.board.path('city').read_text(encoding='utf-8'))
        assert board['status'] == 'answer_completed'
        assert len(board['tasks']) == 3
        assert all(part['status'] == 'reviewed' for part in board['tasks'])
        assert all(message['delivered'] for message in board['messages'])
        assert any('TEAM BOARD MESSAGE' in prompt and 'road corridor' in prompt for prompt in b.prompts)
        work = next(prompt for prompt in a.prompts if 'Solve your assigned' in prompt)
        review = next(prompt for prompt in b.prompts if 'Review and correct' in prompt)
        assert '"id": "roads"' in work and '"id": "roads"' in review
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_unsigned_tab_is_skipped_for_entire_task(tmp_path):
    from tests.test_collaborative_provider import Client
    signed = Client('signed', 'chatgpt', ['proposal', 'final'])
    unsigned = Client('unsigned', 'gemini', [])
    checks = []
    async def probe():
        checks.append(True)
        return {'ready': False, 'status': 'login_required'}
    unsigned.probe = probe
    team = CollaborativeProvider([signed, unsigned], tmp_path/'team.sqlite3', max_rounds=1, progress=lambda _: None)
    try:
        assert await ask(team) == 'final'
        assert not unsigned.prompts and len(checks) == 1
        assert team.status_snapshot()['active_count'] == 1
    finally:
        await team.close()


def test_board_mail_survives_restart_and_cannot_target_unknown_members(tmp_path):
    database = tmp_path/'team.sqlite3'
    store = TeamStore(database)
    board = TeamBoard(store.connection, tmp_path/'boards')
    board.begin('session', 'request', ['a', 'b'])
    board.post('request', 'user', '*', 'Use metre coordinates')
    with pytest.raises(ValueError):
        board.post('request', 'user', 'unknown', 'message')
    store.close()
    store = TeamStore(database)
    try:
        board = TeamBoard(store.connection, tmp_path/'boards')
        message = board.inbox('request', 'a')[0]
        board.acknowledge('request', 'b', [message['id']])
        assert board.inbox('request', 'a')  # Cannot acknowledge another tab's mail.
        board.acknowledge('request', 'a', [message['id']])
        assert not board.inbox('request', 'a') and board.inbox('request', 'b')
        assert board.latest('session') == 'request'
        board.begin('session', 'next-request', ['a', 'b'])
        unread = board.inbox('next-request', 'b')
        assert unread and unread[0]['body'] == 'Use metre coordinates'
        board.acknowledge('next-request', 'b', [unread[0]['id']])
        assert not board.inbox('request', 'b')
    finally:
        store.close()


@pytest.mark.parametrize('task,software,workflow', [
    ('Create a detailed 3D city', 'Blender', 'blender'),
    ('Create a village in Blender', 'Blender', 'blender'),
    ('Create a 3D city in Unreal Engine', 'Unreal Engine', 'general'),
    ('Create a house in Maya', 'Maya', 'general'),
    ('Explain sorting algorithms', 'none', 'general')])
def test_software_analysis_preserves_explicit_choice(task, software, workflow):
    result = analyse_task(task)
    assert result['software'] == software and result['workflow'] == workflow


@pytest.mark.asyncio
@pytest.mark.parametrize('submitted', [True, False])
async def test_part_handoff_only_when_original_was_certified_unsent(tmp_path, submitted):
    from app.providers.base_provider import ProviderError
    class Member:
        provider_name = 'chatgpt'
        def __init__(self, ident):
            self.id, self.parts = ident, []
        async def ask(self, prompt):
            if 'Analyse the current request and divide' in prompt:
                return json.dumps(plan())
            if 'Synthesize the best supported' in prompt:
                return 'final'
            data = json.loads(prompt.split('ASSIGNMENT DATA:\n')[1].split('\nCURRENT REQUEST:')[0])
            part = data['part']['id']
            self.parts.append(part)
            if self.id == 'a' and part == 'roads':
                error = ProviderError('Browser disconnected')
                error.submitted = submitted
                raise error
            return json.dumps({'result': 'proposed ' + part, 'messages': []})
    a, b = Member('a'), Member('b')
    team = CollaborativeProvider([a, b], tmp_path/'team.sqlite3', work_mode='parts', max_rounds=1,
                                 max_peer_repairs=0, progress=lambda _: None)
    try:
        if submitted:
            with pytest.raises(ProviderError, match='parts are blocked'):
                await ask(team, 'Build city in Blender')
            assert a.parts == ['roads'] and b.parts == ['terrain']
            assert team.member_status['a'] == 'uncertain'
        else:
            assert await ask(team, 'Build city in Blender') == 'final'
            assert a.parts == ['roads'] and b.parts == ['terrain', 'roads', 'buildings']
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_cli_board_messages_do_not_launch_browsers(tmp_path):
    from app.browser.team_cli import run_browser_team
    def forbidden(*args, **kwargs):
        pytest.fail('Board access must not open browsers')
    store = TeamStore(tmp_path/'data/browser-team/team.sqlite3')
    board = TeamBoard(store.connection, tmp_path/'data/browser-team/boards')
    board.begin('city', 'request', ['worker'])
    store.close()
    output = []
    assert await run_browser_team(['message', '--session', 'city', '--to', 'worker', 'Check road boundaries'],
        tmp_path, discover=forbidden, fleet_factory=forbidden, progress=output.append) == 0
    assert await run_browser_team(['board', '--session', 'city'], tmp_path,
        discover=forbidden, fleet_factory=forbidden, progress=output.append) == 0
    assert json.loads(output[-1])['messages'][0]['body'] == 'Check road boundaries'
def test_json_presentation_unwrap_preserves_data_and_rejects_prose():
    from app.providers.json_response import unwrap_json_code_block
    raw = json.dumps({'description': 'The "quoted" landmark', 'count': 24})
    assert unwrap_json_code_block('```json\n' + raw + '\n```') == raw
    for text in ('Here is JSON:\n```json\n' + raw + '\n```', '```python\nprint(1)\n```', '```json\n{"bad":}\n```'):
        assert unwrap_json_code_block(text) == text


@pytest.mark.asyncio
@pytest.mark.parametrize('uncertain', [False, True])
async def test_reuse_complete_parts_requires_exact_request_and_resolved_receipts(tmp_path, uncertain):
    from app.providers.base_provider import ProviderError
    member = PartClient('a', set(), asyncio.Event())
    team = CollaborativeProvider([member], tmp_path/'team.sqlite3', work_mode='parts', max_rounds=1, progress=lambda _: None)
    original = 'Build the same building in Blender'
    prior = team.store.begin('default', original)
    team.board.begin('default', prior, ['a'])
    team.board.plan(prior, plan())
    for part in plan()['parts']:
        team.board.task(prior, part['id'], 'answered', owner='a', result='Saved ' + part['id'])
    if uncertain:
        team.store.submission(prior, member, 'synthesis', 1)
    team.store.finish(prior, 'paused')
    try:
        if uncertain:
            with pytest.raises(ProviderError, match='uncertain submissions'):
                await ask(team, original)
            assert not member.prompts
        else:
            assert await ask(team, original) == '{"ordered_steps":[]}'
            assert len(member.prompts) == 1 and 'Saved roads' in member.prompts[0]
    finally:
        await team.close()
