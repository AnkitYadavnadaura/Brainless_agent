import bpy, json
if bpy.data.objects.get('Taj_MinaretFinial_FL'): raise ValueError('Object name already exists')
bpy.ops.mesh.primitive_cone_add()
obj=bpy.context.active_object
obj.location=(-12.0, -8.0, 17.0)
obj.scale=(0.18, 0.18, 0.8)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Taj_MinaretFinial_FL'
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\77c822f50bcf630f6ce0\\revision-2\\00026.blend')

_report={'operation':'add_cone','objects':[{'name':o.name,'type':o.type,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale)} for o in bpy.context.scene.objects]}
with open('C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\77c822f50bcf630f6ce0\\revision-2\\00026.json','w',encoding='utf-8') as stream: json.dump(_report,stream)
