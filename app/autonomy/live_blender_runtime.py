"""Trusted Blender-side timer. Run only by LiveBlenderSession, never by a model."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

import bpy
from mathutils import Vector,Euler

ROOT=Path(sys.argv[sys.argv.index('--')+1]).resolve()
WORKSPACE=ROOT.parent
last_id=None
current_project=None
animation=None


def write(path, value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value),encoding='utf-8')
    temporary.replace(path)


def inside(value):
    path=Path(value).resolve()
    if WORKSPACE not in path.parents:
        raise ValueError('Live job path is outside its workspace')
    return path


def finish(command,error=None):
    global current_project,animation
    current_project=command['project'] if error is None else None
    animation=None
    write(ROOT/f'{command["id"]}.json',dict(status='failed' if error else 'completed',error=error))


def redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def visible_geometry(obj):
    """Do not reveal hidden objects or move the view to a light/camera."""
    return (obj.type in {'MESH','CURVE','SURFACE','META','FONT','VOLUME','POINTCLOUD','GREASEPENCIL'}
            and not obj.hide_viewport and obj.visible_get())


def world_bounds(objects):
    """Frame evaluated geometry, including modifiers, parents and local offsets."""
    depsgraph=bpy.context.evaluated_depsgraph_get()
    points=[]
    for obj in objects:
        if not visible_geometry(obj):
            continue
        evaluated=obj.evaluated_get(depsgraph)
        corners=[evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
        points.extend(point for point in corners if all(math.isfinite(v) for v in point))
    if not points:
        return None
    low=Vector(tuple(min(point[i] for point in points) for i in range(3)))
    high=Vector(tuple(max(point[i] for point in points) for i in range(3)))
    return (low+high)/2,max((high-low).length/2,.05)


def follow_view(objects,*,final=False):
    """Move viewport navigation only; never move or keyframe the scene camera."""
    bounds=world_bounds(objects)
    if bounds is None:
        return
    center,radius=bounds
    blend=1.0 if final else .32
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type!='VIEW_3D':
                continue
            region=next((r for r in area.regions if r.type=='WINDOW'),None)
            if region is None:
                continue
            # Direct navigation properties also work without an operator context
            # and preserve the user's orbit orientation. Include quad-view panes.
            try:
                space=area.spaces.active
                views=list(space.region_quadviews) or [space.region_3d]
                aspect=max(region.width,1)/max(region.height,1)
                half_angle=math.atan(16/max(space.lens,1)/max(aspect,1/aspect))
                distance=max(.2,radius/math.sin(half_angle)*1.15)
                for view in views:
                    if view is None:
                        continue
                    if view.view_perspective=='CAMERA':
                        # Leaving camera view avoids changing a locked render camera.
                        view.view_perspective='PERSP'
                    view.view_location=view.view_location.lerp(center,blend)
                    view.view_distance+=(distance-view.view_distance)*blend
                space.clip_end=max(space.clip_end,distance+radius*2)
            except (AttributeError,ReferenceError,RuntimeError):
                # Closing/changing a viewport during a job must not fail the job.
                continue


def tick():
    global last_id,current_project,animation
    write(ROOT/'heartbeat.json',dict(time=time.time(),pid=os.getpid()))
    if animation:
        command,objects,targets,focus,frame=animation
        try:
            t=min(1,(frame+1)/24)
            t=t*t*(3-2*t)
            for index,(obj,target) in enumerate(zip(objects,targets)):
                if command['animate'] and len(objects)==1:
                    start=target[3]
                    obj.location=start[0].lerp(target[0],t)
                    obj.rotation_euler=tuple(start[1][i]+(target[1][i]-start[1][i])*t for i in range(3))
                    obj.scale=start[2].lerp(target[2],t)
                else:
                    obj.hide_viewport=target[4] or index>int(t*len(objects))
            bpy.context.view_layer.update()
            if command.get('focus_view',True):
                follow_view(focus)
            if frame>=23:
                for obj,target in zip(objects,targets):
                    obj.location,obj.rotation_euler,obj.scale=target[:3]
                    obj.hide_viewport=target[4]
                bpy.context.view_layer.update()
                if command.get('focus_view',True):
                    follow_view(focus,final=True)
                finish(command)
            else:
                animation=(command,objects,targets,focus,frame+1)
            redraw()
        except Exception:
            finish(command,traceback.format_exc()[-2000:])
        return .035
    try:
        command=json.loads((ROOT/'command.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):
        return .2
    if command['id']==last_id:
        return .2
    last_id=command['id']
    try:
        script=inside(command['script'])
        inside(command['project'])
        code=script.read_bytes()
        if hashlib.sha256(code).hexdigest()!=command['sha256']:
            raise ValueError('Trusted compiled job changed before execution')
        if command['source'] and current_project!=command['source']:
            bpy.ops.wm.open_mainfile(filepath=str(inside(command['source'])))
            current_project=command['source']
            last_id=None
            # File loading replaces Blender's context. Execute on the next UI
            # tick so operators see the restored window/view layer.
            return .2
        before={obj.name:(obj.location.copy(),obj.rotation_euler.copy(),obj.scale.copy())
                for obj in bpy.context.scene.objects}
        os.chdir(script.parent)
        exec(compile(code,str(script),'exec'),{'__name__':'__main__'})
        objects=[obj for obj in bpy.context.scene.objects if obj.name not in before and visible_geometry(obj)]
        explicit_target=(bpy.context.scene.objects.get(command['focus_object'])
                         if command.get('focus_object') else None)
        if command['animate']:
            target=explicit_target if command.get('focus_object') else bpy.context.active_object
            objects=[target] if target is not None and visible_geometry(target) else []
        focus=list(objects)
        if command.get('focus_object'):
            focus=[explicit_target] if explicit_target is not None and visible_geometry(explicit_target) else []
            # A material/bevel/shading edit needs a smooth view transition but
            # must not hide or replay transforms of the existing target.
        targets=[]
        for obj in objects:
            start=before.get(obj.name,(Vector((0,0,0)),Euler((0,0,0)),Vector((1,1,1))))
            targets.append((obj.location.copy(),obj.rotation_euler.copy(),obj.scale.copy(),start,obj.hide_viewport))
            if command['animate'] and len(objects)==1:
                obj.location,obj.rotation_euler,obj.scale=start
            else:
                obj.hide_viewport=True
        if objects or (focus and command.get('focus_view',True)):
            animation=(command,objects,targets,focus,0)
        else:
            finish(command)
    except Exception:
        finish(command,traceback.format_exc()[-2000:])
    return .035


bpy.app.timers.register(tick,first_interval=.2,persistent=True)
