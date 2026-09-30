"""Opt-in real Blender integration: BRAINLESS_BLENDER_SMOKE=1."""
import json
import os
from pathlib import Path

import pytest

from app.autonomy.blender_capability import _operate_village, find_blender
from app.autonomy.village_workflow import DEFAULTS, STAGES


@pytest.mark.skipif(os.environ.get('BRAINLESS_BLENDER_SMOKE') != '1', reason='Opt-in Blender render')
@pytest.mark.asyncio
async def test_real_blender_stages_and_render():
    blender = find_blender()
    assert blender, 'Blender must be installed for this integration test'
    root = Path('data/village-smoke').resolve()
    root.mkdir(parents=True, exist_ok=True)
    config = dict(DEFAULTS, buildings=40, trees=40, resolution=640, samples=16, extent=80)
    for index, stage in enumerate(STAGES):
        await _operate_village(blender, root, dict(stage=stage, config=config,
            project=f'{index:02d}.blend', source=f'{index-1:02d}.blend' if index else None))
        report = json.loads((root / f'{index:02d}.json').read_text())
        assert report['stage'] == stage
        assert report['objects'] >= 1
    assert (root / 'village.png').read_bytes().startswith(b'\x89PNG')
