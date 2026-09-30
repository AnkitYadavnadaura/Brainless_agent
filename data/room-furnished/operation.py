import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, 0.0, -0.15)
obj.scale=(4.0, 3.0, 0.15)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Floor'
m=bpy.data.materials.get('WarmFloor') or bpy.data.materials.new('WarmFloor')
m.diffuse_color=(0.28, 0.12, 0.05, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, 3.0, 2.5)
obj.scale=(4.0, 0.15, 2.5)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='BackWall'
m=bpy.data.materials.get('WallPaint') or bpy.data.materials.new('WallPaint')
m.diffuse_color=(0.72, 0.68, 0.58, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-4.0, 0.0, 2.5)
obj.scale=(0.15, 3.0, 2.5)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='LeftWall'
m=bpy.data.materials.get('WallPaint') or bpy.data.materials.new('WallPaint')
m.diffuse_color=(0.72, 0.68, 0.58, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-2.3, 2.78, 1.35)
obj.scale=(0.8, 0.08, 1.35)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Door'
m=bpy.data.materials.get('DoorWood') or bpy.data.materials.new('DoorWood')
m.diffuse_color=(0.18, 0.06, 0.025, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(1.3, 2.78, 2.5)
obj.scale=(1.1, 0.06, 0.85)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='WindowGlass'
m=bpy.data.materials.get('WindowGlass') or bpy.data.materials.new('WindowGlass')
m.diffuse_color=(0.08, 0.35, 0.65, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(1.8, 0.4, 0.55)
obj.scale=(1.45, 1.8, 0.45)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='BedBase'
m=bpy.data.materials.get('BedWood') or bpy.data.materials.new('BedWood')
m.diffuse_color=(0.22, 0.08, 0.03, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(1.8, 0.4, 1.05)
obj.scale=(1.35, 1.7, 0.15)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Mattress'
m=bpy.data.materials.get('Mattress') or bpy.data.materials.new('Mattress')
m.diffuse_color=(0.85, 0.85, 0.78, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(1.8, 1.55, 1.28)
obj.scale=(1.0, 0.3, 0.12)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Pillow'
m=bpy.data.materials.get('Pillow') or bpy.data.materials.new('Pillow')
m.diffuse_color=(0.95, 0.95, 0.9, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-1.8, -1.25, 1.45)
obj.scale=(1.25, 0.55, 0.1)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='DeskTop'
m=bpy.data.materials.get('DeskWood') or bpy.data.materials.new('DeskWood')
m.diffuse_color=(0.35, 0.14, 0.04, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-1.8, -1.25, 0.7)
obj.scale=(1.05, 0.4, 0.65)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='DeskLeg'
m=bpy.data.materials.get('DeskWood') or bpy.data.materials.new('DeskWood')
m.diffuse_color=(0.35, 0.14, 0.04, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-1.8, -0.25, 0.75)
obj.scale=(0.5, 0.5, 0.1)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='ChairSeat'
m=bpy.data.materials.get('Chair') or bpy.data.materials.new('Chair')
m.diffuse_color=(0.05, 0.18, 0.32, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-1.8, 0.18, 1.35)
obj.scale=(0.5, 0.1, 0.65)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='ChairBack'
m=bpy.data.materials.get('Chair') or bpy.data.materials.new('Chair')
m.diffuse_color=(0.05, 0.18, 0.32, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, -0.3, 0.03)
obj.scale=(1.5, 1.0, 0.03)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Rug'
m=bpy.data.materials.get('Rug') or bpy.data.materials.new('Rug')
m.diffuse_color=(0.45, 0.08, 0.06, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-1.65, 2.62, 1.35)
obj.scale=(0.08, 0.08, 0.08)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='DoorHandle'
m=bpy.data.materials.get('Metal') or bpy.data.materials.new('Metal')
m.diffuse_color=(0.8, 0.55, 0.12, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.object.camera_add()
obj=bpy.context.active_object
obj.location=(10.0, -13.0, 8.0)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(1.12, 0.0, 0.64)
bpy.context.active_object.name='RoomCamera'
bpy.context.scene.camera = bpy.context.active_object
bpy.ops.object.light_add(type='AREA')
obj=bpy.context.active_object
obj.location=(0.0, 0.0, 5.5)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='CeilingLight'
bpy.ops.object.light_add(type='AREA')
obj=bpy.context.active_object
obj.location=(1.0, 1.0, 4.0)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='WindowLight'
bpy.context.scene.render.filepath = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\room-furnished\\room.png'
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\room-furnished\\room.blend')
