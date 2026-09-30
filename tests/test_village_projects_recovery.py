import json
from pathlib import Path

import pytest

from app.autonomy.connected_village import ConnectedVillageWorkflow
from app.autonomy.village_projects import checkpoint_path
from app.autonomy.village_workflow import digest
from tests.test_village_projects import village_runtime


@pytest.mark.asyncio
async def test_adopted_completed_checkpoint_has_durable_snapshot(village_runtime, tmp_path):
    workflow, jobs, prompts, _ = village_runtime
    # Build through the previous workflow, with no project/revision database rows.
    legacy = ConnectedVillageWorkflow(None, workflow.execute, tmp_path, lambda _: None, final_quality=True)
    original_result = await legacy.run('village')
    checkpoint = checkpoint_path(tmp_path, 'village')
    original_state = json.loads(checkpoint.read_text())
    assert original_state['version'] == 3
    assert workflow.store.get_project(workflow.store.project_id('village')) is None
    counts = (len(jobs), len(prompts))

    assert await workflow.run('village') == original_result
    project = workflow.store.ensure_project('village')
    revision = workflow.store.revisions(project['id'])[0]
    assert revision['status'] == 'completed'
    assert workflow.store.load_checkpoint(project['id'], revision['id']) == original_state
    assert (len(jobs), len(prompts)) == counts

    # The newly adopted snapshot must recover metadata without rebuilding scenes.
    checkpoint.unlink()
    assert await workflow.run('village') == original_result
    assert json.loads(checkpoint.read_text()) == original_state
    assert (len(jobs), len(prompts)) == counts


@pytest.mark.parametrize('damage', ['missing', 'corrupt'])
@pytest.mark.asyncio
async def test_unseeded_child_repairs_parent_artifact_before_fork(village_runtime, tmp_path, damage):
    workflow, jobs, _, reply = village_runtime
    await workflow.run('village')
    project = workflow.store.ensure_project('village')
    parent = workflow.store.revisions(project['id'])[0]
    parent_checkpoint = checkpoint_path(tmp_path, parent['objective'])
    parent_state = json.loads(parent_checkpoint.read_text())
    damaged_index = max(index for index, record in enumerate(parent_state['completed'])
                        if record['job']['phase'] == 'polish')
    artifact = parent_checkpoint.parent / f'{damaged_index:05d}.blend'
    expected_digest = digest(artifact)
    if damage == 'missing':
        artifact.unlink()
    else:
        artifact.write_bytes(b'corrupted parent scene')

    # Model interruption after planning, before the child's checkpoint is seeded.
    request = workflow.store.enqueue(project['id'], 'Change sunlight angle')
    child = workflow.store.create_revision(project['id'], 'village child revision', parent['id'],
                                           request['id'], plan=reply)
    assert workflow.store.load_checkpoint(project['id'], child['id']) is None
    assert not checkpoint_path(tmp_path, child['objective']).exists()
    count = len(jobs)

    result = await workflow.run('village')

    repaired_jobs = jobs[count:]
    assert [item['job']['phase'] for item in repaired_jobs] == ['polish', 'lighting', 'render', 'lighting', 'render']
    assert all(item['config']['sun_elevation'] == parent_state['config']['sun_elevation']
               for item in repaired_jobs[:3])
    assert all(item['config']['sun_elevation'] == 35 for item in repaired_jobs[3:])
    assert digest(artifact) == expected_digest
    assert workflow.store.revisions(project['id'])[-1]['status'] == 'completed'
    assert workflow.store.requests(project['id'])[0]['status'] == 'completed'
    assert workflow.store.get_project(project['id'])['latest_revision'] == child['id']
    assert Path(result).parent == checkpoint_path(tmp_path, child['objective']).parent
    child_state = workflow.store.load_checkpoint(project['id'], child['id'])
    assert child_state['config']['sun_elevation'] == 35
    assert child_state['revision_requirements'] == reply['requirements']
    count = len(jobs)
    assert await workflow.run('village') == result
    assert len(jobs) == count


@pytest.mark.asyncio
async def test_parseable_invalid_checkpoint_restores_database_snapshot(village_runtime, tmp_path):
    workflow, jobs, prompts, _ = village_runtime
    result = await workflow.run('village')
    project = workflow.store.ensure_project('village')
    revision = workflow.store.revisions(project['id'])[0]
    snapshot = workflow.store.load_checkpoint(project['id'], revision['id'])
    checkpoint = checkpoint_path(tmp_path, revision['objective'])
    checkpoint.write_text('{}')
    counts = (len(jobs), len(prompts))

    assert await workflow.run('village') == result
    assert json.loads(checkpoint.read_text()) == snapshot
    assert (len(jobs), len(prompts)) == counts
    assert workflow.store.revisions(project['id'])[0]['status'] == 'completed'
