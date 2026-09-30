"""Exercise viewport navigation against real Blender data and its timer loop."""
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.skipif(os.environ.get('BRAINLESS_BLENDER_SMOKE') != '1', reason='Opt-in Blender integration')
def test_live_runtime_tracks_edited_geometry_without_camera_or_visibility_side_effects(tmp_path):
    from app.autonomy.blender_capability import find_blender

    blender=find_blender()
    assert blender, 'Blender must be installed for this integration test'
    runtime=Path(__file__).parents[1]/'app'/'autonomy'/'live_blender_runtime.py'
    script=tmp_path/'check_viewport.py'
    script.write_text(f'RUNTIME={str(runtime)!r}\nWORKSPACE={str(tmp_path)!r}\n'+r'''
import bpy, hashlib, importlib.util, json, math, sys
from pathlib import Path
from mathutils import Vector

root=Path(WORKSPACE)/'.live-blender'
root.mkdir()
sys.argv=['blender','--',str(root)]
spec=importlib.util.spec_from_file_location('tested_live_runtime',RUNTIME)
runtime=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
bpy.app.timers.unregister(runtime.tick)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

bpy.ops.object.camera_add(location=(10,-20,15))
camera=bpy.context.object
bpy.context.scene.camera=camera
camera_transform=camera.matrix_world.copy()
bpy.ops.mesh.primitive_cube_add(location=(4,2,1))
body=bpy.context.object
body.name='Body'
for vertex in body.data.vertices:
    vertex.co.x+=3  # Origin is deliberately outside the mesh center.
parent=bpy.data.objects.new('Parent',None)
bpy.context.collection.objects.link(parent)
parent.location=(6,3,2)
parent.rotation_euler.z=.6
body.parent=parent
modifier=body.modifiers.new('Array','ARRAY')
modifier.count=3
modifier.relative_offset_displace=(1.2,0,0)
bpy.ops.mesh.primitive_cube_add(location=(999,999,999))
unrelated=bpy.context.object
unrelated.name='Unrelated'
bpy.ops.mesh.primitive_cube_add(location=(-999,-999,-999))
hidden=bpy.context.object
hidden.name='Originally hidden'
hidden.hide_viewport=True
bpy.context.view_layer.update()

area=next(area for area in bpy.context.window_manager.windows[0].screen.areas if area.type=='VIEW_3D')
view=area.spaces.active.region_3d
orientation=view.view_rotation.copy()
evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
corners=[evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
expected=(Vector(tuple(min(p[i] for p in corners) for i in range(3)))+
          Vector(tuple(max(p[i] for p in corners) for i in range(3))))/2
assert (runtime.world_bounds([body,hidden,camera])[0]-expected).length<1e-5
assert (expected-body.matrix_world.translation).length>4
runtime.follow_view([body,hidden,camera],final=True)
assert (view.view_location-expected).length<1e-4
assert view.view_rotation.rotation_difference(orientation).angle<1e-4
initial_distance=view.view_distance
area.spaces.active.lock_camera=True
view.view_perspective='CAMERA'
runtime.follow_view([body],final=True)
assert view.view_perspective=='PERSP'
assert camera.matrix_world==camera_transform

sequence=0
def start_job(code,**options):
    global sequence
    sequence+=1
    path=Path(WORKSPACE)/f'job{sequence}.py'
    path.write_text(code,encoding='utf-8')
    command=dict(id=str(sequence),script=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                 source=None,project=str(Path(WORKSPACE)/f'{sequence}.blend'),animate=False,focus_view=True)
    command.update(options)
    (root/'command.json').write_text(json.dumps(command),encoding='utf-8')
    runtime.tick()
    return command

def finish_job(command):
    for _ in range(24):
        runtime.tick()
    assert runtime.animation is None
    assert json.loads((root/f'{command["id"]}.json').read_text())['status']=='completed'

# Follow translation/rotation/scale throughout all timer frames and frame the
# final evaluated bounds, not the original origin/size or all objects in scene.
command=start_job("import bpy\nobj=bpy.data.objects['Body']\n"
                  "obj.location=(30,-20,5)\nobj.rotation_euler=(0,0,1.1)\nobj.scale=(4,2,3)\n",
                  animate=True,focus_object='Body')
locations=[]
distances=[]
for _ in range(24):
    runtime.tick()
    locations.append(view.view_location.copy())
    distances.append(view.view_distance)
assert runtime.animation is None
assert sum((a-b).length>1e-4 for a,b in zip(locations,locations[1:]))>20
assert len({round(distance,3) for distance in distances})>20
assert (view.view_location-runtime.world_bounds([body])[0]).length<1e-4
assert view.view_distance>initial_distance*2
assert body.location==Vector((30,-20,5)) and body.scale==Vector((4,2,3))
assert hidden.hide_viewport
assert camera.matrix_world==camera_transform
assert view.view_rotation.rotation_difference(orientation).angle<1e-4

# Non-transform edits focus their explicit target, preserving an unrelated
# active selection, render camera, and the target's actual transforms.
bpy.context.view_layer.objects.active=unrelated
view.view_location=unrelated.location
saved_transform=body.matrix_world.copy()
command=start_job("import bpy\nbpy.data.objects['Body'].modifiers.new('Bevel','BEVEL')\n",focus_object='Body')
assert runtime.animation is not None
finish_job(command)
assert (view.view_location-runtime.world_bounds([body])[0]).length<1e-4
assert bpy.context.active_object==unrelated
assert body.matrix_world==saved_transform and camera.matrix_world==camera_transform

# Revealing newly built geometry must not reveal any originally hidden mesh.
command=start_job("import bpy\nbpy.ops.mesh.primitive_cube_add(location=(2,5,3))\n"
                  "bpy.context.object.name='New visible'\n"
                  "bpy.ops.mesh.primitive_cube_add(location=(500,500,500))\n"
                  "bpy.context.object.name='New hidden'\nbpy.context.object.hide_viewport=True\n")
finish_job(command)
assert hidden.hide_viewport and bpy.data.objects['New hidden'].hide_viewport
assert not bpy.data.objects['New visible'].hide_viewport
assert (view.view_location-Vector((2,5,3))).length<1e-4

# Lights and opt-out jobs never steal the current viewport focus.
previous=view.view_location.copy()
command=start_job("import bpy\nbpy.ops.object.light_add(type='AREA',location=(900,900,900))\n")
assert runtime.animation is None and view.view_location==previous
command=start_job("pass\n",focus_object='Body',focus_view=False)
assert runtime.animation is None and view.view_location==previous

# A user can switch every view to another editor while the timer is running.
for window in bpy.context.window_manager.windows:
    for candidate in window.screen.areas:
        if candidate.type=='VIEW_3D':
            candidate.type='CONSOLE'
command=start_job("pass\n",focus_object='Body')
finish_job(command)
assert camera.matrix_world==camera_transform and hidden.hide_viewport
print('Viewport follow checks passed')
''',encoding='utf-8')
    result=subprocess.run([blender,'--background','--factory-startup','--python-exit-code','1','--python',str(script)],
                          capture_output=True,text=True,timeout=120,check=False)
    assert result.returncode==0,(result.stdout+result.stderr)[-5000:]
    assert 'Viewport follow checks passed' in result.stdout
