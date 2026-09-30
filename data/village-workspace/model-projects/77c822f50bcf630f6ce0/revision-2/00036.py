import bpy, json
if bpy.data.objects.get('Taj_GardenRight'): raise ValueError('Object name already exists')
bpy.ops.mesh.primitive_cube_add()
obj=bpy.context.active_object
obj.location=(23.0, 0.0, 0.15)
obj.scale=(5.0, 20.0, 0.15)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Taj_GardenRight'
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\77c822f50bcf630f6ce0\\revision-2\\00036.blend')

_report={'operation':'add_cube','objects':[{'name':o.name,'type':o.type,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale)} for o in bpy.context.scene.objects]}
with open('C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\77c822f50bcf630f6ce0\\revision-2\\00036.json','w',encoding='utf-8') as stream: json.dump(_report,stream)
