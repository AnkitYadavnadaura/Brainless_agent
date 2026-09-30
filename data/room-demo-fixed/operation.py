import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, 0.0, -0.15)
obj.scale=(4.0, 3.0, 0.15)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Floor'
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, 3.0, 2.5)
obj.scale=(4.0, 0.15, 2.5)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='BackWall'
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-4.0, 0.0, 2.5)
obj.scale=(0.15, 3.0, 2.5)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='LeftWall'
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-2.3, 2.78, 1.35)
obj.scale=(0.8, 0.08, 1.35)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Door'
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(1.5, 2.78, 2.5)
obj.scale=(0.9, 0.08, 0.8)
obj.rotation_euler=(0.0, 0.0, 0.1)
bpy.context.active_object.name='Window'
bpy.ops.object.camera_add()
obj=bpy.context.active_object
obj.location=(10.0, -12.0, 8.0)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(1.1, 0.0, 0.68)
bpy.context.active_object.name='RoomCamera'
bpy.context.scene.camera = bpy.context.active_object
bpy.ops.object.light_add(type='AREA')
obj=bpy.context.active_object
obj.location=(0.0, 0.0, 5.5)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='CeilingLight'
bpy.context.scene.render.filepath = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\room-demo-fixed\\room.png'
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\room-demo-fixed\\room.blend')
