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
