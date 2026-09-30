import bpy, json
if bpy.data.objects.get('Dwarika_TowerFinial'): raise ValueError('Object name already exists')
bpy.ops.mesh.primitive_cone_add()
obj=bpy.context.active_object
obj.location=(0.0, 0.0, 37.0)
obj.scale=(0.8, 0.8, 2.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Dwarika_TowerFinial'
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\5c0724c80c78610b8f36\\revision-4\\00015.blend')

_report={'operation':'add_cone','objects':[{'name':o.name,'type':o.type,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale)} for o in bpy.context.scene.objects]}
with open('C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\5c0724c80c78610b8f36\\revision-4\\00015.json','w',encoding='utf-8') as stream: json.dump(_report,stream)
