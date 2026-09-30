"""Exercise fallback scripts in a real isolated browser with all requests fulfilled locally."""
import json

import pytest
from playwright.async_api import async_playwright

from app.browser.console_protocol import wrap_console_expression, parse_console_receipt
from app.browser.dom_observation import OBSERVE_DOM, ACT_DOM


@pytest.mark.asyncio
async def test_dom_fallback_in_real_browser_without_copy():
    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(channel='chrome', headless=True)
        except Exception as error:
            pytest.skip('Isolated Chrome unavailable: ' + type(error).__name__)
        try:
            page = await browser.new_page()
            await page.route('**/*', lambda route: route.fulfill(content_type='text/html', body='''
                <button id="play" onclick="window.clicks=(window.clicks||0)+1">Play</button>
                <input placeholder="Search" value="private draft value">
                <input type="password" value="secret password value">
                <div contenteditable="true">private editable value</div><p>Visible page text</p>'''))
            await page.goto('https://brainless-test.invalid/')
            logs = []
            page.on('console', lambda message: logs.append(message.text))
            token, nonce = 'b'*32, 'a'*32
            expression = OBSERVE_DOM.replace('__TOKEN__', json.dumps(token))
            await page.evaluate(wrap_console_expression(expression, nonce))
            receipts = [parse_console_receipt(line, nonce) for line in logs if line.startswith('BRAINLESS_RESULT:')]
            assert len(receipts) == 1 and receipts[0]['ok']
            observation = receipts[0]['value']
            assert observation['available']
            text = json.dumps(observation)
            assert 'private draft value' not in text
            assert 'private editable value' not in text
            assert 'secret password value' not in text
            target = next(item for item in observation['elements'] if item['label'] == 'Play')['runtime_id']
            arguments = {'token': token, 'target': target, 'action': 'click', 'text': None}
            action = ACT_DOM.replace('__ARGS__', json.dumps(arguments))
            assert (await page.evaluate(action))['performed']
            assert await page.evaluate('window.clicks') == 1
            assert not (await page.evaluate(action))['performed']
            assert await page.evaluate('window.clicks') == 1
        finally:
            await browser.close()
