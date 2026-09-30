"""Trusted Blender district/object compiler; no model-generated source execution."""
import math
import random

# The adapter embeds both trusted modules in one Blender script. Normal package
# imports also work for tooling that calls the compiler from a Blender session.
if __package__:
    from .village_scene import _village_material, build_stage


def district_step(job, config):
    import bpy
    from mathutils import Vector
    phase = job['phase']
    component = job.get('component')
    area = job.get('area')
    spec = job.get('object')
    prefix = area['id'] if area else 'world'
    if spec:
        prefix += '/' + spec['id']
    rng = random.Random(str(config['seed']) + prefix)
    created=[]

    def mat(name, color, roughness=.8, metallic=0):
        return _village_material(prefix+'/'+name, color, roughness, metallic)

    stone=mat('Stone',(.3,.28,.23))
    wood=mat('Timber',(.17,.085,.035))
    plaster=mat('Plaster',(.55+rng.random()*.12,.48,.35))
    leaf=mat('Foliage',(.075,.20,.025))
    metal=mat('Metal',(.18,.23,.22),.45,.75)

    def mesh(name, vertices, faces, material):
        data=bpy.data.meshes.new(prefix+'/'+name)
        data.from_pydata(vertices,[],faces)
        data.materials.append(material)
        obj=bpy.data.objects.new(prefix+'/'+name,data)
        bpy.context.collection.objects.link(obj)
        obj['district_id']=area['id'] if area else 'world'
        obj['logical_object']=prefix
        obj['phase']=phase
        obj['component']=component or phase
        created.append(obj)
        return obj

    def box(name,x,y,z,w,d,h,material):
        obj=mesh(name,[(x+dx*w/2,y+dy*d/2,z+dz*h/2) for dx,dy,dz in
            ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))],
            [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material)
        # Convex bevels cut inward, retaining the approved footprint. The network
        # surfaces keep their exact edges where districts meet.
        if name not in ('Ground', 'Block ground', 'East west road', 'North south road',
                        'Connected water channel', 'Pond', 'Window glass'):
            bevel=obj.modifiers.new('Edge highlights','BEVEL')
            bevel.width=min(.035,min(w,d,h)*.12)
            bevel.segments=3
            bevel.use_clamp_overlap=True
            bevel.harden_normals=True
            for polygon in obj.data.polygons:
                polygon.use_smooth=True
            normals=obj.modifiers.new('Surface normals','WEIGHTED_NORMAL')
            normals.keep_sharp=True
            normals.weight=50
        return obj

    def cylinder(name, start, end, radius, material, segments=16):
        a,b=Vector(start),Vector(end)
        direction=(b-a).normalized()
        u=direction.cross(Vector((0,0,1)))
        if u.length<.01:
            u=Vector((1,0,0))
        u.normalize()
        v=direction.cross(u)
        vertices=[tuple(center+radius*(math.cos(i*math.tau/segments)*u+math.sin(i*math.tau/segments)*v))
                  for center in (a,b) for i in range(segments)]
        faces=[tuple(range(segments-1,-1,-1)),tuple(range(segments,2*segments))]
        faces.extend((i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments))
        obj=mesh(name,vertices,faces,material)
        for polygon in obj.data.polygons[2:]:
            polygon.use_smooth=True
        return obj

    def foliage(name,x,y,z,w,d,h):
        # Leaf clusters are actual double-sided leaf geometry rather than solid crown balls.
        vertices,faces=[],[]
        for _ in range(240):
            theta=rng.random()*math.tau
            vertical=rng.uniform(-1,1)
            radius=math.sqrt(1-vertical*vertical)*rng.random()**(1/3)
            px=x+math.cos(theta)*radius*w/2
            py=y+math.sin(theta)*radius*d/2
            pz=z+vertical*h/2
            size=rng.uniform(.06,.18)
            tilt=rng.uniform(-.6,.6)*size
            base=len(vertices)
            vertices.extend(((px-size,py,pz-tilt),(px,py-size/2,pz+.025),(px+size,py,pz+tilt),(px,py+size/2,pz-.025)))
            faces.append(tuple(base+i for i in range(4)))
        obj=mesh(name,vertices,faces,leaf)
        for index, color in enumerate(((.11,.23,.035),(.16,.26,.06))):
            obj.data.materials.append(mat('Foliage variation '+str(index),color,.65))
        for polygon in obj.data.polygons:
            polygon.material_index=rng.randrange(3)
        return obj

    if phase=='world':
        bpy.ops.wm.read_factory_settings(use_empty=True)
        # Materials created above were reset together with the scene.
        stone=mat('Soil',(.20,.24,.10))
        size=config['extent']*2
        # The camera sees beyond the settlement; retain a ground backdrop there.
        box('Ground',0,0,-.7,size*2,size*2,1,stone)
    elif phase=='infrastructure':
        xmin,ymin,xmax,ymax=area['bounds']
        cx,cy=area['center']
        size=xmax-xmin
        road=mat('Gravel',(.22,.19,.145))
        # Exact global endpoints, widths and elevations are identical across neighbours.
        if component in (None, 'block'):
            # Keep the block surface above world ground (-.2) to avoid z-fighting.
            earth=mat('Settlement soil',(.20,.235,.10))
            box('Block ground',cx,cy,-.29,size,size,.2,earth)
        if component in (None, 'gully_east_west'):
            box('East west road',cx,cy,-.06,size,4,.18,road)
        if component in (None, 'gully_north_south'):
            box('North south road',cx,cy,-.055,4,size,.18,road)
        if component in (None, 'drainage'):
            channel=area['channel_y']
            water=mat('Water',(.025,.095,.075),.12)
            shader=water.node_tree.nodes.get('Principled BSDF')
            shader.inputs['Transmission Weight'].default_value=.65
            shader.inputs['IOR'].default_value=1.333
            box('Connected water channel',cx,channel,area['water_level'],size,1.2,.025,water)
            for side in (-1,1):
                for direction in (-1,1):
                    length=size/2-2
                    box('Channel retaining wall',cx+direction*(2+length/2),channel+side*.7,-.05,length,.2,.4,stone)
            box('Road bridge',cx,channel,-.095,4,2,.25,stone)
    elif phase in ('create','polish'):
        x,y,w,d,h=spec['x'],spec['y'],spec['width'],spec['depth'],spec['height']
        kind=spec['kind']
        if phase=='create':
            if kind in ('house','villa'):
                if component in (None, 'foundation'):
                    box('Foundation',x,y,.15,w+.2,d+.2,.7,stone)
                if component is None:
                    box('Walls',x,y,h/2+.5,w,d,h,plaster)
                elif component in ('wall_south','wall_north'):
                    side=-1 if component=='wall_south' else 1
                    box(component,x,y+side*(d/2-.1),h/2+.5,w,.2,h,plaster)
                elif component in ('wall_west','wall_east'):
                    side=-1 if component=='wall_west' else 1
                    box(component,x+side*(w/2-.1),y,h/2+.5,.2,max(.1,d-.4),h,plaster)
                if component in (None, 'roof'):
                    roof=mat('Terracotta',(.25,.065,.025))
                    mesh('Roof',[(x-w/2-.2,y-d/2-.2,h+.5),(x+w/2+.2,y-d/2-.2,h+.5),
                        (x,y-d/2-.2,h+.5+w*.3),(x-w/2-.2,y+d/2+.2,h+.5),
                        (x+w/2+.2,y+d/2+.2,h+.5),(x,y+d/2+.2,h+.5+w*.3)],
                        [(0,1,2),(3,5,4),(0,2,5,3),(2,1,4,5)],roof)
                if component in (None, 'entrance'):
                    # Connect each entrance to the same local road network, with paths at ground level.
                    cy=area['center'][1]
                    front=y-d/2-1.25
                    cx=area['center'][0]
                    # An L-shaped path reaches the north/south trunk without crossing other plots.
                    box('Entrance landing',x,front,-.075,1.8,1.5,.15,stone)
                    box('Access path', (x+cx)/2,front,-.075,abs(x-cx)+1,1,.15,stone)
                    if kind=='villa':
                        for side in (-1,1):
                            cylinder('Veranda column',(x+side*w*.35,y-d/2-.7,.1),(x+side*w*.35,y-d/2-.7,3),.13,stone)
                        box('Veranda',x,y-d/2-.7,3,w,.9,.18,stone)
            elif kind=='tree':
                cylinder('Trunk',(x,y,-.2),(x,y,h*.75),max(.08,min(w,d)*.06),wood)
                foliage('Canopy',x,y,h*.75,w,d,h*.5)
            elif kind=='plants':
                foliage('Plant bed',x,y,h/2-.1,w,d,h)
            elif kind=='water':
                water=mat('Pond water',(.02,.075,.065),.10)
                water.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value=.65
                box('Pond',x,y,-.17,w,d,.025,water)
                for side in (-1,1):
                    box('Pond bank',x+side*w/2,y,-.07,.2,d,.25,stone)
                    box('Pond bank',x,y+side*d/2,-.07,w,.2,.25,stone)
            elif kind=='drum':
                cylinder('Drum',(x,y,-.15),(x,y,h-.15),min(w,d)/2,metal,32)
            elif kind=='door':
                box('Door',x,y-.045,h/2+.5,w,.09,h,wood)
            elif kind=='stairs':
                for index in range(3):
                    height=.15*(index+1)
                    box('Step',x,y-.25-(2-index)*.3,height/2-.0,w,.32,height,stone)
            elif kind=='gate':
                y-=1.3
                for side in (-1,1):
                    box('Gate post',x+side*w/2,y,h/2,.12,.12,h,wood)
                for z in (.4,1):
                    box('Gate rail',x,y,z,w,.08,.10,wood)
        else:
            detail=int(job['polish']['detail'])
            if kind in ('house','villa'):
                glass=mat('Window glass',(.05,.10,.14),.15)
                for side in (-1,1):
                    px=x+side*w*.28
                    box('Window frame',px,y-d/2-.025,2,.95,.12,1.3,wood)
                    box('Window glass',px,y-d/2-.095,2,.79,.035,1.13,glass)
                    box('Window crossbar',px,y-d/2-.12,2,.045,.04,1.13,wood)
                    box('Window sill',px,y-d/2-.14,1.3,1.1,.3,.07,stone)
                # Tiles are mesh faces in one object, with gaps and overlaps visible in closeups.
                roof=mat('Roof tiles',(.20,.05,.018))
                vertices,faces=[],[]
                for side in (-1,1):
                    rows=max(4,int(w*detail))
                    cols=max(4,int(d*detail))
                    for row in range(rows):
                        for col in range(cols):
                            base=len(vertices)
                            for rr,cc in ((row,col),(row+1.04,col),(row+1.04,col+.96),(row,col+.96)):
                                xx=min(w/2+.2,rr/rows*(w/2+.2))
                                vertices.append((x+side*xx,y-d/2-.2+cc/cols*(d+.4),h+.54+w*.3*(1-xx/(w/2+.2))))
                            faces.append(tuple(base+i for i in range(4)))
                tiles=mesh('Individual roof tiles',vertices,faces,roof)
                for index in range(1,5):
                    tiles.data.materials.append(mat('Roof tile variation '+str(index),
                        (.17+index*.018,.04+index*.005,.016+index*.002)))
                for polygon in tiles.data.polygons:
                    polygon.material_index=rng.randrange(5)
                cylinder('Gutter',(x-w/2-.22,y-d/2,h+.45),(x-w/2-.22,y+d/2,h+.45),.06,metal)
                box('Chimney',x+w*.25,y,h+.9,.45,.5,1.5,stone)
            elif kind=='tree':
                for i in range(4*detail):
                    angle=i*math.tau/(4*detail)
                    end=(x+math.cos(angle)*w*.35,y+math.sin(angle)*d*.35,h*.65+rng.random()*h*.25)
                    cylinder('Branch',(x,y,h*.45),end,.035,wood,8)
                    foliage('Leaf spray',*end,w*.30,d*.30,h*.22)
            elif kind=='plants':
                for _ in range(detail*4):
                    px,py=x+rng.uniform(-w*.4,w*.4),y+rng.uniform(-d*.4,d*.4)
                    cylinder('Plant stem',(px,py,-.2),(px,py,h*.8),.015,leaf,6)
            elif kind=='drum':
                for z in (.15,h*.45,h*.8):
                    cylinder('Raised band',(x,y,z),(x,y,z+.045),min(w,d)*.515,metal,48)
                cylinder('Cap',(x+w*.18,y,h-.14),(x+w*.18,y,h-.10),.055,metal,16)
            elif kind=='door':
                cylinder('Door handle',(x+w*.32,y-.11,1.55),(x+w*.32+.1,y-.11,1.55),.022,metal,12)
                for side in (-1,1):
                    box('Door jamb',x+side*(w/2+.05),y-.06,h/2+.5,.09,.16,h+.12,wood)
            elif kind in ('stairs','gate'):
                for obj in list(bpy.context.scene.objects):
                    if obj.get('logical_object')==prefix and obj.type=='MESH':
                        bevel=obj.modifiers.get('Edge highlights') or obj.modifiers.new('Worn edges','BEVEL')
                        bevel.width=min(.015,bevel.width); bevel.segments=3
            elif kind=='water':
                for side in (-1,1):
                    foliage('Bank reeds',x+side*w*.4,y,-.02,.3,d,.5)
            # Polish only this logical object's materials; neighbouring objects remain untouched.
            for material in bpy.data.materials:
                if material.name.startswith(prefix+'/') and material.use_nodes:
                    shader=material.node_tree.nodes.get('Principled BSDF')
                    if material.get('village_surface_version') != 2:
                        _village_material(material.name,tuple(material.diffuse_color[:3]),
                            shader.inputs['Roughness'].default_value,shader.inputs['Metallic'].default_value)
                        shader=material.node_tree.nodes.get('Principled BSDF')
                    if 'Water' not in material.name and 'water' not in material.name and 'glass' not in material.name:
                        shader.inputs['Roughness'].default_value=job['polish']['roughness']
                        varied=material.node_tree.nodes.get('Surface roughness')
                        if varied:
                            varied.inputs[2].default_value=max(0,job['polish']['roughness']-varied.inputs[1].default_value/2)
                    for node in material.node_tree.nodes:
                        if node.type=='BUMP':
                            node.inputs['Strength'].default_value=job['polish']['weathering']*.35
            for obj in list(bpy.context.scene.objects):
                if obj.get('logical_object')==prefix:
                    obj['polished']=True
    elif phase=='lighting':
        build_stage('lighting',config)
        bpy.context.scene.camera.data.lens=32
    elif phase!='render':
        raise ValueError('Unknown connected village phase')
    bpy.context.view_layer.update()
    owned=[obj for obj in bpy.context.scene.objects if obj.get('logical_object')==prefix]
    return dict(phase=phase, component=component, district=area['id'] if area else None,
        logical_object=prefix, created=len(created), components=len(owned),
        bounds=[list(min((obj.matrix_world @ Vector(corner))[axis] for obj in owned for corner in obj.bound_box) for axis in range(3)),
                list(max((obj.matrix_world @ Vector(corner))[axis] for obj in owned for corner in obj.bound_box) for axis in range(3))] if owned else None,
        road_ports=job.get('borders',{}), polished=phase=='polish',
        objects=len(bpy.context.scene.objects), vertices=sum(len(obj.data.vertices) for obj in owned if obj.type=='MESH'))
