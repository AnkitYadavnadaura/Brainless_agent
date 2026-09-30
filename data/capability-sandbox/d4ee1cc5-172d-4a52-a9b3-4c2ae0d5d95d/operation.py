import bpy
m=bpy.data.materials.get('wall_material') or bpy.data.materials.new('wall_material')
m.diffuse_color=(0.2, 0.4, 0.8, 1.0)
obj=bpy.context.object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\capability-sandbox\\d4ee1cc5-172d-4a52-a9b3-4c2ae0d5d95d\\scene.blend')
def _brainless_quit():
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(_brainless_quit, first_interval=1.0)
