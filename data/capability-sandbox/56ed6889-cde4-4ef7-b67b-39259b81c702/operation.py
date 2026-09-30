import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_plane_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cylinder_add()
bpy.ops.mesh.primitive_uv_sphere_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cube_add()
bpy.ops.mesh.primitive_cylinder_add()
bpy.ops.mesh.primitive_uv_sphere_add()
bpy.ops.mesh.primitive_cube_add()
m=bpy.data.materials.get('wall_material') or bpy.data.materials.new('wall_material')
m.diffuse_color=(0.2, 0.4, 0.8, 1.0)
obj=bpy.context.object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
m=bpy.data.materials.get('floor_material') or bpy.data.materials.new('floor_material')
m.diffuse_color=(0.2, 0.4, 0.8, 1.0)
obj=bpy.context.object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
m=bpy.data.materials.get('sofa_material') or bpy.data.materials.new('sofa_material')
m.diffuse_color=(0.2, 0.4, 0.8, 1.0)
obj=bpy.context.object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
m=bpy.data.materials.get('wood_material') or bpy.data.materials.new('wood_material')
m.diffuse_color=(0.2, 0.4, 0.8, 1.0)
obj=bpy.context.object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
m=bpy.data.materials.get('metal_material') or bpy.data.materials.new('metal_material')
m.diffuse_color=(0.2, 0.4, 0.8, 1.0)
obj=bpy.context.object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.object.modifier_add(type='BEVEL')
bpy.ops.object.shade_smooth()
bpy.ops.object.camera_add()
bpy.ops.object.light_add(type='AREA')
bpy.ops.object.light_add(type='AREA')
bpy.ops.object.light_add(type='AREA')
bpy.context.scene.render.filepath = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\capability-sandbox\\56ed6889-cde4-4ef7-b67b-39259b81c702\\render.png'
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\capability-sandbox\\56ed6889-cde4-4ef7-b67b-39259b81c702\\scene.blend')
