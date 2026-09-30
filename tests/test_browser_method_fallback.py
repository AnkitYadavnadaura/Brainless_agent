"""Browser alternatives stay in the approved profile and stop on uncertain effects."""
import asyncio
import json
import shutil
import subprocess
from unittest.mock import AsyncMock

import pytest

from app.browser.external_gmail import ExternalGmailProfiles
from app.browser.methods import MethodUnavailable, run_methods
from app.browser.native_console import NativeConsoleIntervention
from app.browser.task_scripts import GMAIL_SEND, YOUTUBE_INSPECT, YOUTUBE_PLAY
from tests.test_external_browser_client import client_fixture
from tests.test_external_gmail import FakeTransport, _inventory


def test_methods_change_once_and_record_verification():
    async def scenario():
        first = AsyncMock(side_effect=MethodUnavailable("control missing"))
        second = AsyncMock(return_value="verified")
        attempts = []
        assert await run_methods([("uia", first), ("dom", second)], attempts=attempts) == "verified"
        assert attempts == [{"method": "uia", "status": "unavailable"},
                            {"method": "dom", "status": "verified"}]
        first.assert_awaited_once()
        second.assert_awaited_once()
    asyncio.run(scenario())


@pytest.mark.parametrize("error", [PermissionError("denied"), asyncio.CancelledError(),
                                    NativeConsoleIntervention("inspect", submitted=True)])
def test_methods_never_hide_denial_cancellation_or_uncertainty(error):
    async def scenario():
        alternate = AsyncMock()
        with pytest.raises(type(error)):
            await run_methods([("first", AsyncMock(side_effect=error)), ("other", alternate)])
        alternate.assert_not_awaited()
    asyncio.run(scenario())


def test_method_exhaustion_is_bounded_and_reports_each_method():
    async def scenario():
        first = AsyncMock(side_effect=MethodUnavailable("not found"))
        other = AsyncMock(side_effect=MethodUnavailable("not verified"))
        with pytest.raises(MethodUnavailable, match="uia: not found.*dom: not verified"):
            await run_methods([("uia", first), ("dom", other)])
        assert first.await_count == other.await_count == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("primary", [
    {"ok": False, "sent": False, "error": "compose"},
    {"ok": False, "sent": False, "error": "recipient"},
    {"ok": False, "sent": False, "error": "draft_verification"},
])
def test_external_gmail_changes_method_only_before_send(tmp_path, primary):
    async def scenario():
        transport = FakeTransport()
        transport.evaluate = AsyncMock(return_value={"ok": True, "sent": True})
        sender = ExternalGmailProfiles(tmp_path, discover=lambda **_: _inventory(tmp_path),
            transport_factory=lambda: transport, ui_runner=lambda *_: primary)
        result = await sender.send("chrome-work", "Google Chrome — Work", "p@example.com", "Update", "Ready.")
        assert result.startswith("Email sent")
        assert transport.navigated == [42]
        hwnd, family, script = transport.evaluate.call_args.args
        assert (hwnd, family) == (42, "chromium")
        assert '"to": "p@example.com"' in script
        assert sender.last_method_attempts[-1] == {"method": "dom", "status": "verified"}
    asyncio.run(scenario())


@pytest.mark.parametrize("primary", [None, {}, {"ok": False, "sent": True},
                                     {"ok": False, "sent": False, "error": "login_required"}])
def test_external_gmail_does_not_retry_unknown_send_or_login(tmp_path, primary):
    async def scenario():
        transport = FakeTransport()
        transport.evaluate = AsyncMock()
        sender = ExternalGmailProfiles(tmp_path, discover=lambda **_: _inventory(tmp_path),
            transport_factory=lambda: transport, ui_runner=lambda *_: primary)
        with pytest.raises(RuntimeError):
            await sender.send("chrome-work", "Google Chrome — Work", "p@example.com", "Update", "Ready.")
        transport.evaluate.assert_not_awaited()
    asyncio.run(scenario())


def test_youtube_switches_to_dom_in_the_same_profile(tmp_path):
    async def scenario():
        client, transport = client_fixture(tmp_path)
        await client.select_profile("chrome-work", "Google Chrome — Work")
        transport.evaluate = AsyncMock(side_effect=[
            {"ok": True, "url": "https://www.youtube.com/watch?v=selected"},
            {"ok": True, "playing": True}])
        async def no_delay(snapshot, predicate):
            return snapshot
        client._wait_for = no_delay
        result = await client.play_youtube("music")
        assert "verified using DOM" in result
        assert len(transport.launches) == 1
        assert transport.navigations == [(42, "https://www.youtube.com/results?search_query=music"),
                                         (42, "https://www.youtube.com/watch?v=selected")]
        assert [call.args[0] for call in transport.evaluate.await_args_list] == [42, 42]
        assert client.last_method_attempts == [
            {"method": "accessibility", "status": "unavailable"}, {"method": "dom", "status": "verified"}]
    asyncio.run(scenario())


def test_generic_youtube_request_opens_unopened_selected_profile(tmp_path):
    async def scenario():
        client, transport = client_fixture(tmp_path)
        await client.select_profile("chrome-work", "Google Chrome — Work")
        transport.snapshots = [
            {"url": "https://www.youtube.com/", "elements": [
                {"runtime_id": "video", "type": "link", "label": "Music 100 views 3 minutes"}]},
            {"url": "https://www.youtube.com/watch?v=selected", "elements": [
                {"runtime_id": "pause", "type": "button", "label": "Pause (k)"}]}]
        assert "playing" in await client.play_youtube("recommendation")
        assert len(transport.launches) == 1
        assert transport.navigations == [(42, "https://www.youtube.com/")]
        assert transport.actions[0][2]["target"] == "video"
    asyncio.run(scenario())


@pytest.mark.parametrize("result", [{"ok": False, "error": "sign-in required"},
                                    {"ok": True, "url": "https://example.com/watch"}])
def test_youtube_dom_requires_a_verified_youtube_result(tmp_path, result):
    async def scenario():
        client, transport = client_fixture(tmp_path)
        await client.select_profile("chrome-work", "Google Chrome — Work")
        await client.open()
        transport.evaluate = AsyncMock(return_value=result)
        with pytest.raises(MethodUnavailable):
            await client._play_youtube_dom()
        assert not transport.navigations
        assert transport.evaluate.await_count == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("script", [GMAIL_SEND.replace("__PAYLOAD__", "{}"), YOUTUBE_INSPECT, YOUTUBE_PLAY])
def test_trusted_dom_scripts_parse(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is unavailable")
    result = subprocess.run([node, "--check"], input=script, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("changed", [False, True])
def test_gmail_dom_verifies_draft_before_one_send(changed):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is unavailable")
    payload = {"to": "person@example.com", "subject": 'A "quoted" subject', "body": "Ready.\nDetails here."}
    harness = r'''
const visible = {getClientRects:()=>[{}], focus(){},dispatchEvent(){}};
global.getComputedStyle = () => ({visibility:'visible'});
global.Event = global.KeyboardEvent = class {};
global.HTMLInputElement = class { get value(){return this.val||''} set value(v){this.val=v} };
global.HTMLTextAreaElement = HTMLInputElement;
global.setTimeout = (f) => {f();return 0};
global.location = {protocol:'https:',hostname:'mail.google.com'};
const subject = Object.assign(new HTMLInputElement(),visible);
subject.value = CHANGED ? 'Another draft' : '';
const body = Object.assign({innerText:'',textContent:''},visible);
const chip = {getAttribute:name=>name==='email'?'person@example.com':null};
let sent = 0;
const send = {...visible,click(){sent++}};
const form = {querySelectorAll(sel){
 if(sel.includes('contenteditable'))return [body];
 if(sel==='[email],[data-hovercard-id]')return [chip];
 if(sel.includes('name="cc"'))return [];
 if(sel.includes('aria-label^="Send"'))return [send];
 throw Error('Unexpected selector: '+sel);
}};
subject.closest = () => form;
global.document = {querySelectorAll(sel){
 if(sel==='input[name="subjectbox"]')return [subject];
 if(sel.includes('role="alert"'))return sent?[{...visible,textContent:'Message sent'}]:[];
 throw Error('Unexpected document selector: '+sel);
}};
'''.replace("CHANGED", "true" if changed else "false")
    script = GMAIL_SEND.replace("__PAYLOAD__", json.dumps(payload))
    result = subprocess.run([node], input=harness + script + '.then(result=>console.log(JSON.stringify({result,sent})));',
                            text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout.splitlines()[-1])
    assert '[Brainless] gmail.origin.verify' in result.stdout
    assert ('gmail.send.verified' if not changed else 'gmail.failed_before_send') in result.stdout
    assert observed["sent"] == (0 if changed else 1)
    assert observed["result"]["ok"] is not changed
