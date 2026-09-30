import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_plane_add()
obj=bpy.context.active_object
obj.location=(0.0, 0.0, 0.0)
obj.scale=(12.0, 10.0, 1.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='VillageGround'
m=bpy.data.materials.get('GrassMaterial') or bpy.data.materials.new('GrassMaterial')
m.diffuse_color=(0.18, 0.45, 0.12, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_plane_add()
obj=bpy.context.active_object
obj.location=(0.0, 0.0, 0.03)
obj.scale=(1.2, 10.0, 1.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='MainRoad'
m=bpy.data.materials.get('RoadMaterial') or bpy.data.materials.new('RoadMaterial')
m.diffuse_color=(0.18, 0.18, 0.16, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_plane_add()
obj=bpy.context.active_object
obj.location=(0.0, 1.0, 0.04)
obj.scale=(7.0, 1.0, 1.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='CrossRoad'
m=bpy.data.materials.get('CrossRoadMaterial') or bpy.data.materials.new('CrossRoadMaterial')
m.diffuse_color=(0.2, 0.2, 0.18, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-5.0, -5.0, 1.5)
obj.scale=(2.0, 1.8, 1.5)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='HouseA'
m=bpy.data.materials.get('HouseAWalls') or bpy.data.materials.new('HouseAWalls')
m.diffuse_color=(0.72, 0.5, 0.3, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-5.0, -5.0, 3.3)
obj.scale=(2.2, 2.0, 0.35)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='HouseARoof'
m=bpy.data.materials.get('RoofMaterial') or bpy.data.materials.new('RoofMaterial')
m.diffuse_color=(0.45, 0.12, 0.08, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(5.0, -4.5, 1.5)
obj.scale=(2.0, 1.8, 1.5)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='HouseB'
m=bpy.data.materials.get('HouseBWalls') or bpy.data.materials.new('HouseBWalls')
m.diffuse_color=(0.82, 0.67, 0.45, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(5.0, -4.5, 3.3)
obj.scale=(2.2, 2.0, 0.35)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='HouseBRoof'
m=bpy.data.materials.get('HouseBRoofMaterial') or bpy.data.materials.new('HouseBRoofMaterial')
m.diffuse_color=(0.5, 0.16, 0.1, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-5.0, 5.0, 1.5)
obj.scale=(2.0, 1.8, 1.5)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='HouseC'
m=bpy.data.materials.get('HouseCWalls') or bpy.data.materials.new('HouseCWalls')
m.diffuse_color=(0.68, 0.72, 0.55, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-5.0, 5.0, 3.3)
obj.scale=(2.2, 2.0, 0.35)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='HouseCRoof'
m=bpy.data.materials.get('HouseCRoofMaterial') or bpy.data.materials.new('HouseCRoofMaterial')
m.diffuse_color=(0.35, 0.18, 0.08, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(5.0, 5.0, 1.5)
obj.scale=(2.0, 1.8, 1.5)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='HouseD'
m=bpy.data.materials.get('HouseDWalls') or bpy.data.materials.new('HouseDWalls')
m.diffuse_color=(0.75, 0.58, 0.38, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(5.0, 5.0, 3.3)
obj.scale=(2.2, 2.0, 0.35)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='HouseDRoof'
m=bpy.data.materials.get('HouseDRoofMaterial') or bpy.data.materials.new('HouseDRoofMaterial')
m.diffuse_color=(0.42, 0.1, 0.06, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, 6.5, 2.0)
obj.scale=(2.5, 1.7, 2.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='VillageHall'
m=bpy.data.materials.get('HallMaterial') or bpy.data.materials.new('HallMaterial')
m.diffuse_color=(0.65, 0.48, 0.3, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cone_add()
obj=bpy.context.active_object
obj.location=(0.0, 6.5, 4.5)
obj.scale=(3.0, 2.2, 1.2)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='HallRoof'
m=bpy.data.materials.get('HallRoofMaterial') or bpy.data.materials.new('HallRoofMaterial')
m.diffuse_color=(0.38, 0.08, 0.05, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cylinder_add()
obj=bpy.context.active_object
obj.location=(-2.5, 1.8, 0.7)
obj.scale=(0.8, 0.8, 0.7)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='VillageWell'
m=bpy.data.materials.get('StoneMaterial') or bpy.data.materials.new('StoneMaterial')
m.diffuse_color=(0.38, 0.38, 0.34, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(-2.5, 1.8, 2.2)
obj.scale=(1.1, 1.1, 0.15)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='WellRoof'
m=bpy.data.materials.get('WoodMaterial') or bpy.data.materials.new('WoodMaterial')
m.diffuse_color=(0.3, 0.16, 0.07, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, -6.0, 0.06)
obj.scale=(0.12, 0.7, 0.02)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='RoadMarker1'
m=bpy.data.materials.get('RoadMarkMaterial') or bpy.data.materials.new('RoadMarkMaterial')
m.diffuse_color=(0.9, 0.8, 0.5, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, -3.5, 0.06)
obj.scale=(0.12, 0.7, 0.02)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='RoadMarker2'
m=bpy.data.materials.get('RoadMarkMaterial2') or bpy.data.materials.new('RoadMarkMaterial2')
m.diffuse_color=(0.9, 0.8, 0.5, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, 3.5, 0.06)
obj.scale=(0.12, 0.7, 0.02)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='RoadMarker3'
m=bpy.data.materials.get('RoadMarkMaterial3') or bpy.data.materials.new('RoadMarkMaterial3')
m.diffuse_color=(0.9, 0.8, 0.5, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(0.0, 6.0, 0.06)
obj.scale=(0.12, 0.7, 0.02)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='RoadMarker4'
m=bpy.data.materials.get('RoadMarkMaterial4') or bpy.data.materials.new('RoadMarkMaterial4')
m.diffuse_color=(0.9, 0.8, 0.5, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cylinder_add()
obj=bpy.context.active_object
obj.location=(-8.0, -2.0, 1.2)
obj.scale=(0.35, 0.35, 1.2)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Tree1'
m=bpy.data.materials.get('TreeTrunk') or bpy.data.materials.new('TreeTrunk')
m.diffuse_color=(0.3, 0.16, 0.06, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_uv_sphere_add()
obj=bpy.context.active_object
obj.location=(-8.0, -2.0, 2.8)
obj.scale=(1.3, 1.3, 1.3)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='TreeCrown1'
m=bpy.data.materials.get('LeafMaterial') or bpy.data.materials.new('LeafMaterial')
m.diffuse_color=(0.08, 0.38, 0.08, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cylinder_add()
obj=bpy.context.active_object
obj.location=(8.0, 2.5, 1.2)
obj.scale=(0.35, 0.35, 1.2)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Tree2'
m=bpy.data.materials.get('Tree2Trunk') or bpy.data.materials.new('Tree2Trunk')
m.diffuse_color=(0.3, 0.16, 0.06, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_uv_sphere_add()
obj=bpy.context.active_object
obj.location=(8.0, 2.5, 2.8)
obj.scale=(1.3, 1.3, 1.3)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='TreeCrown2'
m=bpy.data.materials.get('LeafMaterial2') or bpy.data.materials.new('LeafMaterial2')
m.diffuse_color=(0.08, 0.4, 0.1, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_cylinder_add()
obj=bpy.context.active_object
obj.location=(-8.0, 7.0, 1.2)
obj.scale=(0.35, 0.35, 1.2)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Tree3'
m=bpy.data.materials.get('Tree3Trunk') or bpy.data.materials.new('Tree3Trunk')
m.diffuse_color=(0.3, 0.16, 0.06, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.mesh.primitive_uv_sphere_add()
obj=bpy.context.active_object
obj.location=(-8.0, 7.0, 2.8)
obj.scale=(1.3, 1.3, 1.3)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='TreeCrown3'
m=bpy.data.materials.get('LeafMaterial3') or bpy.data.materials.new('LeafMaterial3')
m.diffuse_color=(0.08, 0.4, 0.1, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.object.camera_add()
obj=bpy.context.active_object
obj.location=(17.0, -19.0, 16.0)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(0.95, 0.0, 0.7)
bpy.context.active_object.name='VillageCamera'
bpy.context.scene.camera = bpy.context.active_object
bpy.ops.object.light_add(type='AREA')
obj=bpy.context.active_object
obj.location=(4.0, -4.0, 18.0)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(0.35, -0.45, -0.4)
bpy.context.active_object.name='SunLight'
bpy.context.active_object.data.energy=4.0
bpy.ops.object.light_add(type='AREA')
obj=bpy.context.active_object
obj.location=(-10.0, -4.0, 10.0)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(0.8, 0.0, -0.8)
bpy.context.active_object.name='FillLight'
bpy.context.active_object.data.energy=1200.0
bpy.context.scene.render.filepath = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\capability-sandbox\\a4045fda-ac17-41f3-a3dd-89784a9689a4\\render.png'
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\capability-sandbox\\a4045fda-ac17-41f3-a3dd-89784a9689a4\\scene.blend')
