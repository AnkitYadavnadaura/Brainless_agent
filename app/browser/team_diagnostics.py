"""Repeatable website smoke checks with durable, explicit evidence reports."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid


def write_report(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=str), encoding='utf-8')
    temporary.replace(path)
    return str(path)


def matches_challenge(response: str, nonce: str) -> bool:
    try:
        answer = json.loads(response)
    except (TypeError, ValueError):
        return False
    return isinstance(answer, dict) and set(answer) == {'nonce', 'sum'} and answer['nonce'] == nonce and type(answer['sum']) is int and answer['sum'] == 42


async def run_live_smoke(team, root: Path, *, fleet_status=None, driver='unknown', progress=print, nonce=None):
    """Exercise actual configured clients; mocks are labelled by their driver.

    Passing requires fresh valid proposals and reviews from every selected
    participant, both provider families, and a valid final synthesis.
    """
    nonce = nonce or uuid.uuid4().hex
    session = 'smoke-' + nonce
    path = Path(root) / 'data/browser-team/diagnostics' / (session + '.json')
    report = dict(kind='browser_team_smoke', session=session, driver=driver,
                  started=datetime.now(timezone.utc).isoformat(), status='running',
                  fleet=fleet_status or {}, members=[], final_verified=False)
    write_report(path, report)
    try:
        team.use_conversation_session(session)
        team.set_checkpoint_context({'purpose': 'Non-sensitive browser collaboration smoke test', 'nonce': nonce})
        await team.open()
        await team.send_prompt('This is a harmless browser-team integration test. Calculate 19 + 23. '
            'Review peer answers when supplied, then return only this exact JSON object: '
            + json.dumps({'nonce': nonce, 'sum': 42}) + '. Preserve the nonce exactly; add no other fields or prose.')
        await team.wait_for_response()
        answer = await team.extract_response()
        report['final_verified'] = matches_challenge(answer, nonce)
        request = team.store.latest(session)
        rounds = [dict(row) for row in team.store.connection.execute(
            'SELECT member_id,provider,round,status,response FROM team_rounds WHERE request_id=?', (request['id'],))]
        for member in team.participants:
            own = [row for row in rounds if row['member_id'] == member.id]
            checks = [{'round': row['round'], 'status': row['status'],
                       'verified': row['status'] == 'completed' and matches_challenge(row['response'], nonce)} for row in own]
            proposal_ok = any(row['round'] in ('proposal', 'retry') and row['verified'] for row in checks)
            review_ok = any(row['round'].startswith('review-') and row['verified'] for row in checks)
            report['members'].append(dict(id=member.id, provider=member.provider_name,
                verified=proposal_ok and review_ok, rounds=checks,
                status=team.member_status[member.id], input_mode=getattr(member, 'active_input_mode',
                                                                       getattr(member, 'input_mode', 'unspecified'))))
        families = {row['provider'] for row in report['members'] if row['verified']}
        report['status'] = ('passed' if report['members'] and all(row['verified'] for row in report['members'])
                            and {'chatgpt', 'gemini'} <= families and report['final_verified']
                            and not report['fleet'].get('failures') else 'partial')
    except asyncio.CancelledError:
        report['status'] = 'interrupted'
        raise
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = f'{type(error).__name__}: {error}'[:2000]
    finally:
        report['health'] = team.status_snapshot()
        report['finished'] = datetime.now(timezone.utc).isoformat()
        write_report(path, report)
        progress(f"Browser smoke test: {report['status']}. Report: {path}")
    return report
