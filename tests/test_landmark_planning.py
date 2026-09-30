import json
import os
from pathlib import Path
import subprocess

import pytest

from app.autonomy.landmark_plans import landmark_starter
from app.autonomy.model_workflow import validate_model_plan,validate_model_step


def test_bevel_amount_is_normalized_and_bounded():
    step=validate_model_step(dict(operation='bevel',args=dict(target='Marble',amount=.12,segments=4)))
    assert step['args']==dict(target='Marble',width=.12,segments=4)
    for args in (dict(amount=-1),dict(amount=float('nan')),dict(amount=.2,width=.3),dict(segments=100)):
        with pytest.raises(ValueError):
            validate_model_step(dict(operation='bevel',args=dict(target='Marble',**args)))


def test_landmark_plan_is_executable_with_documented_limits():
    plan=landmark_starter('create tajmahal in blender')
    steps=validate_model_plan(plan)
    assert len(steps)<=180
    assert sum(s['operation']=='add_dome' for s in steps)==9
    assert sum(s['operation']=='add_arch' for s in steps)==10
    assert plan['unsupported']
    assert landmark_starter('create a car') is None


@pytest.mark.asyncio
async def test_tajmahal_planning_repairs_invalid_responses(monkeypatch,tmp_path):
    from app.autonomy.model_workflow import ModelProjectWorkflow
    calls=[]
    async def ask(provider,prompt):
        calls.append(prompt)
        return {'ordered_steps':[]}  # Exhaust website planning, then use validated starter.
    monkeypatch.setattr('app.autonomy.connected_village.ask',ask)
    workflow=ModelProjectWorkflow(None,None,tmp_path,lambda _:None)
    async def stop_before_execution(*args,**kwargs):
        raise PermissionError('stop after planning')
    original=workflow.planner.request
    async def request(prompt,**kwargs):
        if prompt.startswith('Review'):
            return await stop_before_execution()
        return await original(prompt,**kwargs)
    workflow.planner.request=request
    with pytest.raises(PermissionError):
        await workflow.run('create tajmahal in blender')
    project=workflow.store.ensure_project('create tajmahal in blender')
    revision=workflow.store.revisions(project['id'])[-1]
    state=workflow.store.load_checkpoint(project['id'],revision['id'])
    assert len(calls)==3
    assert any(s['operation']=='add_dome' for s in state['steps'])
    assert state['limitations'] and state['completed']==[]


@pytest.mark.skipif(os.environ.get('BRAINLESS_BLENDER_SMOKE')!='1',reason='Opt-in actual architectural render')
def test_real_tajmahal_arches_domes_and_bevel(tmp_path):
    from app.autonomy.blender_capability import _script,find_blender
    project=tmp_path/'tajmahal.blend'
    lines=['import bpy,json']
    plan=validate_model_plan(landmark_starter('create tajmahal in blender'))
    for step in plan:
        args=dict(step['args'])
        target=args.pop('target',None)
        if target:
            lines.extend([f'obj=bpy.data.objects[{target!r}]',"bpy.ops.object.select_all(action='DESELECT')",
                          'obj.select_set(True)','bpy.context.view_layer.objects.active=obj'])
        if step['operation']=='render':
            args['output']='tajmahal.png'
            lines.extend(["bpy.context.scene.render.engine='CYCLES'",'bpy.context.scene.cycles.samples=16',
                          'bpy.context.scene.cycles.use_denoising=True','bpy.context.scene.render.resolution_x=640',
                          'bpy.context.scene.render.resolution_y=360','bpy.context.scene.render.resolution_percentage=100'])
        body=_script(step['operation'],project,args).rsplit('\nbpy.ops.wm.save_as_mainfile',1)[0]
        lines.append(body)
    lines.extend([
        "assert abs(bpy.data.objects['Mausoleum'].modifiers['Bevel'].width-.12)<1e-5",
        "assert bpy.data.objects['Mausoleum'].modifiers['Bevel'].segments==3",
        "assert len(bpy.data.objects['CentralDome'].data.polygons)>400",
        "assert len(bpy.data.objects['FrontMainArch'].data.polygons)>100",
        f"bpy.ops.wm.save_as_mainfile(filepath={str(project)!r})",
    ])
    script=tmp_path/'build.py'
    script.write_text('\n'.join(lines),encoding='utf-8')
    result=subprocess.run([find_blender(),'--background','--python-exit-code','1','--python',str(script)],
                          capture_output=True,text=True,timeout=180)
    assert result.returncode==0,(result.stdout+result.stderr)[-4000:]
    assert (tmp_path/'tajmahal.png').read_bytes().startswith(b'\x89PNG')
    from PIL import Image,ImageStat
    with Image.open(tmp_path/'tajmahal.png') as image:
        stats=ImageStat.Stat(image.convert('RGB'))
        assert max(stats.mean)>20 and max(stats.stddev)>15, 'Camera/render must show lit geometry, not an empty black image'
    assert project.stat().st_size>0
