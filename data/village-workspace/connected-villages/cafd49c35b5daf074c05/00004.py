"""Trusted procedural village construction, executed inside Blender only.

Website plans supply bounded data, never executable Blender Python.
"""
from __future__ import annotations

import math
import random


def _village_material(name, color, roughness=.8, metallic=0):
    """Use metre-scaled surface detail, independent of a mesh's dimensions.

    This helper is also embedded with the trusted district compiler by the adapter.
    Relief is shader-only: it cannot change a validated object's footprint.
    """
    import bpy

    existing = bpy.data.materials.get(name)
    if existing and existing.get('village_surface_version') == 2:
        return existing
    # Upgrade generated materials loaded from earlier checkpoints as they are used.
    mat = existing or bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    shader = nodes.new('ShaderNodeBsdfPrincipled')
    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    label = name.lower()
    liquid = 'water' in label
    glass = 'glass' in label
    timber = any(word in label for word in ('timber', 'bark', 'wood'))
    foliage = 'foliage' in label

    coordinates = nodes.new('ShaderNodeNewGeometry')
    coordinates.name = 'World metre coordinates'
    vector = coordinates.outputs['Position']
    if timber or liquid:
        mapping = nodes.new('ShaderNodeVectorMath')
        mapping.operation = 'MULTIPLY'
        mapping.inputs[1].default_value = (6, 6, .35) if timber else (.45, 2, 1)
        links.new(vector, mapping.inputs[0])
        vector = mapping.outputs['Vector']
    broad = nodes.new('ShaderNodeTexNoise')
    broad.name = 'Surface color variation'
    broad.inputs['Scale'].default_value = 1.8
    broad.inputs['Detail'].default_value = 3
    links.new(vector, broad.inputs['Vector'])
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = .15
    ramp.color_ramp.elements[0].color = (*(v * (.95 if liquid or glass else .72) for v in color), 1)
    ramp.color_ramp.elements[1].position = .85
    ramp.color_ramp.elements[1].color = (*(min(1, v * 1.05) for v in color), 1)
    links.new(broad.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], shader.inputs['Base Color'])

    fine = nodes.new('ShaderNodeTexNoise')
    fine.name = 'Surface grain in metres'
    fine.inputs['Scale'].default_value = 5 if liquid else 65 if not timber else 12
    fine.inputs['Detail'].default_value = 2
    links.new(vector, fine.inputs['Vector'])
    bump = nodes.new('ShaderNodeBump')
    bump.name = 'Surface relief'
    bump.inputs['Strength'].default_value = .10 if liquid else .18
    bump.inputs['Distance'].default_value = .008 if liquid else .012 if timber else .006
    links.new(fine.outputs['Fac'], bump.inputs['Height'])
    if not glass:
        links.new(bump.outputs['Normal'], shader.inputs['Normal'])
        varied_roughness = nodes.new('ShaderNodeMath')
        varied_roughness.name = 'Surface roughness'
        varied_roughness.operation = 'MULTIPLY_ADD'
        varied_roughness.use_clamp = True
        spread = .035 if liquid or metallic else .12
        varied_roughness.inputs[1].default_value = spread
        varied_roughness.inputs[2].default_value = max(0, roughness - spread / 2)
        links.new(broad.outputs['Fac'], varied_roughness.inputs[0])
        links.new(varied_roughness.outputs[0], shader.inputs['Roughness'])
    if liquid or glass:
        shader.inputs['IOR'].default_value = 1.333 if liquid else 1.45
        shader.inputs['Transmission Weight'].default_value = .65 if liquid else .3
    if foliage:
        shader.inputs['Subsurface Weight'].default_value = .06
        shader.inputs['Subsurface Radius'].default_value = (.03, .06, .015)
    mat['village_surface_version'] = 2
    return mat


def build_stage(stage, config):
    import bpy
    from mathutils import Vector

    rng = random.Random(config['seed'])
    extent = config['extent']
    count = config['buildings']

    def material(name, color, roughness=.8):
        return _village_material(name, color, roughness)

    def box(name, location, scale, mat, bevel=0):
        # Direct datablocks avoid a full scene/dependency update for every detail.
        sx, sy, sz = scale
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([(x*sx, y*sy, z*sz) for x,y,z in
            ((-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1),
             (-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1))], [],
            [(0,3,2,1), (4,5,6,7), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)])
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.location = location
        obj.data.materials.append(mat)
        if bevel:
            mod = obj.modifiers.new('Edge highlights', 'BEVEL')
            mod.width = bevel
            mod.segments = 2
        return obj

    def layout():
        columns = math.ceil(math.sqrt(count))
        spacing = extent * 1.6 / columns
        for index in range(count):
            x = (index % columns - (columns - 1) / 2) * spacing
            y = (index // columns - (columns - 1) / 2) * spacing
            yield index, x, y, spacing

    if stage == 'terrain':
        bpy.ops.wm.read_factory_settings(use_empty=True)
        soil = material('Weathered earth', (.19, .23, .10))
        # Flat settlement pad with undulating surroundings; foundations stay grounded.
        resolution = 80
        vertices, faces = [], []
        for row in range(resolution + 1):
            for col in range(resolution + 1):
                x = (col / resolution * 2 - 1) * extent * 1.6
                y = (row / resolution * 2 - 1) * extent * 1.6
                edge = max(0, max(abs(x), abs(y)) - extent * .85)
                z = math.sin(x * .025) * math.cos(y * .03) * min(edge * .12, 8)
                vertices.append((x, y, z - .08))
        for row in range(resolution):
            for col in range(resolution):
                a = row * (resolution + 1) + col
                faces.append((a, a + 1, a + resolution + 2, a + resolution + 1))
        mesh = bpy.data.meshes.new('Landscape')
        mesh.from_pydata(vertices, [], faces)
        obj = bpy.data.objects.new('Landscape', mesh)
        bpy.context.collection.objects.link(obj)
        mesh.materials.append(soil)
        for polygon in mesh.polygons:
            polygon.use_smooth = True
    elif stage == 'roads':
        road = material('Gravel roads', (.24, .21, .17))
        columns = math.ceil(math.sqrt(count))
        spacing = extent * 1.6 / columns
        for index in range(columns + 1):
            offset = (index - columns / 2) * spacing
            box('Village lane', (offset, 0, .015), (2.4, extent * .85, .04), road)
            box('Cross lane', (0, offset, .02), (extent * .85, 2.4, .04), road)
    elif stage == 'buildings':
        walls = [material('Plaster ' + str(i), color) for i, color in enumerate(
            ((.62, .52, .39), (.47, .40, .32), (.71, .65, .51), (.43, .48, .43)))]
        roof = material('Terracotta', (.25, .075, .035))
        stone = material('Foundation stone', (.27, .28, .26))
        for index, x, y, spacing in layout():
            width = min(4.5, spacing * .25) * rng.uniform(.8, 1)
            depth = width * rng.uniform(.8, 1.15)
            height = rng.uniform(3.2, 5.5)
            box('Foundation_%03d' % index, (x, y, .22), (width + .18, depth + .18, .22), stone, .08)
            box('House_%03d' % index, (x, y, height / 2 + .4), (width, depth, height / 2), walls[index % 4], .07)
            vertices = [(-width-.3, -depth-.3, 0), (width+.3, -depth-.3, 0),
                        (0, -depth-.3, width*.65), (-width-.3, depth+.3, 0),
                        (width+.3, depth+.3, 0), (0, depth+.3, width*.65)]
            mesh = bpy.data.meshes.new('Gabled roof')
            mesh.from_pydata(vertices, [], [(0, 1, 2), (3, 5, 4), (0, 2, 5, 3), (2, 1, 4, 5), (0, 3, 4, 1)])
            obj = bpy.data.objects.new('Roof_%03d' % index, mesh)
            bpy.context.collection.objects.link(obj)
            obj.location = (x, y, height + .4)
            mesh.materials.append(roof)
    elif stage == 'details':
        wood = material('Aged timber', (.12, .065, .025))
        glass = material('Blue window glass', (.075, .14, .18), .15)
        stone = material('Chimney stone', (.25, .22, .19))
        tiles = [material('Roof tile '+str(i), (.15+i*.018, .035+i*.007, .014+i*.004)) for i in range(5)]
        for index, x, y, spacing in layout():
            house = bpy.data.objects['House_%03d' % index]
            w, d, h = (v / 2 for v in house.dimensions)
            box('Door', (x, y-d-.04, 1.35), (.55, .08, .95), wood, .035)
            for side in (-1, 1):
                px = x + side * w * .62
                box('Window frame', (px, y-d-.06, 2.3), (.65, .10, .72), wood, .025)
                box('Window pane', (px, y-d-.17, 2.3), (.53, .02, .60), glass)
                box('Window mullion', (px, y-d-.20, 2.3), (.035, .025, .60), wood)
            box('Chimney', (x+w*.5, y, h*2+1.1), (.32, .35, 1), stone, .03)
            for side in (-1, 1):
                box('Porch post', (x+side*.9, y-d-1, 1.5), (.075, .075, 1.5), wood)
            box('Porch canopy', (x, y-d-.7, 3), (1.2, .9, .09), wood, .025)
            # Individual overlapping tiles in one mesh per roof avoid thousands of objects.
            vertices, faces = [], []
            half_width = w + .3
            rows = max(4, math.ceil(half_width / .42))
            columns = max(4, math.ceil((d*2+.6) / .38))
            for side in (-1, 1):
                for row in range(rows):
                    a = row / rows * half_width
                    b = min(half_width, (row+1.08) / rows * half_width)
                    for col in range(columns):
                        ya = -d-.3 + col/columns*(2*d+.6)
                        yb = ya + (2*d+.6)/columns*.97
                        base = len(vertices)
                        for xx, yy in ((a,ya), (b,ya), (b,yb), (a,yb)):
                            z = h*2+.4+w*.65*(1-xx/half_width)+.045+(rows-row)*.004
                            vertices.append((x+side*xx, y+yy, z))
                        faces.append(tuple(base+j for j in range(4)))
            mesh = bpy.data.meshes.new('Overlapping roof tiles')
            mesh.from_pydata(vertices, [], faces)
            tiled = bpy.data.objects.new('Tiled roof_%03d' % index, mesh)
            bpy.context.collection.objects.link(tiled)
            for mat in tiles:
                mesh.materials.append(mat)
            for polygon in mesh.polygons:
                polygon.material_index = rng.randrange(len(tiles))
            # Timber corner framing, raised sills and small fenced back gardens.
            for side in (-1, 1):
                box('Corner timber', (x+side*(w-.045), y-d-.03, h+.4), (.055,.055,h), wood)
                box('Window sill', (x+side*w*.62, y-d-.22, 1.6), (.74,.20,.065), stone, .025)
            fence_y = y+d+1.3
            for post in range(7):
                box('Garden fence post', (x-w+post*w/3, fence_y, .6), (.045,.045,.6), wood)
            for z in (.45, .95):
                box('Garden fence rail', (x, fence_y, z), (w,.04,.045), wood)
            box('Door step', (x, y-d-.5, .13), (.8,.45,.13), stone, .03)
    elif stage == 'vegetation':
        bark = material('Tree bark', (.13, .075, .035))
        leaves = [material('Foliage '+str(i), c) for i, c in enumerate(
            ((.06, .16, .025), (.12, .23, .035), (.18, .25, .065)))]
        # Linked crown meshes reduce memory cost while retaining variation.
        crown_mesh = None
        for index in range(config['trees']):
            angle = rng.random() * math.tau
            radius = rng.uniform(extent*.9, extent*1.3)
            x, y = math.cos(angle)*radius, math.sin(angle)*radius
            edge = max(0, max(abs(x), abs(y))-extent*.85)
            ground = math.sin(x*.025)*math.cos(y*.03)*min(edge*.12, 8)-.08
            height = rng.uniform(4, 8)
            bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=.19, depth=height, location=(x,y,ground+height/2))
            bpy.context.object.data.materials.append(bark)
            for layer in range(9):
                if crown_mesh is None:
                    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2)
                    obj = bpy.context.object
                    crown_mesh = obj.data
                    for vertex in crown_mesh.vertices:
                        vertex.co *= rng.uniform(.8, 1.2)
                    crown_mesh.materials.append(leaves[0])
                else:
                    obj = bpy.data.objects.new('Tree crown', crown_mesh)
                    bpy.context.collection.objects.link(obj)
                obj.location = (x+rng.uniform(-1.7,1.7), y+rng.uniform(-1.7,1.7), ground+height*.7+rng.uniform(-.5,2))
                obj.scale = (rng.uniform(.8,1.5), rng.uniform(.8,1.5), rng.uniform(1,1.8))
                obj.material_slots[0].link = 'OBJECT'
                obj.material_slots[0].material = leaves[index % 3]
    elif stage == 'lighting':
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = config['samples']
        scene.cycles.seed = config['seed']
        scene.cycles.use_animated_seed = False
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = .01
        scene.cycles.adaptive_min_samples = min(32, config['samples'])
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
        scene.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        scene.cycles.denoising_prefilter = 'ACCURATE'
        scene.cycles.max_bounces = 12
        scene.cycles.diffuse_bounces = 6
        scene.cycles.glossy_bounces = 6
        scene.cycles.transmission_bounces = 8
        scene.cycles.transparent_max_bounces = 8
        scene.cycles.sample_clamp_indirect = 10
        scene.render.resolution_x = config['resolution']
        scene.render.resolution_y = round(config['resolution'] * 9 / 16)
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.world = bpy.data.worlds.get('Physical sky') or bpy.data.worlds.new('Physical sky')
        scene.world.use_nodes = True
        sky = scene.world.node_tree.nodes.get('Village sky') or scene.world.node_tree.nodes.new('ShaderNodeTexSky')
        sky.name = 'Village sky'
        sky.sky_type = 'NISHITA'
        sky.sun_elevation = math.radians(config['sun_elevation'])
        sky.sun_rotation = math.radians(135)
        # A single analytic sun gives controllable shadows without a second sky sun.
        sky.sun_disc = False
        scene.world.node_tree.links.new(sky.outputs['Color'], scene.world.node_tree.nodes['Background'].inputs['Color'])
        scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .3
        sun = bpy.data.objects.get('Village sun')
        if sun is None or sun.type != 'LIGHT':
            sun = bpy.data.objects.new('Village sun', bpy.data.lights.new('Village sun', 'SUN'))
            scene.collection.objects.link(sun)
        direction = Vector((math.cos(sky.sun_elevation) * math.cos(sky.sun_rotation),
                            math.cos(sky.sun_elevation) * math.sin(sky.sun_rotation),
                            math.sin(sky.sun_elevation)))
        sun.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
        sun.data.energy = 2
        sun.data.angle = math.radians(1.5)
        sun.data.color = (1, .91, .78)
        camera = bpy.data.objects.get('Village camera')
        if camera is None or camera.type != 'CAMERA':
            camera = bpy.data.objects.new('Village camera', bpy.data.cameras.new('Village camera'))
            scene.collection.objects.link(camera)
        camera.location = (extent*1.3, -extent*1.6, extent*.95)
        camera.rotation_euler = (Vector((0,0,2))-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.clip_end = extent*20
        camera.data.lens = 40
        scene.camera = camera
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.exposure = -.7
        scene.view_settings.gamma = 1

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

import bpy,json
_report=district_step({'phase': 'infrastructure', 'area': {'id': 'area-0-0', 'row': 0, 'col': 0, 'bounds': [-120.0, -120.0, -60.0, -60.0], 'edges': {'west': 'v-0-0', 'east': 'v-0-1', 'south': 'h-0-0', 'north': 'h-1-0'}, 'center': [-90.0, -90.0], 'channel_y': -110.4, 'channel_width': 1.2, 'water_level': -0.16, 'neighbours': ['area-0-1', 'area-1-0']}, 'borders': {'west': {'id': 'v-0-0', 'road_port': [-120.0, -90.0, 0], 'road_width': 4, 'elevation': 0, 'verge_width': 1, 'palette': 'weathered rural stone/plaster/timber'}, 'east': {'id': 'v-0-1', 'road_port': [-60.0, -90.0, 0], 'road_width': 4, 'elevation': 0, 'verge_width': 1, 'palette': 'weathered rural stone/plaster/timber'}, 'south': {'id': 'h-0-0', 'road_port': [-90.0, -120.0, 0], 'road_width': 4, 'elevation': 0, 'verge_width': 1, 'palette': 'weathered rural stone/plaster/timber'}, 'north': {'id': 'h-1-0', 'road_port': [-90.0, -60.0, 0], 'road_width': 4, 'elevation': 0, 'verge_width': 1, 'palette': 'weathered rural stone/plaster/timber'}}, 'area_plan': {'objects': [{'id': 'home1', 'kind': 'house', 'x': -106.25, 'y': -73.75, 'width': 6.0, 'depth': 6.0, 'height': 4.0, 'parent': None}, {'id': 'home1_door', 'kind': 'door', 'x': -106.25, 'y': -76.75, 'width': 1.2, 'depth': 0.2, 'height': 2.1, 'parent': 'home1'}, {'id': 'home1_stairs', 'kind': 'stairs', 'x': -106.25, 'y': -76.75, 'width': 1.8, 'depth': 1.2, 'height': 0.45, 'parent': 'home1'}, {'id': 'home2', 'kind': 'house', 'x': -73.75, 'y': -73.75, 'width': 6.0, 'depth': 6.0, 'height': 4.0, 'parent': None}, {'id': 'home2_door', 'kind': 'door', 'x': -73.75, 'y': -76.75, 'width': 1.2, 'depth': 0.2, 'height': 2.1, 'parent': 'home2'}, {'id': 'home2_stairs', 'kind': 'stairs', 'x': -73.75, 'y': -76.75, 'width': 1.8, 'depth': 1.2, 'height': 0.45, 'parent': 'home2'}], 'rationale': 'Sparse runtime layout with two homes and connected entrances; additional scenery omitted.'}, 'component': 'drainage', 'grid': 4},{'seed': 42, 'extent': 120, 'buildings': 100, 'trees': 240, 'samples': 256, 'resolution': 2560, 'sun_elevation': 25})
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\connected-villages\\cafd49c35b5daf074c05\\00004.blend')
with open('C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-workspace\\connected-villages\\cafd49c35b5daf074c05\\00004.json',"w") as report:
    json.dump(_report,report)
