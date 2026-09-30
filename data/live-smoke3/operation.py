import bpy
import json
from pathlib import Path
_project = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\live-smoke3\\scene.blend'
_marker = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\live-smoke3\\blender-complete.json'
_step = 0
_step_delay = 0.8

def _run_step():
    global _step
    if _step >= 5:
        bpy.ops.wm.save_as_mainfile(filepath=_project)
        Path(_marker).write_text(json.dumps({'status': 'completed', 'steps': _step}), encoding='utf-8')
        return None
    if _step == 0:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    if _step == 1:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(2.0, 0.0, 1.0)
        obj.scale=(2.0, 1.0, 1.0)
        obj.rotation_euler=(0.0, 0.0, 0.3)
        bpy.context.active_object.name='LiveCube'
    if _step == 2:
        m=bpy.data.materials.get('LiveMaterial') or bpy.data.materials.new('LiveMaterial')
        m.diffuse_color=(0.1, 0.4, 0.8, 1.0)
        obj=bpy.context.active_object
        if obj and hasattr(obj.data, 'materials'):
            obj.data.materials.append(m)
    if _step == 3:
        bpy.ops.object.camera_add()
        obj=bpy.context.active_object
        obj.location=(8.0, -8.0, 6.0)
        obj.scale=(1.0, 1.0, 1.0)
        obj.rotation_euler=(1.1, 0.0, 0.8)
        bpy.context.active_object.name='LiveCamera'
        bpy.context.scene.camera = bpy.context.active_object
    if _step == 4:
        bpy.context.scene.render.filepath = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\live-smoke3\\render.png'
    bpy.context.view_layer.update()
    _step += 1
    return _step_delay

bpy.app.timers.register(_run_step, first_interval=0.5)
