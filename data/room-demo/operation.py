import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.object.camera_add()
bpy.context.scene.camera = bpy.context.object
bpy.ops.object.light_add(type='AREA')
bpy.ops.object.light_add(type='AREA')
bpy.context.scene.render.filepath = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\room-demo\\room.png'
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\room-demo\\room.blend')
