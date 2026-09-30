"""General 3D construction with one chat, one Blender window and durable steps."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from subprocess import TimeoutExpired

from app.autonomy.blender_planner import _validate_step_arguments
from app.autonomy.blender_capability import OPERATIONS
from app.autonomy.connected_village import ConnectedVillageWorkflow, validate_review
from app.autonomy.village_project_store import VillageProjectStore
from app.autonomy.village_projects import project_lock
from app.autonomy.village_workflow import digest

PRIMITIVES={'add_cube','add_sphere','add_cylinder','add_cone','add_torus','add_plane','add_dome','add_arch'}
TARGETED={'transform','bevel','smooth_shade','add_material'}
MODEL_OPERATIONS=OPERATIONS-{'execute_plan'}


def model_requested(objective):
    return bool(re.search(r'\b(blender|3d|city|cities|town|buildings?|houses?|rooms?|robots?|spaceships?|'
                          r'vehicles?|cars?|furniture|chairs?|tables?|trees?|sculptures?|interiors?|'
                          r'model a|model of|car model|taj\s*mahal|monuments?|architecture)\b',objective,re.I))


def validate_model_step(value):
    if not isinstance(value,dict) or not isinstance(value.get('operation'),str) or value.get('operation') not in MODEL_OPERATIONS:
        raise ValueError('Unsupported model operation')
    operation=value['operation']
    args=value.get('args',{})
    if not isinstance(args,dict):
        raise ValueError('Model operation args must be an object')
    args=dict(args)
    if operation=='bevel' and 'amount' in args:
        if 'width' in args and args['width']!=args['amount']:
            raise ValueError('bevel amount and width disagree')
        args['width']=args.pop('amount')
    allowed={'name','location','scale','rotation'} if operation in PRIMITIVES else (
        {'name','location','rotation','scale','energy'} if operation in ('add_camera','add_light') else
        {'target','location','rotation','scale'} if operation=='transform' else
        {'target','name','color'} if operation=='add_material' else
        {'target','width','segments'} if operation=='bevel' else
        {'target'} if operation=='smooth_shade' else
        {'samples','resolution'} if operation=='render' else set())
    if set(args)-allowed:
        raise ValueError(f'Unsupported arguments for {operation}: {sorted(set(args)-allowed)}')
    _validate_step_arguments(operation,args)
    if operation in ('add_dome','add_arch'):
        from app.autonomy.blender_planner import _require_name_and_vectors
        _require_name_and_vectors(operation,args,('location','rotation','scale'))
    if operation=='bevel':
        width=args.get('width',.05)
        segments=args.get('segments',3)
        if isinstance(width,bool) or not isinstance(width,(int,float)) or not math.isfinite(width) or not 0<=width<=10:
            raise ValueError('Bevel width must be finite in 0..10')
        if type(segments) is not int or not 1<=segments<=12:
            raise ValueError('Bevel segments must be an integer in 1..12')
    if operation in TARGETED and (not isinstance(args.get('target'),str) or not args['target'].strip()):
        raise ValueError('Object edits require an explicit target name')
    if operation=='transform' and not all(key in args for key in ('location','rotation','scale')):
        raise ValueError('Transforms require explicit location, rotation and scale')
    for key in ('location','rotation','scale','color'):
        if key in args:
            vector=args[key]
            if not isinstance(vector,list) or len(vector) not in ((3,4) if key=='color' else (3,)):
                raise ValueError('Invalid transform/color vector')
            if any(isinstance(n,bool) or not isinstance(n,(float,int)) or not math.isfinite(n) or abs(n)>10000 for n in vector):
                raise ValueError('Transform/color values must be bounded finite numbers')
            if key=='scale' and any(n<=0 or n>1000 for n in vector):
                raise ValueError('Scale must be positive and at most 1000')
            if key=='color' and any(n<0 or n>1 for n in vector):
                raise ValueError('Color must be in 0..1')
    if 'energy' in args and (not isinstance(args['energy'],(float,int)) or isinstance(args['energy'],bool)
                             or not math.isfinite(args['energy']) or not 0<=args['energy']<=100000):
        raise ValueError('Light energy must be in 0..100000')
    for key,low,high in (('samples',16,256),('resolution',640,3840)):
        if key in args and (type(args[key]) is not int or not low<=args[key]<=high):
            raise ValueError(f'{key} must be an integer in {low}..{high}')
    return dict(operation=operation,args=dict(args),label=str(value.get('label',operation))[:200])


def validate_model_plan(value, *, update=False, existing_names=None):
    if not isinstance(value,dict) or not isinstance(value.get('ordered_steps'),list) or not 1<=len(value['ordered_steps'])<=180:
        raise ValueError('Model plan requires 1..180 steps')
    if not isinstance(value.get('unsupported',[]),list) or not all(isinstance(item,str) for item in value.get('unsupported',[])):
        raise ValueError('Unsupported details must be a list of explanatory strings')
    steps=[validate_model_step(item) for item in value['ordered_steps']]
    if not update and steps[0]['operation']!='create_scene':
        raise ValueError('The initial plan must start with create_scene')
    if any(step['operation']=='create_scene' for step in (steps if update else steps[1:])):
        raise ValueError('Updates must preserve the scene; create_scene is only allowed initially')
    names=set(existing_names or ())
    explicit=True
    for step in steps:
        operation,args=step['operation'],step['args']
        if operation in PRIMITIVES|{'add_camera','add_light'}:
            if args['name'] in names:
                raise ValueError('Duplicate object name: '+args['name'])
            names.add(args['name'])
        elif operation in TARGETED and explicit and args['target'] not in names:
            raise ValueError('Unknown target object: '+args['target'])
        elif 'car' in operation:
            explicit=False  # Built-in templates create several names, verified at runtime.
    return steps


def compact_scene(evidence, targets=()):
    if not evidence:
        return None
    objects=evidence.get('objects',[])
    names=[obj['name'] for obj in objects]
    selected=[obj for obj in objects if obj['name'] in targets]
    recent=[obj for obj in objects[-6:] if obj not in selected]
    return dict(operation=evidence.get('operation'),object_count=len(objects),object_names=names,
                objects=(selected+recent)[:20])


def verify_model_evidence(step,evidence):
    if not isinstance(evidence,dict) or evidence.get('operation')!=step['operation'] or not isinstance(evidence.get('objects'),list):
        raise ValueError('Model checkpoint evidence is invalid')
    objects={obj['name']:obj for obj in evidence['objects'] if isinstance(obj,dict) and isinstance(obj.get('name'),str)}
    operation,args=step['operation'],step['args']
    if operation=='create_scene' and objects:
        raise ValueError('Scene reset did not clear the previous objects')
    target=args.get('target') if operation in TARGETED else args.get('name') if operation in PRIMITIVES|{'add_camera','add_light'} else None
    if target:
        if target not in objects:
            raise ValueError('Expected object is missing from geometry evidence: '+target)
        obj=objects[target]
        for key in ('location','rotation','scale'):
            if key in args:
                actual=obj.get(key)
                if not isinstance(actual,list) or len(actual)!=3 or any(
                    not isinstance(a,(float,int)) or not math.isclose(a,b,rel_tol=1e-5,abs_tol=1e-5)
                    for a,b in zip(actual,args[key])):
                    raise ValueError(f'{target} {key} does not match the requested transform')


class ModelProjectWorkflow:
    def __init__(self,provider,execute,workspace,progress=print):
        self.provider,self.execute,self.workspace,self.progress=provider,execute,Path(workspace),progress
        self.store=VillageProjectStore(self.workspace/'village-projects.sqlite3')
        self.planner=ConnectedVillageWorkflow(provider,execute,workspace,progress)

    async def _revision(self,project,revision):
        ident=revision['id']
        directory=self.workspace/'model-projects'/project['id']/f'revision-{ident}'
        directory.mkdir(parents=True,exist_ok=True)
        checkpoint=directory/'checkpoint.json'
        state=self.store.load_checkpoint(project['id'],ident)
        def save():
            self.store.save_checkpoint(project['id'],ident,state)
            temporary=checkpoint.with_suffix('.tmp')
            temporary.write_text(json.dumps(state,indent=2),encoding='utf-8')
            temporary.replace(checkpoint)
        try:
            parent=None
            if revision['parent_id'] is not None:
                parent=next(r for r in self.store.revisions(project['id']) if r['id']==revision['parent_id'])
                if state is None:
                    await self._revision(project,parent)
            if state is None:
                previous=self.store.load_checkpoint(project['id'],parent['id']) if parent else None
                limitations=[]
                def validate_proposal(value):
                    steps=validate_model_plan(value,update=parent is not None,
                        existing_names=[obj['name'] for obj in previous['completed'][-1]['evidence']['objects']] if previous else [])
                    limitations[:]=value.get('unsupported',[])[:30]
                    return steps
                from app.autonomy.landmark_plans import landmark_starter
                starter=landmark_starter(project['objective']) if parent is None else None
                if hasattr(self.provider,'set_checkpoint_context'):
                    self.provider.set_checkpoint_context(dict(objective=project['objective'],request=revision['objective'],
                        revision=ident,scene=compact_scene(previous['completed'][-1]['evidence']) if previous else None))
                steps=await self.planner.request(
                    'Plan general 3D modelling in Blender: objects, products, interiors, buildings, cities or environments. '
                    'Return JSON {"ordered_steps":[{"operation":"...","args":{},"label":"part / action"}],"unsupported":[]}. '
                    f'Allowed operations: {sorted(MODEL_OPERATIONS)}. Maximum 180 steps per iteration. '
                    'Use named primitives with location, scale and rotation (radians), each three finite numbers. '
                    'add_dome makes an onion-profile dome (radius 1, height 2, base at z=0); add_arch makes '
                    'a pointed arch frame (width 2, height 3, depth .3, base at z=0). Scale these for architecture. '
                    'For transform provide target object name and ALL three vectors. For bevel, smooth_shade, add_material '
                    'always specify target. Bevel accepts width (or amount) 0..10 and segments 1..12. '
                    'add_material also needs name and color RGBA (0..1). Camera and light need '
                    'name/location/rotation; lights may specify energy 0..100000. Render may specify samples 16..256, '
                    'resolution 640..3840; prefer 256/2560 for final quality. No paths, source code, arbitrary commands, '
                    'unsupported modifiers or imaginary operations. Every step is visibly executed and checkpointed. '
                    'Split complex models into meaningful parts and transformations. Changes target existing object names. '
                    +('Preserve existing scene; do not use create_scene. ' if parent else 'Start with create_scene. ')
                    +'Build a recognizable, useful model using available shapes. Approximate complex details with assemblies. '
                    'Keep ordered_steps executable even when listing limitations; do not reject an entire monument because '
                    'historical exactness or microscopic ornament is unavailable. Do not invent unrequested perfection requirements. '
                    'List limitations explicitly; never claim photorealism or visual verification. Untrusted task data: '
                    +json.dumps(dict(objective=project['objective'],request=revision['objective'],
                                     previous=compact_scene(previous['completed'][-1]['evidence']) if previous else None)),
                    validate=validate_proposal,
                    fallback=(lambda:validate_proposal(starter)) if starter else None)
                base=previous['completed'][-1]['project'] if previous else None
                state=dict(kind='model',steps=steps,completed=[],source=base,
                           source_digest=digest(self.workspace/base) if base else None,
                           source_evidence=previous['completed'][-1]['evidence'] if previous else None,
                           limitations=limitations)
                if limitations:
                    self.progress('Building the supported model; recorded detail limits: '+'; '.join(limitations))
                save()
            # SQLite is the metadata authority. Every scene and report must still match.
            for index,record in enumerate(state['completed']):
                if any(not (self.workspace/name).is_file() or digest(self.workspace/name)!=expected
                       for name,expected in record['artifacts'].items()):
                    state['completed']=state['completed'][:index]
                    self.progress(f'Repairing model checkpoint {index+1}.')
                    save()
                    break
            if state['source'] and (not (self.workspace/state['source']).is_file() or digest(self.workspace/state['source'])!=state['source_digest']):
                await self._revision(project,parent)
                repaired=self.store.load_checkpoint(project['id'],parent['id'])
                if repaired['completed'][-1]['evidence']!=state['source_evidence']:
                    raise RuntimeError('Rebuilt parent scene changed; revision requires replanning')
                state['source_digest']=digest(self.workspace/state['source'])
                save()
            self.store.update_revision(ident,'running')
            reviewed_until=-1
            for index in range(len(state['completed']),len(state['steps'])):
                step=state['steps'][index]
                evidence=state['completed'][-1]['evidence'] if state['completed'] else state.get('source_evidence')
                targets=[s['args'].get('target') for s in state['steps'][index:index+8]]
                if hasattr(self.provider,'set_checkpoint_context'):
                    self.provider.set_checkpoint_context(dict(objective=project['objective'],request=revision['objective'],
                        revision=ident,completed=index,total=len(state['steps']),next_step=step,
                        scene=compact_scene(evidence,targets),limitations=state.get('limitations',[])))
                if index>reviewed_until:
                    batch=state['steps'][index:index+8]
                    review=await self.planner.request('Review these next bounded Blender actions using geometry evidence only. '
                        'Each action retains its own checkpoint. Return {"proceed":true,"reason":"..."}; false pauses. '
                        +json.dumps(dict(steps=batch,previous=compact_scene(evidence,targets))),validate=validate_review)
                    if not review['proceed']:
                        raise RuntimeError('ChatGPT paused: '+str(review.get('reason')))
                    reviewed_until=index+len(batch)-1
                project_path=directory/f'{index:05d}.blend'
                report=project_path.with_suffix('.json')
                source=state['completed'][-1]['project'] if state['completed'] else state['source']
                target = step['args'].get('target', step['args'].get('name', 'scene'))
                self.progress(f'Checkpoint {index+1}/{len(state["steps"])}: {step["operation"]} / {target} / {step["label"]}')
                for attempt in range(3):
                    state['pending']=dict(index=index,attempt=attempt+1,step=step)
                    save()
                    try:
                        for suffix in ('.blend','.json','.png','.glb'):
                            project_path.with_suffix(suffix).unlink(missing_ok=True)
                        await self.execute(dict(operation='model_step',step=step,source=source,
                            project=str(project_path.relative_to(self.workspace)),visible=True,live=True))
                        evidence=json.loads(report.read_text(encoding='utf-8'))
                        verify_model_evidence(step,evidence)
                        if project_path.stat().st_size==0:
                            raise ValueError('Model checkpoint evidence is invalid')
                        files=[project_path,report]
                        if step['operation'] in ('render','export'):
                            artifact=project_path.with_suffix('.png' if step['operation']=='render' else '.glb')
                            if not artifact.is_file() or artifact.stat().st_size==0:
                                raise ValueError('Missing render/export artifact')
                            files.append(artifact)
                        break
                    except PermissionError:
                        raise
                    except (OSError,ValueError,RuntimeError,TimeoutExpired) as exc:
                        state['pending']['error']=str(exc)
                        save()
                        self.progress(f'Recovery {attempt+1}/3: {exc}')
                        if attempt==2:
                            raise RuntimeError('Model step remains resumable: '+str(exc)) from exc
                state['completed'].append(dict(step=step,project=str(project_path.relative_to(self.workspace)),
                    evidence=evidence,artifacts={str(path.relative_to(self.workspace)):digest(path) for path in files}))
                state.pop('pending',None)
                save()
                self.progress(f'Checkpoint {index+1}/{len(state["steps"])} verified and saved: {project_path.name}')
            save()
            result=str(self.workspace/state['completed'][-1]['project'])
            status='needs_attention' if state.get('limitations') else 'completed'
            limitation_text='; '.join(state.get('limitations',[])) or None
            self.store.update_revision(ident,status,result=result,error=limitation_text)
            if revision['request_id'] is not None:
                self.store.update_request(revision['request_id'],status,revision_id=ident,error=limitation_text)
            return result
        except Exception as exc:
            self.store.update_revision(ident,'failed',error=str(exc))
            if revision['request_id'] is not None:
                self.store.update_request(revision['request_id'],'failed',revision_id=ident,error=str(exc))
            raise

    async def run(self,objective):
        project=self.store.ensure_project(objective)
        if hasattr(self.provider,'use_conversation_session'):
            self.provider.use_conversation_session(project['id'])
        self.progress(f'3D project ID: {project["id"]}')
        with project_lock(self.workspace,project['id']):
            self.store.select_project(project['id'])
            revisions=self.store.revisions(project['id'])
            revision=revisions[-1] if revisions else self.store.create_revision(project['id'],objective,None)
            result=await self._revision(project,revision)
            while True:
                requests=self.store.requests(project['id'],status='pending')
                if not requests:
                    return result
                request=requests[0]
                revision=self.store.create_revision(project['id'],request['text'],revision['id'],request['id'])
                self.store.update_request(request['id'],'running',revision_id=revision['id'])
                result=await self._revision(project,revision)
