import bpy
bpy.ops.mesh.primitive_cube_add()
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\capability-sandbox\\4685e33a-e181-422f-988f-2c501101beef\\scene.blend')
def _brainless_quit():
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(_brainless_quit, first_interval=1.0)
