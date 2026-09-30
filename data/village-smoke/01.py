"""Trusted procedural village construction, executed inside Blender only.

Website plans supply bounded data, never executable Blender Python.
"""
from __future__ import annotations

import math
import random


def build_stage(stage, config):
    import bpy
    from mathutils import Vector

    rng = random.Random(config['seed'])
    extent = config['extent']
    count = config['buildings']

    def material(name, color, roughness=.8):
        existing = bpy.data.materials.get(name)
        if existing:
            return existing
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = (*color, 1)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        shader = nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*color, 1)
        shader.inputs['Roughness'].default_value = roughness
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 7
        noise.inputs['Detail'].default_value = 4
        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position = .2
        ramp.color_ramp.elements[0].color = (*(v * .45 for v in color), 1)
        ramp.color_ramp.elements[1].position = .8
        ramp.color_ramp.elements[1].color = (*color, 1)
        mat.node_tree.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
        mat.node_tree.links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .22
        bump.inputs['Distance'].default_value = .08
        mat.node_tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
        mat.node_tree.links.new(bump.outputs['Normal'], shader.inputs['Normal'])
        return mat

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
        scene.cycles.use_denoising = True
        scene.render.resolution_x = config['resolution']
        scene.render.resolution_y = round(config['resolution'] * 9 / 16)
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.world = bpy.data.worlds.new('Physical sky')
        scene.world.use_nodes = True
        sky = scene.world.node_tree.nodes.new('ShaderNodeTexSky')
        sky.sky_type = 'NISHITA'
        sky.sun_elevation = math.radians(config['sun_elevation'])
        scene.world.node_tree.links.new(sky.outputs['Color'], scene.world.node_tree.nodes['Background'].inputs['Color'])
        scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .3
        bpy.ops.object.light_add(type='SUN', rotation=(.4, -.5, -.6))
        bpy.context.object.data.energy = 2
        bpy.context.object.data.angle = .08
        bpy.ops.object.camera_add(location=(extent*1.3, -extent*1.6, extent*.95))
        camera = bpy.context.object
        camera.rotation_euler = (Vector((0,0,2))-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.clip_end = extent*20
        camera.data.lens = 40
        scene.camera = camera
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.exposure = -.7

import bpy, json
build_stage('roads', {'seed': 42, 'extent': 80, 'buildings': 40, 'trees': 40, 'samples': 16, 'resolution': 640, 'sun_elevation': 25})
bpy.ops.wm.save_as_mainfile(filepath='C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-smoke\\01.blend')
with open('C:\\Users\\user\\OneDrive\\Desktop\\Brainless_agent-main\\Brainless_agent\\data\\village-smoke\\01.json', "w") as report:
    json.dump({"stage": 'roads', "objects": len(bpy.context.scene.objects), "meshes": len(bpy.data.meshes), "engine": bpy.context.scene.render.engine}, report)
