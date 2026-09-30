import sys

import pytest

from app.autonomy.village_project_store import VillageProjectStore


@pytest.mark.asyncio
async def test_queue_and_status_do_not_start_browser(monkeypatch,tmp_path,capsys):
    import run
    store=VillageProjectStore(tmp_path/'projects.sqlite3')
    project=store.ensure_project('Test village')
    monkeypatch.setattr('app.autonomy.village_project_store.VillageProjectStore',lambda path:store)
    def forbidden(*args,**kwargs):
        raise AssertionError('Queue/status must not start Application or browser')
    monkeypatch.setattr(run,'Application',forbidden)
    monkeypatch.setattr(sys,'argv',['run.py','village','update',project['id'],'More detailed walls'])
    await run.main()
    assert store.requests(project['id'])[0]['text']=='More detailed walls'
    assert 'Queued update' in capsys.readouterr().out
    monkeypatch.setattr(sys,'argv',['run.py','village','status',project['id']])
    await run.main()
    assert 'More detailed walls' in capsys.readouterr().out
