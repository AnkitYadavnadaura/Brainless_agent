import json
import pytest

from app.autonomy.village_workflow import DEFAULTS, STAGES, VillageWorkflow, validate_config, village_requested


class Provider:
    def prepare_conversation(self, prompt):
        self.prompt = prompt
    async def open(self): pass
    async def verify_page(self): pass
    async def start_conversation(self): pass
    async def send_prompt(self, prompt): pass
    async def wait_for_response(self): pass
    def remember_conversation(self): pass
    async def extract_response(self):
        return json.dumps({'config': DEFAULTS} if 'Design a large' in self.prompt
                          else {'proceed': True, 'reason': 'Metadata supports continuation'})


@pytest.mark.asyncio
async def test_resume_skips_completed_stages_and_detects_tampering(tmp_path):
    calls = []
    fail = True
    async def execute(args):
        nonlocal fail
        stage = args['stage']
        if stage == 'buildings' and fail:
            fail = False
            raise RuntimeError('interrupted')
        calls.append(stage)
        project = tmp_path / args['project']
        project.write_bytes(b'BLENDER scene ' + stage.encode())
        project.with_suffix('.json').write_text(json.dumps({'stage': stage, 'objects': 10}))
        if stage == 'render':
            project.with_name('village.png').write_bytes(b'render')
    workflow = VillageWorkflow(Provider(), execute, tmp_path, lambda _: None)
    with pytest.raises(RuntimeError, match='interrupted'):
        await workflow.run('Create a village')
    result = await workflow.run('Create a village')
    assert calls == list(STAGES)
    await workflow.run('Create a village')
    assert calls == list(STAGES)
    from pathlib import Path
    Path(result).write_bytes(b'tampered')
    with pytest.raises(ValueError, match='artifact'):
        await workflow.run('Create a village')


@pytest.mark.parametrize('value', [True, float('nan'), -1, 100000])
def test_config_rejects_unbounded_and_non_integer_values(value):
    with pytest.raises(ValueError):
        validate_config(dict(DEFAULTS, buildings=value))


def test_village_routing():
    assert village_requested('Create a big village with GTA 6 level graphics')
    assert not village_requested('Create a car')


@pytest.mark.asyncio
async def test_website_pause_prevents_execution(tmp_path):
    class PausingProvider(Provider):
        async def extract_response(self):
            return json.dumps({'config': DEFAULTS} if 'Design a large' in self.prompt
                              else {'proceed': False, 'reason': 'Needs clarification'})
    async def execute(args):
        pytest.fail('A denied stage must not execute')
    with pytest.raises(RuntimeError, match='paused'):
        await VillageWorkflow(PausingProvider(), execute, tmp_path).run('village')
