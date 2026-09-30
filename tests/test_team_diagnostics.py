import json

import pytest

from app.browser.team_diagnostics import matches_challenge, run_live_smoke
from app.providers.collaborative import CollaborativeProvider


class Member:
    def __init__(self, name, answer):
        self.id = name
        self.provider_name = name
        self.answer = answer
        self.prompts = []

    async def ask(self, prompt):
        self.prompts.append(prompt)
        return self.answer


@pytest.mark.asyncio
async def test_smoke_verifies_each_provider_and_persists_a_labelled_report(tmp_path):
    exact = json.dumps({'nonce': 'fresh-test', 'sum': 42})
    clients = [Member('chatgpt', exact), Member('gemini', exact)]
    team = CollaborativeProvider(clients, tmp_path / 'team.sqlite3', progress=lambda _: None)
    try:
        report = await run_live_smoke(team, tmp_path, nonce='fresh-test', driver='FakeTransport', progress=lambda _: None)
        assert report['status'] == 'passed' and report['final_verified']
        assert all(item['verified'] for item in report['members'])
        assert len(clients[0].prompts) == 3 and len(clients[1].prompts) == 2
        saved = json.loads((tmp_path / 'data/browser-team/diagnostics/smoke-fresh-test.json').read_text())
        assert saved['driver'] == 'FakeTransport' and saved['status'] == 'passed'
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_smoke_does_not_pass_with_only_one_provider(tmp_path):
    team = CollaborativeProvider([Member('chatgpt', '{"nonce":"test","sum":42}')],
                                 tmp_path / 'team.sqlite3', progress=lambda _: None)
    try:
        assert (await run_live_smoke(team, tmp_path, nonce='test', progress=lambda _: None))['status'] == 'partial'
    finally:
        await team.close()


@pytest.mark.asyncio
async def test_smoke_reports_partial_when_a_selected_profile_never_launched(tmp_path):
    answer = '{"nonce":"test","sum":42}'
    team = CollaborativeProvider([Member('chatgpt', answer), Member('gemini', answer)],
                                 tmp_path / 'team.sqlite3', progress=lambda _: None)
    try:
        report = await run_live_smoke(team, tmp_path, nonce='test', progress=lambda _: None,
                                     fleet_status={'failures': {'missing-profile': 'Launch failed'}})
        assert report['final_verified'] and all(item['verified'] for item in report['members'])
        assert report['status'] == 'partial'
    finally:
        await team.close()


@pytest.mark.parametrize('response', ['{"nonce":"old","sum":42}', '{"nonce":"test","sum":true}',
    '{"nonce":"test","sum":42,"extra":1}', 'The answer is 42', '```json\n{"nonce":"test","sum":42}\n```'])
def test_smoke_rejects_stale_incorrect_or_noncontract_replies(response):
    assert not matches_challenge(response, 'test')
