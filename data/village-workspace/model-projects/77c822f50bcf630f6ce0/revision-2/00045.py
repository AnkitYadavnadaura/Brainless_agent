import bpy, json
obj=bpy.data.objects.get('Taj_CentralDome')
if obj is None: raise ValueError('Target object is missing')
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active=obj
m=bpy.data.materials.get('DomeMarble') or bpy.data.materials.new('DomeMarble')
m.diffuse_color=(0.96, 0.96, 0.93, 1.0)
m.use_nodes=True
m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(0.96, 0.96, 0.93, 1.0)
obj=bpy.context.active_object
if obj and hasattr(obj.data, 'materials'):
    obj.data.materials.append(m)
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\77c822f50bcf630f6ce0\\revision-2\\00045.blend')

_report={'operation':'add_material','objects':[{'name':o.name,'type':o.type,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale)} for o in bpy.context.scene.objects]}
with open('C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\77c822f50bcf630f6ce0\\revision-2\\00045.json','w',encoding='utf-8') as stream: json.dump(_report,stream)
