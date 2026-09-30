import asyncio
import json
from types import SimpleNamespace

import pytest

from app.browser.chromium_leader import ChromiumLeader, ChromiumTransport
from app.providers.native_website import DOM_PROGRAM, NativeClientError


class Page:
    def __init__(self):
        self.url = 'about:blank'
        self.closed = False
        self.calls = []
        self.failure = None

    def is_closed(self):
        return self.closed

    async def goto(self, url, **kwargs):
        self.url = url

    async def evaluate(self, program, payload):
        self.calls.append((program, payload))
        if self.failure:
            raise self.failure
        return {'bound': True, 'ready': True, 'busy': False, 'url': self.url}


class Driver:
    def __init__(self):
        self.chromium = self
        self.context = self
        self.pages = []
        self.stopped = self.closed = False
        self.launches = []
        self.entered = self.release = None

    async def start(self):
        return self

    async def launch_persistent_context(self, **kwargs):
        self.launches.append(kwargs)
        if self.entered:
            self.entered.set()
            await self.release.wait()
        return self

    async def new_page(self):
        page = Page()
        self.pages.append(page)
        return page

    async def close(self):
        self.closed = True

    async def stop(self):
        self.stopped = True


@pytest.mark.asyncio
async def test_signed_out_leader_provider_is_not_opened(tmp_path):
    driver = Driver()
    leader = ChromiumLeader(tmp_path, playwright_factory=lambda: driver, progress=lambda _: None)
    leader.excluded_providers = {'chatgpt'}
    try:
        clients = await leader.start()
        assert [client.id for client in clients] == ['chromium-leader:gemini']
        assert clients[0].tab_index == 2
        assert [page.url for page in driver.pages] == ['https://gemini.google.com/app']
        assert (await clients[0].probe())['ready']
    finally:
        await leader.close()


@pytest.mark.asyncio
async def test_managed_leader_pins_two_website_tabs_in_an_isolated_profile(tmp_path):
    driver = Driver()
    leader = ChromiumLeader(tmp_path, playwright_factory=lambda: driver, progress=lambda _: None)
    clients = await leader.start()
    assert [client.id for client in clients] == ['chromium-leader:chatgpt', 'chromium-leader:gemini']
    assert all(client.team_role == 'leader' and client.active_input_mode == 'playwright' for client in clients)
    assert all([(await client.probe())['ready'] for client in clients])
    assert [page.url for page in driver.pages] == ['https://chatgpt.com/', 'https://gemini.google.com/app']
    assert driver.launches[0]['user_data_dir'] == str(tmp_path / 'data/chromium-leader')
    assert driver.launches[0]['chromium_sandbox']
    assert await leader.start() is clients
    assert len(driver.launches) == 1
    await leader.close()
    assert driver.closed and driver.stopped


@pytest.mark.asyncio
async def test_managed_transport_rejects_code_and_cross_provider_navigation():
    page = Page()
    transport = ChromiumTransport({1: page})
    with pytest.raises(ValueError):
        await transport.evaluate(1, 'chromium', 'fetch("https://example.com")', tab_index=1)
    with pytest.raises(ValueError):
        await transport.navigate(1, 'https://gemini.google.com/app', tab_index=1)
    with pytest.raises(NativeClientError):
        await transport.navigate(9, 'https://chatgpt.com/', tab_index=1)
    assert not page.calls


@pytest.mark.asyncio
@pytest.mark.parametrize('action,submitted', [('observe', False), ('prepare', False), ('submit', True)])
async def test_managed_transport_preserves_submission_certainty(action, submitted):
    page = Page()
    page.url = 'https://chatgpt.com/'
    page.failure = RuntimeError('Browser disconnected')
    transport = ChromiumTransport({1: page})
    script = '(' + DOM_PROGRAM + ')(' + json.dumps({'origin': 'https://chatgpt.com', 'action': action}) + ')'
    with pytest.raises(NativeClientError) as failure:
        await transport.evaluate(1, 'chromium', script, tab_index=1)
    assert failure.value.submitted is submitted


@pytest.mark.asyncio
async def test_cancelled_managed_launch_waits_for_context_and_closes_it(tmp_path):
    driver = Driver()
    driver.entered, driver.release = asyncio.Event(), asyncio.Event()
    leader = ChromiumLeader(tmp_path, playwright_factory=lambda: driver, progress=lambda _: None)
    task = asyncio.create_task(leader.start())
    await driver.entered.wait()
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    driver.release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert driver.closed and driver.stopped and not leader.participants
