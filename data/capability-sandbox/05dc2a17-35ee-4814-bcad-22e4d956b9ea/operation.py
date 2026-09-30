import bpy
m=bpy.data.materials.get('Tree3TrunkMaterial') or bpy.data.materials.new('Tree3TrunkMaterial')
m.diffuse_color=(0.3, 0.15, 0.06, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_uv_sphere_add()
obj=bpy.context.active_object
obj.location=(-9.0, 7.0, 3.0)
obj.scale=(1.4, 1.4, 1.4)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Tree3Crown'
m=bpy.data.materials.get('Tree3Leaves') or bpy.data.materials.new('Tree3Leaves')
m.diffuse_color=(0.08, 0.38, 0.09, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, -7.0, 0.07)
obj.scale=(0.12, 0.8, 0.03)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='RoadMarker1'
m=bpy.data.materials.get('RoadMark1') or bpy.data.materials.new('RoadMark1')
m.diffuse_color=(0.9, 0.8, 0.45, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, -4.0, 0.07)
obj.scale=(0.12, 0.8, 0.03)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='RoadMarker2'
m=bpy.data.materials.get('RoadMark2') or bpy.data.materials.new('RoadMark2')
m.diffuse_color=(0.9, 0.8, 0.45, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, 5.0, 0.07)
obj.scale=(0.12, 0.8, 0.03)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='RoadMarker3'
m=bpy.data.materials.get('RoadMark3') or bpy.data.materials.new('RoadMark3')
m.diffuse_color=(0.9, 0.8, 0.45, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.object.camera_add()
obj=bpy.context.active_object
obj.location=(18.0, -21.0, 17.0)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(1.0, 0.0, 0.7)
bpy.context.active_object.name='VillageCamera'
bpy.context.scene.camera = bpy.context.active_object
bpy.ops.object.light_add(type='AREA')
obj=bpy.context.active_object
obj.location=(6.0, -8.0, 18.0)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(0.4, -0.5, -0.4)
bpy.context.active_object.name='Sun'
bpy.context.active_object.data.energy=4.0
bpy.ops.object.light_add(type='AREA')
obj=bpy.context.active_object
obj.location=(-10.0, -6.0, 10.0)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(0.7, 0.0, -0.8)
bpy.context.active_object.name='Fill'
bpy.context.active_object.data.energy=1000.0
bpy.context.scene.render.filepath = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\capability-sandbox\\05dc2a17-35ee-4814-bcad-22e4d956b9ea\\render.png'
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\capability-sandbox\\05dc2a17-35ee-4814-bcad-22e4d956b9ea\\scene.blend')
