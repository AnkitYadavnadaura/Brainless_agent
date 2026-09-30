import json
from pathlib import Path

import pytest

from app.autonomy.village_projects import VillageProjectWorkflow, checkpoint_path, validate_revision, project_lock
from app.autonomy.village_workflow import DEFAULTS, digest


@pytest.fixture
def village_runtime(monkeypatch,tmp_path):
    jobs=[]
    prompts=[]
    revision_reply={'config':{'sun_elevation':35},'requirements':[
        {'text':'Change sunlight angle','status':'supported','reason':'sun_elevation=35'}]}
    async def ask(provider,prompt):
        prompts.append(prompt)
        if prompt.startswith('Plan a large'):
            return dict(config=dict(DEFAULTS,extent=80,samples=16,resolution=640),grid=2)
        if prompt.startswith('Plan this small'):
            payload=json.loads(prompt[prompt.index('{"context":'):])
            home=payload['starter_plan']['objects'][0]
            return {'objects':[home]}
        if prompt.startswith('Specify individual'):
            return {'detail':2}
        if prompt.startswith('Plan a revision'):
            return revision_reply
        return {'proceed':True}
    monkeypatch.setattr('app.autonomy.connected_village.ask',ask)
    async def execute(args):
        job=args['job']
        jobs.append(args)
        project=tmp_path/args['project']
        project.write_bytes(json.dumps(job).encode())
        logical=job.get('area',{}).get('id','world')
        if 'object' in job:
            logical+='/'+job['object']['id']
        project.with_suffix('.json').write_text(json.dumps(dict(phase=job['phase'],objects=1,
            logical_object=logical,components=1,component=job.get('component'),created=1,
            polished=job['phase']=='polish')))
        if job['phase']=='render':
            project.with_name('village.png').write_bytes(b'png')
    workflow=VillageProjectWorkflow(None,execute,tmp_path,lambda _:None)
    return workflow,jobs,prompts,revision_reply


@pytest.mark.asyncio
async def test_revision_reuses_prefix_and_keeps_original(village_runtime,tmp_path):
    workflow,jobs,prompts,reply=village_runtime
    project=workflow.store.ensure_project('village')
    await workflow.run('village')
    original=checkpoint_path(tmp_path,'village')
    before=digest(original)
    original_jobs=len(jobs)
    assert jobs[-1]['config']['samples']==256
    assert jobs[-1]['config']['resolution']==2560
    workflow.store.enqueue(project['id'],'Change sunlight angle')
    await workflow.run('village')
    assert digest(original)==before
    assert [item['job']['phase'] for item in jobs[original_jobs:]]==['lighting','render']
    revisions=workflow.store.revisions(project['id'])
    assert len(revisions)==2 and revisions[-1]['status']=='completed'
    assert workflow.store.requests(project['id'])[0]['status']=='completed'
    assert all(item['config']['sun_elevation']==35 for item in jobs[original_jobs:])
    changed=checkpoint_path(tmp_path,revisions[-1]['objective'])
    saved=json.loads(changed.read_text())
    assert saved['revision_requirements']==reply['requirements']
    # Recover lost JSON metadata from SQLite without regenerating verified geometry.
    changed.write_text('{broken json')
    count=len(jobs)
    await workflow.run('village')
    assert len(jobs)==count
    assert json.loads(changed.read_text())==saved


@pytest.mark.asyncio
async def test_unavailable_request_is_unresolved(village_runtime):
    workflow,jobs,prompts,reply=village_runtime
    reply.clear()
    reply.update(requirements=[dict(text='Licensed game assets',status='unsupported',reason='Assets not supplied')])
    project=workflow.store.ensure_project('village')
    workflow.store.enqueue(project['id'],'Use licensed game assets')
    await workflow.run('village')
    request=workflow.store.requests(project['id'])[0]
    assert request['status']=='needs_input' and 'Assets not supplied' in request['error']
    assert len(workflow.store.revisions(project['id']))==1


@pytest.mark.asyncio
async def test_planned_revision_survives_crash_before_seed(village_runtime,tmp_path):
    workflow,jobs,prompts,reply=village_runtime
    await workflow.run('village')
    project=workflow.store.ensure_project('village')
    parent=workflow.store.revisions(project['id'])[0]
    request=workflow.store.enqueue(project['id'],'Change sunlight angle')
    revision=workflow.store.create_revision(project['id'],'village revision',parent['id'],request['id'],plan=reply)
    before=len(jobs)
    await workflow.run('village')
    assert [item['job']['phase'] for item in jobs[before:]]==['lighting','render']
    assert workflow.store.revisions(project['id'])[-1]['status']=='completed'
    assert checkpoint_path(tmp_path,revision['objective']).is_file()


@pytest.mark.asyncio
async def test_render_downgrade_is_not_reported_as_final_quality(village_runtime):
    workflow,jobs,prompts,reply=village_runtime
    execute=workflow.execute
    failed=False
    async def flaky(args):
        nonlocal failed
        if args['job']['phase']=='render' and not failed:
            failed=True
            raise RuntimeError('Resource exhaustion')
        await execute(args)
    workflow.execute=flaky
    await workflow.run('village')
    project=workflow.store.ensure_project('village')
    revision=workflow.store.revisions(project['id'])[-1]
    assert revision['status']=='needs_attention'
    assert 'lower budget' in revision['error']


@pytest.mark.asyncio
async def test_revision_validation_rejects_unbounded_changes(village_runtime,tmp_path):
    workflow,*_=village_runtime
    await workflow.run('village')
    state=json.loads(checkpoint_path(tmp_path,'village').read_text())
    for value in ({'config':{'extent':200}}, {'polish':{'missing':{}}}, {'areas':{'missing':{}}}, {'config':{'samples':-1}}):
        value['requirements']=[dict(text='Change',status='supported',reason='Requested')]
        with pytest.raises(ValueError):
            validate_revision(value,state)


def test_only_one_worker_can_write_a_project(tmp_path):
    with project_lock(tmp_path,'one'):
        with pytest.raises(RuntimeError,match='active worker'):
            with project_lock(tmp_path,'one'):
                pass
        with project_lock(tmp_path,'two'):
            pass
    with project_lock(tmp_path,'one'):
        pass
