import json
import os
from pathlib import Path

import pytest

from app.autonomy.village_workflow import DEFAULTS
from app.autonomy.village_districts import master_plan, area_context, validate_area, starter_area_plan, HOUSE_PARTS, INFRASTRUCTURE_PARTS, validate_component
from app.autonomy.connected_village import ConnectedVillageWorkflow


CONFIG=dict(DEFAULTS,extent=80,buildings=40,trees=40,samples=16,resolution=640)


def example(area, all_kinds=False):
    xmin,ymin,xmax,ymax=area['bounds']
    size=xmax-xmin
    objects=[dict(id='home',kind='house',x=xmin+size*.25,y=ymin+size*.7,width=6,depth=6,height=4),
             dict(id='door',kind='door',parent='home'),dict(id='stairs',kind='stairs',parent='home'),
             dict(id='tree',kind='tree',x=xmin+size*.25,y=ymin+size*.35,width=4,depth=4,height=6)]
    if all_kinds:
        objects += [dict(id='villa',kind='villa',x=xmin+size*.75,y=ymin+size*.7,width=8,depth=7,height=5),
            dict(id='plants',kind='plants',x=xmin+size*.35,y=ymin+size*.35,width=2,depth=2,height=.6),
            dict(id='pond',kind='water',x=xmin+size*.75,y=ymin+size*.35,width=5,depth=4,height=.3),
            dict(id='drum',kind='drum',x=xmin+size*.65,y=ymin+size*.35,width=.7,depth=.7,height=1),
            dict(id='gate',kind='gate',parent='villa')]
    return dict(objects=objects)


def test_neighbours_share_exact_contract_and_context():
    master=master_plan(CONFIG,2)
    a,b=master['areas'][:2]
    assert a['edges']['east']==b['edges']['west']
    assert a['channel_y']==b['channel_y']
    assert area_context(master,b,{a['id']:{'objects':['tree']}})['neighbours'][a['id']]['objects']==['tree']


def test_footprints_attachments_and_corridors():
    area=master_plan(CONFIG,2)['areas'][0]
    plan=validate_area(example(area,True),area)
    assert plan['objects'][1]['y']==plan['objects'][0]['y']-3
    bad=example(area)
    bad['objects'][0]['x']=area['center'][0]
    with pytest.raises(ValueError,match='road'):
        validate_area(bad,area)
    bad=example(area)
    bad['objects'][1]['parent']='missing'
    with pytest.raises(ValueError,match='earlier'):
        validate_area(bad,area)
    bad=example(area)
    bad['objects'][0]['x']=float('nan')
    with pytest.raises(ValueError,match='finite'):
        validate_area(bad,area)


@pytest.mark.parametrize('grid', range(2, 9))
@pytest.mark.parametrize('tile_size', [24, 40, 80])
def test_starter_layout_fits_every_district(grid, tile_size):
    master=master_plan(dict(CONFIG,extent=grid*tile_size/2),grid)
    for area in master['areas']:
        plan=starter_area_plan(area)
        assert validate_area(plan,area)==plan
        assert sum(obj['kind']=='house' for obj in plan['objects'])==2


def test_border_error_identifies_object_and_center_limits():
    area=master_plan(CONFIG,2)['areas'][0]
    bad=example(area)
    bad['objects'][0]['x']=area['bounds'][0]+2
    with pytest.raises(ValueError,match="home.*area-0-0.*center must satisfy"):
        validate_area(bad,area)


@pytest.mark.parametrize('failures', [1, 3])
@pytest.mark.parametrize('invalid_plans', [False, True])
@pytest.mark.asyncio
async def test_object_resume_retains_area_plans_and_polish(monkeypatch,tmp_path,invalid_plans,failures):
    prompts=[]
    async def ask(provider,prompt):
        prompts.append(prompt)
        if prompt.startswith('Plan a large'):
            return dict(config=CONFIG,grid=2)
        if prompt.startswith('Plan this small'):
            payload=json.loads(prompt[prompt.index('{"context":'):])
            context=payload['context']
            assert validate_area(payload['starter_plan'],context['area'])==payload['starter_plan']
            response=example(context['area'])
            if invalid_plans:
                response['objects'][0]['x']=context['area']['bounds'][0]+2
                if payload['validation_error']:
                    assert payload['rejected_plan']==response
                    assert 'center must satisfy' in payload['validation_error']
            return response
        if prompt.startswith('Specify individual'):
            return dict(weathering=.5,detail=2,roughness=.7)
        return dict(proceed=True,reason='Continue from observed metadata')
    monkeypatch.setattr('app.autonomy.connected_village.ask',ask)
    executed=[]
    fail=failures
    async def execute(args):
        nonlocal fail
        job=args['job']
        if job['phase']=='polish' and fail:
            fail-=1
            raise RuntimeError('simulated power loss')
        executed.append(job)
        project=tmp_path/args['project']
        project.write_bytes(json.dumps(job).encode())
        logical=job.get('area',{}).get('id','world')+'/'+job.get('object',{}).get('id','')
        project.with_suffix('.json').write_text(json.dumps(dict(phase=job['phase'],objects=10,
            logical_object=logical,components=3,component=job.get('component'),created=1,polished=job['phase']=='polish')))
        if job['phase']=='render':
            project.with_name('village.png').write_bytes(b'png')
    progress=[]
    workflow=ConnectedVillageWorkflow(None,execute,tmp_path,progress.append)
    if failures==3:
        with pytest.raises(RuntimeError,match='power loss'):
            await workflow.run('connected village')
        saved=json.loads(next(tmp_path.rglob('checkpoint.json')).read_text())
        assert saved['pending']['status']=='failed'
        assert saved['pending']['attempt']==3
    result=await workflow.run('connected village')
    objects_per_area=6 if invalid_plans else 4
    homes_per_area=2 if invalid_plans else 1
    assert len(executed)==1+4*(4+objects_per_area*2+homes_per_area*6)+2
    assert [j['component'] for j in executed if j['phase']=='create' and j.get('object',{}).get('id')=='home'] == (list(HOUSE_PARTS)*4 if not invalid_plans else [])
    assert sum(p.startswith('Plan this small') for p in prompts)==(12 if invalid_plans else 4)
    assert sum(p.startswith('Specify individual') for p in prompts)==4*objects_per_area
    assert sum('Using validated sparse layout' in p for p in progress)==(4 if invalid_plans else 0)
    count=len(prompts)
    await workflow.run('connected village')
    assert len(prompts)==count
    Path(result).write_bytes(b'corrupt')
    before=len(executed)
    await workflow.run('connected village')
    assert len(executed)==before+1
    assert any('Repairing damaged checkpoint' in p for p in progress)


@pytest.mark.skipif(os.environ.get('BRAINLESS_BLENDER_SMOKE')!='1',reason='Opt-in real Blender run')
@pytest.mark.asyncio
async def test_real_connected_objects(tmp_path):
    from app.autonomy.blender_capability import _operate_district, find_blender
    root=tmp_path/'blender-smoke'
    root.mkdir(parents=True,exist_ok=True)
    master=master_plan(CONFIG,2)
    area=master['areas'][0]
    plan=validate_area(example(area,True),area)
    context=area_context(master,area,{})
    shared=dict(area=area,borders=context['borders'],area_plan=plan)
    jobs=[dict(phase='world')]+[dict(phase='infrastructure',component=part,**shared) for part in INFRASTRUCTURE_PARTS]
    for obj in plan['objects']:
        for part in (HOUSE_PARTS if obj['kind'] in ('house','villa') else (None,)):
            jobs.append(dict(phase='create',object=obj,**shared,**({'component':part} if part else {})))
        jobs.append(dict(phase='polish',object=obj,polish=dict(detail=2,weathering=.5,roughness=.7),**shared))
    neighbour=master['areas'][1]
    jobs.append(dict(phase='infrastructure',area=neighbour,area_plan=validate_area(example(neighbour),neighbour),
                     borders=area_context(master,neighbour,{})['borders']))
    jobs.extend((dict(phase='lighting'),dict(phase='render')))
    for index,job in enumerate(jobs):
        job['grid']=2
        await _operate_district(find_blender(),root,dict(config=CONFIG,job=job,
            project=f'{index:05d}.blend',source=f'{index-1:05d}.blend' if index else None))
        report=json.loads((root/f'{index:05d}.json').read_text())
        assert report['phase']==job['phase']
        if 'component' in job:
            assert report['component']==job['component']
            assert report['created']>0
        if job['phase'] in ('create','polish'):
            assert report['components']>0
            assert report['logical_object']==area['id']+'/'+job['object']['id']
        if job['phase']=='polish':
            assert report['polished']
    assert (root/'village.png').read_bytes().startswith(b'\x89PNG')


@pytest.mark.asyncio
async def test_planning_recovery_and_explicit_pause(monkeypatch,tmp_path):
    from app.autonomy.connected_village import validate_review
    calls=[]
    async def malformed(provider,prompt):
        calls.append(prompt)
        raise ValueError('Malformed JSON')
    monkeypatch.setattr('app.autonomy.connected_village.ask',malformed)
    workflow=ConnectedVillageWorkflow(None,None,tmp_path,lambda _:None)
    assert await workflow.request('plan',fallback=lambda: {'safe':True})=={'safe':True}
    assert len(calls)==3
    with pytest.raises(RuntimeError,match='checkpoints retained'):
        await workflow.request('review',validate=validate_review)
    async def paused(provider,prompt):
        return {'proceed':False,'reason':'User pause'}
    monkeypatch.setattr('app.autonomy.connected_village.ask',paused)
    assert (await workflow.request('review',validate=validate_review))['proceed'] is False
    for invalid in ([],None,{'proceed':'true'}):
        with pytest.raises(ValueError):
            validate_review(invalid)


def test_component_contract_rejects_wrong_phase_and_object():
    for part in HOUSE_PARTS:
        validate_component(dict(phase='create',object={'kind':'house'},component=part))
    for job in (dict(phase='render',component='roof'),
                dict(phase='create',object={'kind':'tree'},component='wall_south'),
                dict(phase='infrastructure',component='unknown')):
        with pytest.raises(ValueError,match='component'):
            validate_component(job)


@pytest.mark.parametrize('started_area', [False, True])
@pytest.mark.asyncio
async def test_legacy_migration_and_render_budget_recovery(monkeypatch,tmp_path,started_area):
    import hashlib
    from app.autonomy.village_workflow import digest
    objective='legacy recovery'
    directory=tmp_path/'connected-villages'/hashlib.sha256(objective.encode()).hexdigest()[:20]
    directory.mkdir(parents=True)
    config=dict(CONFIG,samples=64,resolution=1280)
    master=master_plan(config,2)
    area=master['areas'][0]
    plan=starter_area_plan(area)
    jobs=[dict(phase='world',grid=2)]
    if started_area:
        jobs.append(dict(phase='infrastructure',grid=2,area=area,area_plan=plan,
                         borders=area_context(master,area,{})['borders']))
    completed=[]
    for index,job in enumerate(jobs):
        project=directory/f'{index:05d}.blend'
        project.write_bytes(b'legacy scene')
        report=project.with_suffix('.json')
        report.write_text(json.dumps(dict(phase=job['phase'],objects=1)))
        completed.append(dict(job=job,evidence=dict(phase=job['phase'],objects=1),
                              artifacts={p.name:digest(p) for p in (project,report)}))
    checkpoint=directory/'checkpoint.json'
    checkpoint.write_text(json.dumps(dict(version=2,objective=objective,config=config,master=master,
        plans={area['id']:plan} if started_area else {},polish={},completed=completed,art_direction='rural')))
    async def ask(provider,prompt):
        if prompt.startswith('Plan this small'):
            payload=json.loads(prompt[prompt.index('{"context":'):])
            return payload['starter_plan']
        if prompt.startswith('Specify individual'):
            return {'detail':1000}  # Repaired with validated polish defaults.
        return {'proceed':True}
    monkeypatch.setattr('app.autonomy.connected_village.ask',ask)
    executed=[]
    renders=[]
    async def execute(args):
        job=args['job']
        if job['phase']=='render':
            renders.append(args['config'])
            if len(renders)==1:
                raise RuntimeError('render resource exhaustion')
        executed.append(job)
        project=tmp_path/args['project']
        project.write_bytes(json.dumps(job).encode())
        logical=job.get('area',{}).get('id','world')+'/'+job.get('object',{}).get('id','')
        project.with_suffix('.json').write_text(json.dumps(dict(phase=job['phase'],objects=1,
            logical_object=logical,components=1,created=1,component=job.get('component'),polished=job['phase']=='polish')))
        if job['phase']=='render':
            project.with_name('village.png').write_bytes(b'png')
    await ConnectedVillageWorkflow(None,execute,tmp_path,lambda _:None).run(objective)
    state=json.loads(checkpoint.read_text())
    assert state['version']==3
    assert 'pending' not in state
    assert not any(job['phase']=='world' for job in executed)
    assert renders[1]['samples']==32 and renders[1]['resolution']==640
    assert state['completed'][-1]['execution_config']==renders[1]
    for job in executed:
        if job['phase']=='create' and job['object']['kind']=='house':
            assert ('component' in job)==(not started_area or job['area']['id']!=area['id'])
