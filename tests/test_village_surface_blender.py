"""Opt-in real Blender surface/footprint checks: BRAINLESS_BLENDER_SMOKE=1."""
import os
from pathlib import Path
import subprocess

import pytest

from app.autonomy import district_scene, village_scene
from app.autonomy.blender_capability import find_blender
from app.autonomy.village_districts import HOUSE_PARTS, master_plan, starter_area_plan, validate_area
from app.autonomy.village_workflow import DEFAULTS


@pytest.mark.skipif(os.environ.get('BRAINLESS_BLENDER_SMOKE') != '1', reason='Opt-in Blender render')
def test_real_blender_surface_controls_and_footprints(tmp_path):
    blender = find_blender()
    assert blender, 'Blender must be installed for this integration test'
    config = dict(DEFAULTS, extent=80, buildings=40, trees=40, samples=16, resolution=640)
    area = master_plan(config, 2)['areas'][0]
    plan = starter_area_plan(area)
    plan['objects'].extend([
        dict(id='tree', kind='tree', x=-61, y=-51, width=4, depth=4, height=6),
        dict(id='plants', kind='plants', x=-51, y=-51, width=2, depth=2, height=.6),
        dict(id='pond', kind='water', x=-21, y=-51, width=5, depth=4, height=.3),
        dict(id='drum', kind='drum', x=-12, y=-51, width=.7, depth=.7, height=1),
    ])
    plan = validate_area(plan, area)
    source = Path(village_scene.__file__).read_text(encoding='utf-8')
    source += '\n' + Path(district_scene.__file__).read_text(encoding='utf-8')
    source += f'\nCONFIG={config!r}\nAREA={area!r}\nPLAN={plan!r}\nROOT={str(tmp_path)!r}\n'
    source += f'HOUSE_PARTS={HOUSE_PARTS!r}\n'
    source += '''
import bpy
from pathlib import Path
from mathutils import Vector

district_step(dict(phase='world'), CONFIG)
district_step(dict(phase='infrastructure', area=AREA), CONFIG)
# Resuming an older checkpoint must upgrade that object's generated materials.
legacy=bpy.data.materials.new(AREA['id']+'/home1/Plaster')
legacy.use_nodes=True
legacy.node_tree.nodes.new('ShaderNodeTexNoise').inputs['Scale'].default_value=5
for spec in PLAN['objects']:
    for component in HOUSE_PARTS if spec['kind']=='house' else (None,):
        district_step(dict(phase='create', area=AREA, object=spec, component=component), CONFIG)
    district_step(dict(phase='polish', area=AREA, object=spec,
        polish=dict(detail=2, roughness=.63, weathering=.4)), CONFIG)

# Bevels must stay inside original geometry, including very thin door/window parts.
depsgraph=bpy.context.evaluated_depsgraph_get()
bevel_count=0
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or not any(mod.type=='BEVEL' for mod in obj.modifiers):
        continue
    low=[min(vertex.co[axis] for vertex in obj.data.vertices) for axis in range(3)]
    high=[max(vertex.co[axis] for vertex in obj.data.vertices) for axis in range(3)]
    evaluated=obj.evaluated_get(depsgraph)
    for vertex in evaluated.data.vertices:
        assert all(low[axis]-.0001 <= vertex.co[axis] <= high[axis]+.0001 for axis in range(3)), obj.name
    bevel_count+=1
assert bevel_count > 10
for spec in PLAN['objects']:
    if spec['kind'] not in ('tree','plants','water','drum'):
        continue
    prefix=AREA['id']+'/'+spec['id']
    for obj in bpy.context.scene.objects:
        if obj.get('logical_object')==prefix:
            for corner in obj.bound_box:
                point=obj.matrix_world @ Vector(corner)
                assert abs(point.x-spec['x']) <= spec['width']/2+.5, obj.name
                assert abs(point.y-spec['y']) <= spec['depth']/2+.5, obj.name

wall=bpy.data.materials[AREA['id']+'/home1/Plaster']
assert wall.node_tree.nodes['World metre coordinates'].outputs['Position'].is_linked
assert wall.node_tree.nodes['Surface grain in metres'].inputs['Scale'].default_value==65
roughness=wall.node_tree.nodes['Surface roughness']
assert abs(roughness.inputs[2].default_value + roughness.inputs[1].default_value/2 - .63) < .0001
assert abs(wall.node_tree.nodes['Surface relief'].inputs['Strength'].default_value-.14) < .0001
tiles=bpy.data.objects[AREA['id']+'/home1/Individual roof tiles']
assert len({p.material_index for p in tiles.data.polygons})==5
glass=bpy.data.materials[AREA['id']+'/home1/Window glass'].node_tree.nodes['Principled BSDF']
assert not glass.inputs['Normal'].is_linked
assert glass.inputs['Transmission Weight'].default_value > 0

district_step(dict(phase='lighting'), CONFIG)
scene=bpy.context.scene
lighting_objects=len(scene.objects)
district_step(dict(phase='lighting'), CONFIG)
assert len(scene.objects)==lighting_objects, 'Lighting updates must not duplicate sun/camera'
assert scene.cycles.samples==16 and scene.cycles.seed==CONFIG['seed']
assert scene.cycles.use_denoising and scene.cycles.use_adaptive_sampling
assert scene.cycles.denoising_prefilter=='ACCURATE'
assert scene.cycles.transmission_bounces==8
assert not scene.world.node_tree.nodes['Village sky'].sun_disc
sky=scene.world.node_tree.nodes['Village sky']
expected=Vector((math.cos(sky.sun_elevation)*math.cos(sky.sun_rotation),
                 math.cos(sky.sun_elevation)*math.sin(sky.sun_rotation), math.sin(sky.sun_elevation)))
actual=bpy.data.objects['Village sun'].rotation_euler.to_matrix() @ Vector((0,0,1))
assert (actual-expected).length < .0001
camera=scene.camera
camera.location=(-40,-115,60)
camera.rotation_euler=(Vector((-40,-40,1))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.lens=40
scene.render.filepath=str(Path(ROOT)/'surfaces.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(Path(ROOT)/'surfaces.blend'))
'''
    script = tmp_path / 'surface_check.py'
    script.write_text(source, encoding='utf-8')
    result = subprocess.run([blender, '--background', '--python-exit-code', '1', '--python', str(script)],
                            capture_output=True, text=True, timeout=300, check=False)
    (tmp_path / 'surface_check.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    assert result.returncode == 0, (result.stdout + result.stderr)[-4000:]
    assert (tmp_path / 'surfaces.png').read_bytes().startswith(b'\x89PNG')
    assert (tmp_path / 'surfaces.blend').stat().st_size > 0
