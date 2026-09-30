"""The Browser LLM reviews logs as evidence, without confirming or repeating actions."""
import asyncio

from app.autonomy.mission import MissionStatus
from tests.test_voice_browser_followup import assistant_fixture


def test_browser_llm_reviews_recovered_accessibility_and_console_steps():
    async def scenario():
        assistant, missions, questions, provider = assistant_fixture(observe=True, responses=[
            '{"summary":"The accessibility tree was stale; DOM observation recovered the current page."}'])
        await assistant.handle('Open YouTube')
        mission = missions[-1]
        mission.status = MissionStatus.COMPLETED
        mission.checkpoint['browser_observation'] = {
            'available': True, 'url': 'https://www.youtube.com/', 'elements': [],
            'diagnostics': [{'method': 'accessibility', 'error': 'stale'}, {'method': 'dom', 'status': 'observed'}],
            'console_diagnostics': {'steps': ['observe.dom.completed'], 'receipt_channel': 'console'}}
        await assistant.mission_finished(mission)
        assert len(provider.prompts) == 1
        assert 'observe.dom.completed' in provider.prompts[0]
        assert 'diagnosis only' in provider.prompts[0]
        assert mission.checkpoint['browser_llm_diagnostic_review']['authority'] == 'advisory_only'
        assert len(missions) == 1
        assert 'YouTube' in questions[-1]
    asyncio.run(scenario())


def test_browser_llm_cannot_turn_a_diagnostic_review_into_tool_execution():
    async def scenario():
        assistant, missions, _, provider = assistant_fixture(observe=True, responses=[
            '{"action":"execute","goal":"Send again","sequence":[]}'])
        await assistant.handle('Open YouTube')
        mission = missions[-1]
        mission.status = MissionStatus.FAILED
        mission.checkpoint['last_error'] = 'ACTION_FAILED: console outcome uncertain'
        await assistant.mission_finished(mission)
        assert len(provider.prompts) == 1
        assert len(missions) == 1
        assert 'summary' not in mission.checkpoint.get('browser_llm_diagnostic_review', {})
    asyncio.run(scenario())


def test_stop_during_diagnostic_reasoning_cannot_restore_an_old_question():
    async def scenario():
        assistant, missions, questions, provider = assistant_fixture(observe=True)
        await assistant.handle('Open YouTube')
        mission = missions[-1]
        mission.status = MissionStatus.FAILED
        mission.checkpoint['last_error'] = 'ACTION_FAILED: console outcome uncertain'
        async def complete(*args, **kwargs):
            assistant.reset()
            return '{"summary":"Old diagnosis"}'
        provider.complete = complete
        before = len(questions)
        await assistant.mission_finished(mission)
        assert len(questions) == before
        assert len(missions) == 1
    asyncio.run(scenario())
