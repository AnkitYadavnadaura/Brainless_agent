import bpy
import json
from pathlib import Path
_project = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\capability-sandbox\\4d1daead-ee86-481c-8f9b-876e699dbd0b\\house_boundary_02.blend'
_marker = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\capability-sandbox\\4d1daead-ee86-481c-8f9b-876e699dbd0b\\blender-complete.json'
_step = 0
_step_delay = 0.8

def _run_step():
    global _step
    if _step >= 21:
        bpy.ops.wm.save_as_mainfile(filepath=_project)
        Path(_marker).write_text(json.dumps({'status': 'completed', 'steps': _step}), encoding='utf-8')
        return None
    if _step == 0:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(0.0, 0.0, 2.5)
        obj.scale=(6.0, 5.0, 2.5)
        obj.rotation_euler=(0.0, 0.0, 0.0)
        bpy.context.active_object.name='House_Main'
    if _step == 1:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(0.0, 0.0, 5.5)
        obj.scale=(6.5, 5.5, 0.5)
        obj.rotation_euler=(0.0, 0.0, 0.0)
        bpy.context.active_object.name='Roof'
    if _step == 2:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(-3.5, -5.1, 3.0)
        obj.scale=(1.2, 0.2, 1.0)
        obj.rotation_euler=(0.0, 0.0, 0.0)
        bpy.context.active_object.name='Window_1'
    if _step == 3:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(0.0, -5.1, 3.0)
        obj.scale=(1.2, 0.2, 1.0)
        obj.rotation_euler=(0.0, 0.0, 0.0)
        bpy.context.active_object.name='Window_2'
    if _step == 4:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(3.5, -5.1, 3.0)
        obj.scale=(1.2, 0.2, 1.0)
        obj.rotation_euler=(0.0, 0.0, 0.0)
        bpy.context.active_object.name='Window_3'
    if _step == 5:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(-2.0, -7.0, 1.5)
        obj.scale=(1.5, 0.3, 1.5)
        obj.rotation_euler=(0.0, 0.0, 0.0)
        bpy.context.active_object.name='Gate_1'
    if _step == 6:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(2.0, -7.0, 1.5)
        obj.scale=(1.5, 0.3, 1.5)
        obj.rotation_euler=(0.0, 0.0, 0.0)
        bpy.context.active_object.name='Gate_2'
    if _step == 7:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(-10.0, 0.0, 1.5)
        obj.scale=(0.3, 10.0, 1.5)
        obj.rotation_euler=(0.0, 0.0, 0.0)
        bpy.context.active_object.name='Boundary_Left'
    if _step == 8:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(10.0, 0.0, 1.5)
        obj.scale=(0.3, 10.0, 1.5)
        obj.rotation_euler=(0.0, 0.0, 0.0)
        bpy.context.active_object.name='Boundary_Right'
    if _step == 9:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(0.0, 10.0, 1.5)
        obj.scale=(10.0, 0.3, 1.5)
        obj.rotation_euler=(0.0, 0.0, 0.0)
        bpy.context.active_object.name='Boundary_Back'
    if _step == 10:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(-7.0, -10.0, 1.5)
        obj.scale=(3.0, 0.3, 1.5)
        obj.rotation_euler=(0.0, 0.0, 0.0)
        bpy.context.active_object.name='Boundary_Front_Left'
    if _step == 11:
        bpy.ops.mesh.primitive_cube_add()
        obj=bpy.context.active_object
        obj.location=(7.0, -10.0, 1.5)
        obj.scale=(3.0, 0.3, 1.5)
        obj.rotation_euler=(0.0, 0.0, 0.0)
        bpy.context.active_object.name='Boundary_Front_Right'
    if _step == 12:
        obj=bpy.context.active_object
        if obj is None or obj.type!='MESH': raise ValueError('Bevel requires a mesh target')
        modifier=obj.modifiers.new('Bevel','BEVEL')
        modifier.width=0.15
        modifier.segments=3
        modifier.limit_method='ANGLE'
    if _step == 13:
        obj=bpy.context.active_object
        if obj is None or obj.type!='MESH': raise ValueError('Bevel requires a mesh target')
        modifier=obj.modifiers.new('Bevel','BEVEL')
        modifier.width=0.15
        modifier.segments=3
        modifier.limit_method='ANGLE'
    if _step == 14:
        obj=bpy.context.active_object
        if obj is None or obj.type!='MESH': raise ValueError('Bevel requires a mesh target')
        modifier=obj.modifiers.new('Bevel','BEVEL')
        modifier.width=0.1
        modifier.segments=3
        modifier.limit_method='ANGLE'
    if _step == 15:
        obj=bpy.context.active_object
        if obj is None or obj.type!='MESH': raise ValueError('Bevel requires a mesh target')
        modifier=obj.modifiers.new('Bevel','BEVEL')
        modifier.width=0.1
        modifier.segments=3
        modifier.limit_method='ANGLE'
    if _step == 16:
        obj=bpy.context.active_object
        if obj is None or obj.type!='MESH': raise ValueError('Bevel requires a mesh target')
        modifier=obj.modifiers.new('Bevel','BEVEL')
        modifier.width=0.1
        modifier.segments=3
        modifier.limit_method='ANGLE'
    if _step == 17:
        obj=bpy.context.active_object
        if obj is None or obj.type!='MESH': raise ValueError('Bevel requires a mesh target')
        modifier=obj.modifiers.new('Bevel','BEVEL')
        modifier.width=0.1
        modifier.segments=3
        modifier.limit_method='ANGLE'
    if _step == 18:
        obj=bpy.context.active_object
        if obj is None or obj.type!='MESH': raise ValueError('Bevel requires a mesh target')
        modifier=obj.modifiers.new('Bevel','BEVEL')
        modifier.width=0.1
        modifier.segments=3
        modifier.limit_method='ANGLE'
    if _step == 19:
        obj=bpy.context.active_object
        if obj is None or obj.type!='MESH': raise ValueError('Bevel requires a mesh target')
        modifier=obj.modifiers.new('Bevel','BEVEL')
        modifier.width=0.1
        modifier.segments=3
        modifier.limit_method='ANGLE'
    if _step == 20:
        obj=bpy.context.active_object
        if obj is None or obj.type!='MESH': raise ValueError('Bevel requires a mesh target')
        modifier=obj.modifiers.new('Bevel','BEVEL')
        modifier.width=0.1
        modifier.segments=3
        modifier.limit_method='ANGLE'
    bpy.context.view_layer.update()
    _step += 1
    return _step_delay

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.app.timers.register(_run_step, first_interval=0.5)
