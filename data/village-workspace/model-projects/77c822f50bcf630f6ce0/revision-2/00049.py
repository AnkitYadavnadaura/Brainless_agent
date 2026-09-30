import bpy, json
if bpy.data.objects.get('Taj_Camera'): raise ValueError('Object name already exists')
bpy.ops.object.camera_add()
obj=bpy.context.active_object
obj.location=(34.0, -44.0, 25.0)
obj.scale=(1.0, 1.0, 1.0)
obj.rotation_euler=(1.18, 0.0, 0.66)
bpy.context.active_object.name='Taj_Camera'
bpy.context.scene.camera = bpy.context.active_object
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\77c822f50bcf630f6ce0\\revision-2\\00049.blend')

_report={'operation':'add_camera','objects':[{'name':o.name,'type':o.type,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale)} for o in bpy.context.scene.objects]}
with open('C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\77c822f50bcf630f6ce0\\revision-2\\00049.json','w',encoding='utf-8') as stream: json.dump(_report,stream)
