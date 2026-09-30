from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.autonomy.village_project_store import VillageProjectStore


@pytest.fixture
def session(monkeypatch,tmp_path):
    import run
    from app.autonomy.capability_lifecycle import CapabilityStatus
    monkeypatch.setattr(run,'__file__',str(tmp_path/'run.py'))
    store=VillageProjectStore(tmp_path/'data'/'village-workspace'/'village-projects.sqlite3')
    built=[]
    class Workflow:
        def __init__(self,*args):
            self.store=store
            self.planner=SimpleNamespace(request=AsyncMock(return_value='uncertain'))
        async def run(self,objective):
            built.append(objective)
            project=store.ensure_project(objective)
            store.select_project(project['id'])
            revisions=store.revisions(project['id'])
            revision=revisions[-1] if revisions else store.create_revision(project['id'],objective,None)
            store.save_checkpoint(project['id'],revision['id'],dict(completed=[dict(evidence=dict(objects=[{'name':'Dome'}]))]))
            store.update_revision(revision['id'],'completed',result='test.blend')
            for request in store.requests(project['id'],'pending'):
                store.update_request(request['id'],'completed',revision_id=revision['id'])
            return 'test.blend'
    monkeypatch.setattr('app.autonomy.model_workflow.ModelProjectWorkflow',Workflow)
    child=SimpleNamespace(agent_id='child',current_task=None)
    async def start(root_id,child_id,executor):
        return await executor(child,None)
    app=SimpleNamespace(
        capability_lifecycle=SimpleNamespace(register_builder=lambda *args:None,
            acquire=AsyncMock(return_value=SimpleNamespace(status=CapabilityStatus.VALIDATED)),promote=AsyncMock()),
        autonomous=SimpleNamespace(factory=SimpleNamespace(create=lambda *args:child)),
        agent_manager=SimpleNamespace(start_agent=start),providers=SimpleNamespace(get=lambda _:None))
    monkeypatch.setattr(run,'ensure_root_agent',AsyncMock(return_value=SimpleNamespace(agent_id='root')))
    return run,app,store,built


@pytest.mark.asyncio
async def test_interactive_new_subject_does_not_modify_previous_project(session,monkeypatch):
    run,app,store,built=session
    inputs=iter(['create tajmahal in blender','make dome larger','create a sports car in Blender',''])
    monkeypatch.setattr('builtins.input',lambda *args:next(inputs))
    await run.run_agent_session(app)
    assert built==['create tajmahal in blender','create tajmahal in blender','create a sports car in Blender']
    taj=store.ensure_project(built[0])
    assert [r['text'] for r in store.requests(taj['id'])]==['make dome larger']
    assert store.selected_project()['objective']==built[-1]


@pytest.mark.asyncio
async def test_related_request_after_restart_uses_selected_project(session,monkeypatch):
    run,app,store,built=session
    previous=store.ensure_project('create tajmahal in blender')
    store.select_project(previous['id'])
    inputs=iter(['add more details',''])
    monkeypatch.setattr('builtins.input',lambda *args:next(inputs))
    await run.run_agent_session(app)
    assert built==[previous['objective']]
    assert store.requests(previous['id'])[0]['text']=='add more details'


@pytest.mark.asyncio
async def test_explicit_resume_id_is_not_rerouted_to_selected_project(session):
    run,app,store,built=session
    previous=store.ensure_project('create tajmahal in blender')
    store.select_project(previous['id'])
    await run.run_agent_session(app,'create a car in blender',followups=False)
    assert built==['create a car in blender']
    assert store.requests(previous['id'])==[]


@pytest.mark.asyncio
async def test_explicit_new_same_subject_gets_separate_project(session,monkeypatch):
    run,app,store,built=session
    previous=store.ensure_project('create tajmahal in blender')
    store.select_project(previous['id'])
    inputs=iter(['/new create tajmahal in blender',''])
    monkeypatch.setattr('builtins.input',lambda *args:next(inputs))
    await run.run_agent_session(app)
    assert '[New project ' in built[0]
    assert store.selected_project()['id']!=previous['id']
    assert store.requests(previous['id'])==[]


@pytest.mark.parametrize('relation',['related','uncertain'])
@pytest.mark.asyncio
async def test_ambiguous_initial_task_is_classified_before_scene_changes(session,monkeypatch,relation):
    run,app,store,built=session
    previous=store.ensure_project('create tajmahal in blender')
    store.select_project(previous['id'])
    request='create a Taj Mahal museum in blender'
    inputs=iter([request,''])
    monkeypatch.setattr('builtins.input',lambda *args:next(inputs))
    classifier=AsyncMock(return_value=relation)
    monkeypatch.setattr('app.autonomy.task_relation.classify_task',classifier)
    await run.run_agent_session(app)
    assert classifier.await_count==1
    assert built==([previous['objective']] if relation=='related' else [])
    assert len(store.requests(previous['id']))==(1 if relation=='related' else 0)
