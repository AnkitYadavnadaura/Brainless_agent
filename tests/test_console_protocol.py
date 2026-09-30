"""Exercise real asynchronous JavaScript and native receipt collection without sending anything."""
import asyncio
import json
import shutil
import subprocess

import pytest

from app.browser.console_protocol import wrap_console_expression, parse_console_receipt
from app.browser.dom_observation import OBSERVE_DOM, ACT_DOM
from app.browser.native_console import NativeConsoleIntervention
from tests.test_native_console import Desktop, owned, transport


@pytest.mark.parametrize('mode', ['disappears_after_await', 'missing', 'throws'])
@pytest.mark.parametrize('fails', [False, True])
def test_async_receipt_executes_once_even_without_copy(mode, fails):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    nonce = 'a' * 32
    expression = "(async()=>{runs++;await Promise.resolve();" + (
        "throw Error('sample failure');" if fails else "return {confirmed:true};") + "})()"
    wrapped = wrap_console_expression(expression, nonce)
    script = r'''
const vm = require('vm');
const logs=[],copies=[];
const context={runs:0,Promise,console:{log:s=>logs.push(s)}};
const mode=MODE;
if(mode!=='missing')context.copy=s=>{if(mode==='throws')throw Error('clipboard blocked');copies.push(s)};
vm.createContext(context);
const result=vm.runInContext(SOURCE,context);
delete context.copy;
result.then(()=>process.stdout.write(JSON.stringify({logs,copies,runs:context.runs})));
'''.replace('MODE', json.dumps(mode)).replace('SOURCE', json.dumps(wrapped))
    result = subprocess.run([node], input=script, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data['runs'] == 1
    receipts = [line for line in data['logs'] if line.startswith('BRAINLESS_RESULT:')]
    assert len(receipts) == 1
    receipt = parse_console_receipt(receipts[0], nonce)
    assert receipt['ok'] is not fails
    assert receipt['steps'][0] == 'execution.started'
    assert receipt['steps'][-1] == ('execution.failed' if fails else 'execution.completed')
    assert len(data['copies']) == (1 if mode == 'disappears_after_await' else 0)


def test_receipt_parser_rejects_foreign_malformed_or_oversized_results():
    nonce = 'a' * 32
    assert parse_console_receipt(json.dumps({'brainless_nonce': 'b'*32}), nonce) is None
    assert parse_console_receipt('BRAINLESS_RESULT:' + nonce + ':not json', nonce) is None
    assert parse_console_receipt('x'*2_000_001, nonce) is None


@pytest.mark.asyncio
async def test_transport_uses_console_receipt_without_reexecuting_script():
    backend = Desktop()
    backend.respond = False
    backend.console_receipt = lambda hwnd, nonce: 'BRAINLESS_RESULT:' + nonce + ':' + json.dumps({
        'brainless_nonce': nonce, 'ok': True, 'value': {'sent': True},
        'steps': ['execution.started', 'gmail.send.verified', 'execution.completed']})
    client = transport(backend)
    hwnd = await owned(client)
    assert await client.evaluate(hwnd, 'chromium', '({sent:true})') == {'sent': True}
    assert sum(item[0] == 'keys' and item[2] == ('enter',) for item in backend.trace) == 1
    assert backend.clipboard == 'private previous clipboard'
    assert client.console_diagnostics[hwnd]['receipt_channel'] == 'console'
    assert 'gmail.send.verified' in client.console_diagnostics[hwnd]['steps']


@pytest.mark.asyncio
async def test_existing_focused_console_is_not_toggled_closed():
    backend = Desktop()
    backend.console_focused = lambda *_: True
    client = transport(backend)
    hwnd = await owned(client)
    await client.evaluate(hwnd, 'chromium', '({ok:true})')
    assert not any(item[0] == 'keys' and item[2] == ('ctrl', 'shift', 'j') for item in backend.trace)


@pytest.mark.asyncio
async def test_foreign_console_receipt_cannot_confirm_or_replay_an_action():
    backend = Desktop()
    backend.respond = False
    backend.console_receipt = lambda *_: json.dumps({'brainless_nonce': 'b'*32, 'ok': True, 'value': {'sent': True}})
    client = transport(backend)
    hwnd = await owned(client)
    with pytest.raises(NativeConsoleIntervention):
        await client.evaluate(hwnd, 'chromium', '({sent:true})')
    with pytest.raises(NativeConsoleIntervention):
        await client.evaluate(hwnd, 'chromium', '({sent:true})')
    assert sum(item[0] == 'keys' and item[2] == ('enter',) for item in backend.trace) == 1
    assert client.console_diagnostics[hwnd]['status'] == 'receipt_missing'


@pytest.mark.parametrize('source', [OBSERVE_DOM.replace('__TOKEN__', '"a"'), ACT_DOM.replace('__ARGS__', '{}')])
def test_dom_fallback_scripts_parse(source):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    result = subprocess.run([node, '--check'], input=source, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
