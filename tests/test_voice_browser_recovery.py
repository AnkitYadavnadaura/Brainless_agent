"""Browser recovery observes before choosing a bounded alternative plan."""
import asyncio
import json

import pytest

from app.autonomy.mission import MissionStatus
from tests.test_voice_browser_followup import assistant_fixture
from tests.test_external_gmail import gmail_voice_fixture


def plan(function, arguments):
    return json.dumps({"action": "execute", "goal": "Play requested music",
                       "sequence": [{"function": function, "arguments": arguments}]})


async def fail_and_observe(assistant, missions):
    failed = missions[-1]
    failed.status = MissionStatus.FAILED
    failed.checkpoint["last_error"] = "ACTION_FAILED: Video control missing"
    await assistant.mission_finished(failed)
    observing = missions[-1]
    assert observing is not failed
    assert observing.checkpoint["function_sequence"] == [{"function": "browser.observe", "arguments": {}}]
    observing.status = MissionStatus.COMPLETED
    observing.checkpoint["browser_observation"] = {
        "available": True, "url": "https://www.youtube.com/", "elements": []}
    return await assistant.mission_finished(observing)


def test_browser_failure_inspects_then_executes_different_governed_plan():
    async def scenario():
        assistant, missions, _, provider = assistant_fixture(observe=True, responses=[
            plan("browser.navigate", {"url": "https://www.youtube.com/results?search_query=music"})])
        await assistant.handle("play music on youtube")
        result = await fail_and_observe(assistant, missions)
        assert result["status"] == "accepted"
        assert len(missions) == 3
        assert missions[-1].goal == missions[0].goal
        assert missions[-1].checkpoint["browser_recovery_attempt"] == 1
        assert "Video control missing" in provider.prompts[-1]
        assert "UNTRUSTED_CURRENT_PAGE" in provider.prompts[-1]
        assert missions[-1].checkpoint["function_sequence"][0]["function"] == "browser.navigate"
    asyncio.run(scenario())


def test_browser_recovery_stops_after_two_replans():
    async def scenario():
        assistant, missions, questions, _ = assistant_fixture(observe=True, responses=[
            plan("browser.navigate", {"url": "https://www.youtube.com/"}),
            plan("youtube.search", {"query": "music"})])
        await assistant.handle("play music on youtube")
        await fail_and_observe(assistant, missions)
        await fail_and_observe(assistant, missions)
        assert missions[-1].checkpoint["browser_recovery_attempt"] == 2
        count = len(missions)
        missions[-1].status = MissionStatus.FAILED
        missions[-1].checkpoint["last_error"] = "ACTION_FAILED: Unavailable"
        await assistant.mission_finished(missions[-1])
        assert len(missions) == count
        assert "did not finish" in questions[-1]
    asyncio.run(scenario())


@pytest.mark.parametrize("error", ["PERMISSION_DENIED: no", "ACTION_FAILED: outcome uncertain",
                                  "ACTION_FAILED: manual sign-in required", "ACTION_FAILED: lost focus"])
def test_browser_recovery_does_not_retry_intervention_or_denial(error):
    async def scenario():
        assistant, missions, _, provider = assistant_fixture(observe=True)
        await assistant.handle("play music on youtube")
        missions[-1].status = MissionStatus.FAILED
        missions[-1].checkpoint["last_error"] = error
        await assistant.mission_finished(missions[-1])
        assert len(missions) == 1 and not provider.prompts
    asyncio.run(scenario())


@pytest.mark.parametrize("response", [
    plan("youtube.play", {"query": "music"}),
    plan("gmail.send_email", {"to": "a@example.com"}),
])
def test_recovery_rejects_repeated_plans_and_out_of_scope_tools(response):
    async def scenario():
        assistant, missions, questions, _ = assistant_fixture(observe=True, responses=[response])
        await assistant.handle("play music on youtube")
        await fail_and_observe(assistant, missions)
        assert len(missions) == 2
        assert "recovery methods" in questions[-1]
    asyncio.run(scenario())


@pytest.mark.parametrize("status,detail,expected", [
    (MissionStatus.COMPLETED, "", "confirmed the email was sent"),
    (MissionStatus.FAILED, "ACTION_FAILED: Gmail send outcome is uncertain", "outcome is uncertain"),
    (MissionStatus.BLOCKED, "PERMISSION_DENIED: Send declined", "Send declined"),
])
def test_send_outcome_is_visible_and_never_automatically_replayed(status, detail, expected):
    async def scenario():
        assistant, _, missions, questions = gmail_voice_fixture([
            '{"action":"send","goal":"Send update","to":"person@example.com","subject":"Update","body":"Ready."}'])
        await assistant.handle("send email to person@example.com saying ready")
        await assistant.handle("Chrome Work")
        missions[0].status = MissionStatus.COMPLETED
        await assistant.mission_finished(missions[0])
        sending = missions[-1]
        sending.status = status
        sending.checkpoint["last_error"] = detail
        await assistant.mission_finished(sending)
        assert expected in questions[-1]
        assert len(missions) == 2
    asyncio.run(scenario())
