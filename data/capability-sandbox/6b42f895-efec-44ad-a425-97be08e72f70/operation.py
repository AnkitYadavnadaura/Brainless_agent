import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, 0.0, 1.5)
obj.scale=(5.0, 4.0, 1.5)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='House_GroundFloor'
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, 0.0, 4.5)
obj.scale=(5.0, 4.0, 1.5)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='House_SecondFloor'
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, 0.0, 6.5)
obj.scale=(5.5, 4.5, 0.5)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Roof'
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, -4.05, 1.5)
obj.scale=(1.0, 0.15, 1.5)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='FrontDoor'
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-2.0, -4.05, 4.5)
obj.scale=(1.2, 0.15, 1.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='UpperWindow'
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(2.0, -4.05, 4.5)
obj.scale=(1.2, 0.15, 1.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='UpperWindow2'
bpy.ops.mesh.primitive_plane_add()
obj=bpy.context.active_object
obj.location=(0.0, 0.0, 0.0)
obj.scale=(10.0, 10.0, 1.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Ground'
bpy.ops.object.camera_add()
obj=bpy.context.active_object
obj.location=(14.0, -18.0, 11.0)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(0.95, 0.0, 0.62)
bpy.context.active_object.name='Camera'
bpy.context.scene.camera = bpy.context.active_object
bpy.ops.object.light_add(type='AREA')
obj=bpy.context.active_object
obj.location=(6.0, -8.0, 12.0)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='KeyLight'
bpy.context.active_object.data.energy=1200.0
bpy.context.scene.render.filepath = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\capability-sandbox\\6b42f895-efec-44ad-a425-97be08e72f70\\render.png'
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\capability-sandbox\\6b42f895-efec-44ad-a425-97be08e72f70\\two_floor_house.blend')
