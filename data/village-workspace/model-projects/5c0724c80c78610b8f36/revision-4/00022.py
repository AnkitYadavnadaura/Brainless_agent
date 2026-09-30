import bpy, json
if bpy.data.objects.get('Dwarika_RightFacadeArch'): raise ValueError('Object name already exists')
"""Trusted architectural primitives with bounded, deterministic geometry."""
import math


def build_architectural_primitive(kind, name):
    import bpy
    vertices, faces = [], []
    if kind == 'add_dome':
        profile = [(.8,0),(.85,.18),(.96,.4),(1,.65),(.94,.95),(.77,1.25),(.5,1.55),(.22,1.82)]
        segments=64
        for radius,z in profile:
            vertices.extend((radius*math.cos(i*math.tau/segments),radius*math.sin(i*math.tau/segments),z)
                            for i in range(segments))
        faces.append(tuple(range(segments-1,-1,-1)))
        for ring in range(len(profile)-1):
            for i in range(segments):
                nxt=(i+1)%segments
                faces.append((ring*segments+i,ring*segments+nxt,(ring+1)*segments+nxt,(ring+1)*segments+i))
        tip=len(vertices)
        vertices.append((0,0,2))
        offset=(len(profile)-1)*segments
        faces.extend((offset+i,offset+(i+1)%segments,tip) for i in range(segments))
    elif kind == 'add_arch':
        outer=[(-1,0)]+[(x,1.6+1.4*(1-abs(x))**.65) for x in (i/16-1 for i in range(33))]+[(1,0)]
        inner=[(-.8,0)]+[(x*.8,1.6+1.1*(1-abs(x))**.65) for x in (i/16-1 for i in range(33))]+[(.8,0)]
        count=len(outer)
        for y in (-.15,.15):
            vertices.extend((x,y,z) for x,z in outer+inner)
        for i in range(count-1):
            j=i+1
            faces.extend(((i,j,count+j,count+i),(2*count+i,3*count+i,3*count+j,2*count+j),
                          (i,2*count+i,2*count+j,j),(count+i,count+j,3*count+j,3*count+i)))
        faces.extend(((0,count,3*count,2*count),(count-1,3*count-1,4*count-1,2*count-1)))
    else:
        raise ValueError('Unknown architectural primitive')
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    if kind=='add_dome':
        for polygon in mesh.polygons:
            polygon.use_smooth=polygon.index!=0
    return obj

build_architectural_primitive('add_arch','Dwarika_RightFacadeArch')
obj=bpy.context.active_object
obj.location=(9.0, -14.0, 4.0)
obj.scale=(2.5, 0.8, 3.0)
obj.rotation_euler=(0.0, 0.0, 0.0)
bpy.context.active_object.name='Dwarika_RightFacadeArch'
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\5c0724c80c78610b8f36\\revision-4\\00022.blend')

_report={'operation':'add_arch','objects':[{'name':o.name,'type':o.type,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale)} for o in bpy.context.scene.objects]}
with open('C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\model-projects\\5c0724c80c78610b8f36\\revision-4\\00022.json','w',encoding='utf-8') as stream: json.dump(_report,stream)
