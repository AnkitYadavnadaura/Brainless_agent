import bpy, json
if bpy.data.objects.get('Dwarika_Column_CL'): raise ValueError('Object name already exists')
bpy.ops.mesh.primitive_cylinder_add()
obj=bpy.context.active_object
obj.location=(-3.0, -19.0, 5.0)
obj.scale=(0.7, 0.7, 5.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Dwarika_Column_CL'
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\5c0724c80c78610b8f36\\revision-4\\00019.blend')

_report={'operation':'add_cylinder','objects':[{'name':o.name,'type':o.type,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale)} for o in bpy.context.scene.objects]}
with open('C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\5c0724c80c78610b8f36\\revision-4\\00019.json','w',encoding='utf-8') as stream: json.dump(_report,stream)
