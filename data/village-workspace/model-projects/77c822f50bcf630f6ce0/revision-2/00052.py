import bpy, json
bpy.context.scene.render.engine='CYCLES'
bpy.context.scene.cycles.use_denoising=True
bpy.context.scene.cycles.samples=128
bpy.context.scene.render.resolution_x=2560
bpy.context.scene.render.resolution_y=1440
bpy.context.scene.render.resolution_percentage=100
bpy.context.scene.render.filepath = 'C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\77c822f50bcf630f6ce0\\revision-2\\00052.png'
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\77c822f50bcf630f6ce0\\revision-2\\00052.blend')

_report={'operation':'render','objects':[{'name':o.name,'type':o.type,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale)} for o in bpy.context.scene.objects]}
with open('C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\77c822f50bcf630f6ce0\\revision-2\\00052.json','w',encoding='utf-8') as stream: json.dump(_report,stream)
