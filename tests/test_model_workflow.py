import json
import math
import os
from pathlib import Path

import pytest

from app.autonomy.model_workflow import ModelProjectWorkflow, validate_model_plan, validate_model_step, verify_model_evidence


def cube():
    return dict(operation='add_cube',args=dict(name='Body',location=[2,0,1],rotation=[0,0,.2],scale=[2,1,1]))


@pytest.mark.asyncio
async def test_general_model_resume_update_and_retry(monkeypatch,tmp_path):
    async def ask(provider,prompt):
        if prompt.startswith('Plan general'):
            update='Preserve existing scene' in prompt
            steps=[dict(operation='transform',args=dict(target='Body',location=[5,0,1],rotation=[0,0,.4],scale=[3,1,1]))] if update else [dict(operation='create_scene'),cube()]
            return {'ordered_steps':steps,'unsupported':[]}
        return {'proceed':True}
    monkeypatch.setattr('app.autonomy.connected_village.ask',ask)
    jobs=[]
    failed=False
    async def execute(args):
        nonlocal failed
        jobs.append(args)
        assert args['live'] and args['visible']
        project=tmp_path/args['project']
        step=args['step']
        if step['operation']=='transform' and not failed:
            failed=True
            project.write_bytes(b'partial')
            raise RuntimeError('Transient error')
        objects=json.loads((tmp_path/args['source']).read_text()) if args['source'] else []
        if step['operation']=='add_cube':
            objects.append(dict(step['args'],type='MESH'))
        if step['operation']=='transform':
            objects[0].update({k:v for k,v in step['args'].items() if k!='target'})
        project.write_text(json.dumps(objects))
        project.with_suffix('.json').write_text(json.dumps(dict(operation=step['operation'],objects=objects)))
    workflow=ModelProjectWorkflow(None,execute,tmp_path,lambda _:None)
    first=await workflow.run('Create a 3d robot')
    original=Path(first).read_bytes()
    project=workflow.store.ensure_project('Create a 3d robot')
    workflow.store.enqueue(project['id'],'Move and scale Body')
    second=await workflow.run('Create a 3d robot')
    assert len(jobs)==4  # two initial steps, failed update, successful retry
    assert Path(first).read_bytes()==original
    assert json.loads(Path(second).read_text())[0]['location']==[5,0,1]
    assert workflow.store.requests(project['id'])[0]['status']=='completed'
    await workflow.run('Create a 3d robot')
    assert len(jobs)==4
    Path(second).write_bytes(b'corrupt')
    await workflow.run('Create a 3d robot')
    assert len(jobs)==5


def test_general_model_rejects_invalid_and_destructive_update_plans():
    for step in (dict(operation=[]), dict(operation='execute_plan'),
                 dict(operation='transform',args={'target':'Body'}),
                 dict(operation='render',args={'samples':100000}),
                 dict(operation='add_cube',args=dict(cube()['args'],scale=[math.inf,1,1]))):
        with pytest.raises(ValueError):
            validate_model_step(step)
    with pytest.raises(ValueError,match='preserve'):
        validate_model_plan({'ordered_steps':[{'operation':'create_scene'}]},update=True)
    with pytest.raises(ValueError,match='Duplicate'):
        validate_model_plan({'ordered_steps':[dict(operation='create_scene'),cube(),cube()]})
    with pytest.raises(ValueError,match='Unknown target'):
        validate_model_plan({'ordered_steps':[dict(operation='bevel',args={'target':'missing'})]},update=True)
    with pytest.raises(ValueError,match='missing'):
        verify_model_evidence(cube(),{'operation':'add_cube','objects':[]})
    with pytest.raises(ValueError,match='transform'):
        verify_model_evidence(cube(),{'operation':'add_cube','objects':[dict(cube()['args'],location=[0,0,0])]})


@pytest.mark.skipif(os.environ.get('BRAINLESS_BLENDER_LIVE_SMOKE')!='1',reason='Opt-in visible Blender window')
@pytest.mark.asyncio
async def test_one_visible_blender_process_for_multiple_steps(tmp_path):
    from app.autonomy.live_blender import LiveBlenderSession
    from app.autonomy.blender_capability import _operate_model_step,find_blender
    session=LiveBlenderSession(find_blender(),tmp_path)
    steps=[dict(operation='create_scene'),cube(),dict(operation='transform',
        args=dict(target='Body',location=[4,2,1],rotation=[0,0,.7],scale=[1,2,1]))]
    pid=None
    try:
        for index,step in enumerate(steps):
            await _operate_model_step(find_blender(),tmp_path,dict(step=step,project=f'{index:05d}.blend',
                source=f'{index-1:05d}.blend' if index else None),live_session=session)
            if pid is None:
                pid=session.process.pid
            assert session.process.pid==pid and session.process.poll() is None
        report=json.loads((tmp_path/'00002.json').read_text())
        body=next(obj for obj in report['objects'] if obj['name']=='Body')
        assert body['location']==[4,2,1]
        assert body['scale']==[1,2,1]
        assert body['rotation'][2]==pytest.approx(.7)
        # A new controller reattaches to the same visible worker after CLI restart.
        restarted=LiveBlenderSession(find_blender(),tmp_path)
        await restarted.ensure_started()
        assert restarted.process is None
        # An interrupted Blender is restarted and restores the previous .blend.
        session.process.terminate()
        session.process.wait(timeout=15)
        await _operate_model_step(find_blender(),tmp_path,dict(step=dict(operation='bevel',args={'target':'Body'}),
            project='00003.blend',source='00002.blend'),live_session=session)
        assert session.process.pid!=pid
        # The district builder uses this same worker and writes component evidence.
        from app.autonomy.blender_capability import _operate_district
        from app.autonomy.village_districts import master_plan,starter_area_plan,area_context
        from app.autonomy.village_workflow import DEFAULTS
        config=dict(DEFAULTS,extent=80,samples=16,resolution=640)
        master=master_plan(config,2)
        area=master['areas'][0]
        plan=starter_area_plan(area)
        shared=dict(area=area,area_plan=plan,borders=area_context(master,area,{})['borders'],grid=2)
        district_jobs=[dict(phase='world',grid=2),dict(phase='infrastructure',component='block',**shared),
                       dict(phase='create',component='foundation',object=plan['objects'][0],**shared)]
        current_pid=session.process.pid
        for index,job in enumerate(district_jobs,4):
            await _operate_district(find_blender(),tmp_path,dict(config=config,job=job,
                project=f'{index:05d}.blend',source=f'{index-1:05d}.blend' if index>4 else None),live_session=session)
            assert session.process.pid==current_pid
        assert json.loads((tmp_path/'00006.json').read_text())['component']=='foundation'
    finally:
        if session.process is not None and session.process.poll() is None:
            session.process.terminate()
            session.process.wait(timeout=15)
