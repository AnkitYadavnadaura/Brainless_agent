"""Trusted Blender automation adapter with fixed, structured operations."""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.agents.tools import RiskLevel, ToolSpec
from app.autonomy.capability_lifecycle import CapabilityCandidate


OPERATIONS = frozenset({
    "create_scene", "add_cube", "add_sphere", "add_cylinder", "add_cone",
    "add_torus", "add_plane", "add_dome", "add_arch", "add_camera", "add_light", "transform",
    "bevel", "smooth_shade", "add_material",
    "create_car_body", "create_car_wheels", "create_car_windows",
    "create_car_lights", "apply_car_materials", "setup_car_camera",
    "setup_car_lighting", "create_car", "render", "export",
    "execute_plan",
})
MAX_PLAN_STEPS = 180


def find_blender() -> str | None:
    configured = os.environ.get("BLENDER_EXECUTABLE")
    if configured and Path(configured).is_file():
        return configured
    on_path = shutil.which("blender")
    if on_path:
        return on_path
    if os.name == "nt":
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        candidates = sorted(
            (program_files / "Blender Foundation").glob("Blender*/blender.exe"),
            reverse=True,
        )
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    return None


def build_blender_tool(candidate: CapabilityCandidate, workspace: Path):
    blender = find_blender()
    if blender is None:
        raise RuntimeError("Blender is not installed or BLENDER_EXECUTABLE is unavailable")
    root = workspace.resolve()
    live_session = None

    async def operate(arguments: dict[str, Any]) -> str:
        nonlocal live_session
        if "ordered_steps" in arguments and "steps" not in arguments:
            arguments = dict(arguments)
            arguments["steps"] = arguments.pop("ordered_steps")
        else:
            arguments = dict(arguments)
        arguments.setdefault("operation", "execute_plan")
        arguments.setdefault("project", "scene.blend")
        arguments.setdefault("visible", True)
        arguments.setdefault("live", True)
        operation = str(arguments["operation"])
        if arguments.get('live') and operation in ('district_step','model_step') and live_session is None:
            from app.autonomy.live_blender import LiveBlenderSession
            live_session=LiveBlenderSession(blender,root)
        if operation == 'district_step':
            return await _operate_district(blender, root, arguments, live_session=live_session if arguments.get('live') else None)
        if operation == 'model_step':
            return await _operate_model_step(blender,root,arguments,live_session=live_session if arguments.get('live') else None)
        if operation == 'village_stage':
            return await _operate_village(blender, root, arguments)
        if operation not in OPERATIONS:
            raise ValueError(f"Unsupported Blender operation: {operation}")
        project = _safe_path(root, arguments.get("project", "scene.blend"))
        project.parent.mkdir(parents=True, exist_ok=True)
        script = _script(operation, project, arguments)
        script_path = root / "operation.py"
        script_path.write_text(script, encoding="utf-8")
        visible = bool(arguments.get("visible", False))
        live = bool(arguments.get("live", False))
        if operation == "execute_plan" and visible and live:
            marker = root / "blender-complete.json"
            marker.unlink(missing_ok=True)
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            process = subprocess.Popen(
                [blender, "--python", str(script_path)],
                cwd=str(root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            non_render_outputs = tuple(
                output for output in _plan_outputs(root, arguments)
                if output.suffix.lower() not in {".png", ".jpg", ".jpeg", ".exr"}
            )
            await _wait_for_live_completion(
                marker, project, non_render_outputs,
                process=process,
            )
            render_outputs = tuple(
                output for output in _plan_outputs(root, arguments)
                if output.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr"}
            )
            if render_outputs:
                render_log = root / "blender-render.log"
                render_result = await asyncio.to_thread(
                    subprocess.run,
                    [
                        blender, "--background", str(project),
                        "--render-frame", "1",
                        "--log-file", str(render_log),
                    ],
                    cwd=str(root),
                    capture_output=True,
                    check=False,
                    text=True,
                )
                if render_result.returncode != 0:
                    raise RuntimeError(
                        "Live Blender scene was created, but final render failed: "
                        f"{(render_result.stderr or render_result.stdout)[-1200:]}"
                    )
                for output in render_outputs:
                    if not output.is_file() or output.stat().st_size == 0:
                        raise RuntimeError(f"Live Blender render was not produced: {output}")
            return str(project)
        # Execute scripts headlessly first. Opening a GUI process with
        # --python can leave Blender responsive but waiting before the script
        # finishes on Windows. A verified file is then opened in a persistent
        # GUI process for the user to inspect and edit.
        command = [blender, "--background"]
        if project.exists():
            command.append(str(project))
        command.extend(["--python", str(script_path)])
        if operation == "render":
            command.extend(["--render-frame", str(int(arguments.get("frame", 1)))])
        log_path = root / "blender.log"
        command.extend(["--log-file", str(log_path)])
        # Run Blender work in a worker thread. On Windows this avoids leaving
        # Proactor pipe transports behind when the CLI event loop exits.
        result = await asyncio.to_thread(
            subprocess.run,
            command,
            cwd=str(root),
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            details = (result.stderr + result.stdout).strip()
            raise RuntimeError(f"Blender failed with exit code {result.returncode}: {details[-1200:]}")
        if not project.exists():
            raise RuntimeError("Blender did not produce the project file")
        outputs = _plan_outputs(root, arguments) if operation == "execute_plan" else ()
        if operation in {"render", "export"}:
            output = _safe_path(root, arguments.get("output", "render.png" if operation == "render" else "export.glb"))
            outputs = (output,)
        for output in outputs:
            if not output.exists() or output.stat().st_size == 0:
                raise RuntimeError(f"Blender did not produce the requested output: {output}")
        if visible:
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            gui_command = [blender, str(project)]
            subprocess.Popen(
                gui_command,
                cwd=str(root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        return str(project)

    return operate


async def _operate_district(blender: str, root: Path, arguments: dict[str, Any], *, live_session=None) -> str:
    from app.autonomy.village_workflow import validate_config
    from app.autonomy.village_districts import master_plan, validate_area, validate_polish, validate_component
    config=validate_config(arguments.get('config'))
    job=dict(arguments['job'])
    validate_component(job)
    phase=job.get('phase')
    if phase not in ('world','infrastructure','create','polish','lighting','render'):
        raise ValueError('Unknown district phase')
    if phase in ('infrastructure','create','polish'):
        master=master_plan(config,job['grid'])
        area=next((a for a in master['areas'] if a['id']==job['area']['id']),None)
        if area!=job['area'] or job['borders']!={k:master['edges'][v] for k,v in area['edges'].items()}:
            raise ValueError('Shared boundary contract mismatch')
        plan=validate_area(job['area_plan'],area)
        if phase in ('create','polish') and job['object'] not in plan['objects']:
            raise ValueError('Object is outside validated area plan')
        if phase=='polish':
            job['polish']=validate_polish(job['polish'])
    project=_safe_path(root,arguments['project'])
    project.parent.mkdir(parents=True,exist_ok=True)
    source=_safe_path(root,arguments['source']) if arguments.get('source') else None
    if phase!='world' and (source is None or not source.is_file()):
        raise ValueError('District step requires a completed source scene')
    if source==project:
        raise ValueError('Output must be a new checkpoint')
    implementation=Path(__file__).with_name('village_scene.py').read_text(encoding='utf-8')
    implementation+='\n'+Path(__file__).with_name('district_scene.py').read_text(encoding='utf-8')
    output=project.parent/'village.png'
    script=implementation+f'\nimport bpy,json\n_report=district_step({job!r},{config!r})\n'
    if phase=='render':
        script+=f'bpy.context.scene.cycles.samples={config["samples"]}\n'
        script+=f'bpy.context.scene.render.resolution_x={config["resolution"]}\n'
        script+=f'bpy.context.scene.render.resolution_y={round(config["resolution"]*9/16)}\n'
        script+='bpy.context.scene.render.resolution_percentage=100\n'
        script+=f'bpy.context.scene.render.filepath={str(output)!r}\nbpy.ops.render.render(write_still=True)\n'
    script+=f'bpy.ops.wm.save_as_mainfile(filepath={str(project)!r})\n'
    script+=f'with open({str(project.with_suffix(".json"))!r},"w") as report:\n    json.dump(_report,report)\n'
    path=project.with_suffix('.py')
    path.write_text(script,encoding='utf-8')
    if live_session is not None:
        await live_session.run(path,source,project,focus_view=phase not in ('lighting','render'))
        if not project.is_file() or not project.with_suffix('.json').is_file():
            raise RuntimeError('Live district step did not produce its checkpoint')
        return str(project)
    command=[blender,'--background']+([str(source)] if source else [])
    command+=['--python-exit-code','1','--python',str(path)]
    result=await asyncio.to_thread(subprocess.run,command,capture_output=True,text=True,
        cwd=str(project.parent),timeout=7200,check=False)
    project.with_suffix('.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode or not project.is_file() or not project.with_suffix('.json').is_file():
        raise RuntimeError('District step failed: '+(result.stderr+result.stdout)[-1400:])
    if arguments.get('visible'):
        subprocess.Popen([blender,str(project)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return str(project)


async def _operate_model_step(blender,root,arguments,*,live_session=None):
    from app.autonomy.model_workflow import validate_model_step
    import json
    step=validate_model_step(arguments['step'])
    operation,args=step['operation'],dict(step['args'])
    project=_safe_path(root,arguments['project'])
    source=_safe_path(root,arguments['source']) if arguments.get('source') else None
    if source==project or (operation!='create_scene' and (source is None or not source.is_file())):
        raise ValueError('Model step requires a separate verified source checkpoint')
    project.parent.mkdir(parents=True,exist_ok=True)
    prefix='import bpy, json\n'
    target=args.pop('target',None)
    if target:
        prefix+=f"obj=bpy.data.objects.get({target!r})\nif obj is None: raise ValueError('Target object is missing')\n"
        prefix+="bpy.ops.object.select_all(action='DESELECT')\nobj.select_set(True)\nbpy.context.view_layer.objects.active=obj\n"
    if operation in ('add_cube','add_sphere','add_cylinder','add_cone','add_torus','add_plane','add_dome','add_arch','add_camera','add_light'):
        prefix+=f"if bpy.data.objects.get({args['name']!r}): raise ValueError('Object name already exists')\n"
    if operation=='render':
        prefix+="bpy.context.scene.render.engine='CYCLES'\nbpy.context.scene.cycles.use_denoising=True\n"
        prefix+=f"bpy.context.scene.cycles.samples={args.get('samples',256)}\n"
        prefix+=f"bpy.context.scene.render.resolution_x={args.get('resolution',2560)}\n"
        prefix+=f"bpy.context.scene.render.resolution_y={round(args.get('resolution',2560)*9/16)}\n"
        prefix+="bpy.context.scene.render.resolution_percentage=100\n"
        args['output']=project.stem+'.png'
    if operation=='export':
        args['output']=project.stem+'.glb'
    script=prefix+_script(operation,project,args).removeprefix('import bpy\n')
    script+="\n_report={'operation':"+repr(operation)+",'objects':[{'name':o.name,'type':o.type,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale)} for o in bpy.context.scene.objects]}\n"
    script+=f"with open({str(project.with_suffix('.json'))!r},'w',encoding='utf-8') as stream: json.dump(_report,stream)\n"
    path=project.with_suffix('.py')
    path.write_text(script,encoding='utf-8')
    if live_session is not None:
        await live_session.run(path,source,project,
            animate=operation in ('add_cube','add_sphere','add_cylinder','add_cone','add_torus','add_plane','add_dome','add_arch','transform'),
            focus_object=target or (args.get('name') if operation.startswith('add_') and operation not in ('add_camera','add_light') else None),
            focus_view=operation not in ('render','export','add_light','add_camera','create_scene'))
    else:
        command=[blender,'--background']+([str(source)] if source else [])+['--python-exit-code','1','--python',str(path)]
        result=await asyncio.to_thread(subprocess.run,command,capture_output=True,text=True,timeout=7200,check=False)
        project.with_suffix('.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:
            raise RuntimeError('Model step failed: '+(result.stdout+result.stderr)[-1600:])
    if not project.is_file() or not project.with_suffix('.json').is_file():
        raise RuntimeError('Model step did not produce checkpoint evidence')
    return str(project)


async def _operate_village(blender: str, root: Path, arguments: dict[str, Any]) -> str:
    from app.autonomy.village_workflow import STAGES, validate_config
    config = validate_config(arguments.get('config'))
    stage = arguments.get('stage')
    if stage not in STAGES:
        raise ValueError('Unknown village stage')
    project = _safe_path(root, arguments['project'])
    project.parent.mkdir(parents=True, exist_ok=True)
    source = _safe_path(root, arguments['source']) if arguments.get('source') else None
    if stage != 'terrain' and (source is None or not source.is_file()):
        raise ValueError('A completed source scene is required')
    if source == project:
        raise ValueError('Village stages require a new output project')
    # Only trusted repository source is embedded; configuration is literal data.
    implementation = Path(__file__).with_name('village_scene.py').read_text(encoding='utf-8')
    output = project.parent / 'village.png'
    script = implementation + '\nimport bpy, json\n'
    if stage != 'render':
        script += f'build_stage({stage!r}, {config!r})\n'
    else:
        script += f'bpy.context.scene.render.filepath = {str(output)!r}\nbpy.ops.render.render(write_still=True)\n'
    script += f'bpy.ops.wm.save_as_mainfile(filepath={str(project)!r})\n'
    script += (f'with open({str(project.with_suffix(".json"))!r}, "w") as report:\n'
               f'    json.dump({{"stage": {stage!r}, "objects": len(bpy.context.scene.objects), '
               '"meshes": len(bpy.data.meshes), "engine": bpy.context.scene.render.engine}, report)\n')
    script_path = project.with_suffix('.py')
    script_path.write_text(script, encoding='utf-8')
    command = [blender, '--background'] + ([str(source)] if source else [])
    command += ['--python-exit-code', '1', '--python', str(script_path)]
    result = await asyncio.to_thread(subprocess.run, command, capture_output=True, text=True,
                                   cwd=str(project.parent), timeout=7200, check=False)
    project.with_suffix('.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode or not project.is_file() or not project.with_suffix('.json').is_file():
        raise RuntimeError('Village stage failed: ' + (result.stderr + result.stdout)[-1200:])
    if arguments.get('visible'):
        subprocess.Popen([blender, str(project)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(project)


def health_check_blender(spec: ToolSpec, workspace: Path) -> bool:
    return spec.tool_id == "blender.scene" and find_blender() is not None and workspace.is_dir()


def blender_candidate() -> CapabilityCandidate:
    return CapabilityCandidate(
        capability_id="blender.scene", version="1.0.0", tool_id="blender.scene",
        name="Blender scene and car automation",
        description=(
            "Create or edit a Blender scene and open the resulting project in Blender. "
            "Call with operation='execute_plan', project as a simple filename, visible=true, "
            "live=true, and steps as an ordered list of {operation, args} objects. "
            "Start with create_scene; use only supported structured Blender operations."
        ),
        required_permissions=frozenset({"filesystem.read", "filesystem.write", "process.execute"}),
        risk=RiskLevel.MEDIUM,
        input_schema=("operation", "project", "visible", "live", "steps"),
        output_schema="blend path",
        source="trusted-catalog", builder_key="blender-scene", health_check_key="blender-scene",
    )


def _safe_path(root: Path, value: object) -> Path:
    path = (root / str(value)).resolve()
    if path != root and root not in path.parents:
        raise ValueError("Blender project paths must stay inside the sandbox")
    return path


def _script(operation: str, project: Path, arguments: dict[str, Any]) -> str:
    project_text = repr(str(project))
    if operation == "create_scene":
        body = "bpy.ops.wm.read_factory_settings(use_empty=True)"
    elif operation in ('add_dome','add_arch'):
        body=Path(__file__).with_name('architectural_scene.py').read_text(encoding='utf-8')
        body+=f"\nbuild_architectural_primitive({operation!r},{arguments.get('name','Architecture')!r})\n"
        body+=_object_transform_script(arguments)
    elif operation in {
        "add_cube", "add_sphere", "add_cylinder", "add_cone",
        "add_torus", "add_plane",
    }:
        body = _primitive_script(operation, arguments)
    elif operation == "add_camera":
        body = (
            "bpy.ops.object.camera_add()\n"
            + _object_transform_script(arguments)
            + "\nbpy.context.scene.camera = bpy.context.active_object"
        )
    elif operation == "add_light":
        energy = _number(arguments, "energy", 1200)
        body = (
            "bpy.ops.object.light_add(type='AREA')\n"
            + _object_transform_script(arguments)
            + f"\nbpy.context.active_object.data.energy={energy!r}"
        )
    elif operation == "transform":
        body = _transform_script(arguments)
    elif operation == "bevel":
        width=_number(arguments,'width',arguments.get('amount',.05))
        segments=arguments.get('segments',3)
        import math
        if not math.isfinite(width) or not 0<=width<=10 or type(segments) is not int or not 1<=segments<=12:
            raise ValueError('Bevel width must be 0..10 and segments 1..12')
        body = ("obj=bpy.context.active_object\n"
                "if obj is None or obj.type!='MESH': raise ValueError('Bevel requires a mesh target')\n"
                "modifier=obj.modifiers.new('Bevel','BEVEL')\n"
                f"modifier.width={width!r}\nmodifier.segments={segments!r}\nmodifier.limit_method='ANGLE'")
    elif operation == "smooth_shade":
        body = "bpy.ops.object.shade_smooth()"
    elif operation == "add_material":
        body = _material_script(arguments)
    elif operation == "create_car_body":
        body = _car_body_script()
    elif operation == "create_car_wheels":
        body = _car_wheels_script()
    elif operation == "create_car_windows":
        body = _car_windows_script()
    elif operation == "create_car_lights":
        body = _car_lights_script()
    elif operation == "apply_car_materials":
        body = _car_materials_script()
    elif operation == "setup_car_camera":
        body = _car_camera_script()
    elif operation == "setup_car_lighting":
        body = _car_lighting_script()
    elif operation == "create_car":
        body = "\n".join((
            _car_body_script(), _car_wheels_script(), _car_windows_script(),
            _car_lights_script(), _car_materials_script(), _car_camera_script(),
            _car_lighting_script(),
        ))
    elif operation == "render":
        body = "bpy.context.scene.render.filepath = " + repr(str(_safe_path(project.parent, arguments.get("output", "render.png")))) + "\nbpy.ops.render.render(write_still=True)"
    elif operation == "export":
        output = _safe_path(project.parent, arguments.get("output", "export.glb"))
        body = "bpy.ops.export_scene.gltf(filepath=" + repr(str(output)) + ", export_format='GLB')"
    elif operation == "execute_plan":
        if arguments.get("live"):
            return _live_plan_script(project, arguments)
        body = _plan_body(project, arguments)
    else:
        body = "bpy.ops.wm.save_as_mainfile(filepath=" + project_text + ")"
    script = "import bpy\n" + body + "\nbpy.ops.wm.save_as_mainfile(filepath=" + project_text + ")\n"
    return script


def _live_plan_script(project: Path, arguments: dict[str, Any]) -> str:
    steps = arguments.get("steps")
    if not isinstance(steps, list) or not steps or len(steps) > MAX_PLAN_STEPS:
        raise ValueError(f"Blender execute_plan requires 1 to {MAX_PLAN_STEPS} steps")
    marker = project.parent / "blender-complete.json"
    bodies: list[str] = []
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("operation"), str):
            raise ValueError("Every Blender plan step must contain an operation")
        operation = step["operation"]
        args = step.get("args", {})
        if operation not in OPERATIONS or operation == "execute_plan" or not isinstance(args, dict):
            raise ValueError(f"Unsupported live Blender step: {operation}")
        if operation == "render":
            nested = (
                "bpy.context.scene.render.filepath = "
                + repr(str(_safe_path(project.parent, args.get("output", "render.png"))))
            )
        else:
            nested = _script(operation, project, args).removeprefix("import bpy\n")
        nested = nested.split("\nbpy.ops.wm.save_as_mainfile", 1)[0]
        bodies.append(nested)
    preamble = ""
    if steps[0].get("operation") == "create_scene":
        preamble = bodies.pop(0) + "\n"
    branches = []
    for index, body in enumerate(bodies):
        branches.append(f"if _step == {index}:\n" + "\n".join(f"    {line}" for line in body.splitlines()))
    branches_text = "\n".join(branches)
    return (
        "import bpy\nimport json\nfrom pathlib import Path\n"
        f"_project = {str(project)!r}\n_marker = {str(marker)!r}\n"
        "_step = 0\n_step_delay = 0.8\n\n"
        "def _run_step():\n"
        "    global _step\n"
        f"    if _step >= {len(bodies)}:\n"
        "        bpy.ops.wm.save_as_mainfile(filepath=_project)\n"
        "        Path(_marker).write_text(json.dumps({'status': 'completed', 'steps': _step}), encoding='utf-8')\n"
        "        return None\n"
        f"    {branches_text.replace(chr(10), chr(10) + '    ')}\n"
        "    bpy.context.view_layer.update()\n"
        "    _step += 1\n"
        "    return _step_delay\n\n"
        f"{preamble}bpy.app.timers.register(_run_step, first_interval=0.5)\n"
    )


def _plan_body(project: Path, arguments: dict[str, Any]) -> str:
    steps = arguments.get("steps")
    if not isinstance(steps, list) or not steps or len(steps) > MAX_PLAN_STEPS:
        raise ValueError(f"Blender execute_plan requires 1 to {MAX_PLAN_STEPS} steps")
    bodies: list[str] = []
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("operation"), str):
            raise ValueError("Every Blender plan step must contain an operation")
        operation = step["operation"]
        if operation not in OPERATIONS or operation == "execute_plan":
            raise ValueError(f"Unsupported nested Blender operation: {operation}")
        args = step.get("args", {})
        if not isinstance(args, dict):
            raise ValueError(f"Arguments for {operation} must be an object")
        nested = _script(operation, project, args)
        nested = nested.removeprefix("import bpy\n")
        nested = nested.split("\nbpy.ops.wm.save_as_mainfile", 1)[0]
        bodies.append(nested)
    return "\n".join(bodies)


def _plan_outputs(root: Path, arguments: dict[str, Any]) -> tuple[Path, ...]:
    outputs = [_safe_path(root, arguments.get("project", "scene.blend"))]
    for step in arguments.get("steps", []):
        if isinstance(step, dict) and step.get("operation") == "render":
            args = step.get("args", {})
            outputs.append(_safe_path(root, args.get("output", "render.png")))
        if isinstance(step, dict) and step.get("operation") == "export":
            args = step.get("args", {})
            outputs.append(_safe_path(root, args.get("output", "scene.glb")))
    return tuple(outputs)


async def _wait_for_file(
    path: Path,
    timeout: float = 120.0,
    *,
    process: subprocess.Popen | None = None,
    log_path: Path | None = None,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not path.is_file() or path.stat().st_size == 0:
        if process is not None and process.poll() is not None:
            details = ""
            if log_path is not None and log_path.is_file():
                details = log_path.read_text(encoding="utf-8", errors="replace")[-1600:]
            raise RuntimeError(
                f"Blender exited with code {process.returncode} before producing "
                f"{path}. Diagnostics: {details}"
            )
        if log_path is not None and log_path.is_file():
            details = log_path.read_text(encoding="utf-8", errors="replace")
            if "Traceback (most recent call last)" in details or "Error:" in details:
                if process is not None and process.poll() is None:
                    process.terminate()
                raise RuntimeError(
                    f"Blender reported an execution error before producing {path}: "
                    f"{details[-1600:]}"
                )
        if asyncio.get_running_loop().time() >= deadline:
            raise RuntimeError(f"Blender did not produce verified output: {path}")
        await asyncio.sleep(0.25)


async def _wait_for_live_completion(
    marker: Path,
    project: Path,
    outputs: tuple[Path, ...],
    *,
    process: subprocess.Popen,
    timeout: float = 900.0,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not marker.is_file():
        if process.poll() is not None:
            raise RuntimeError(
                f"Live Blender process exited with code {process.returncode} "
                "before completing the plan"
            )
        if asyncio.get_running_loop().time() >= deadline:
            process.terminate()
            raise RuntimeError("Live Blender plan timed out before completion")
        await asyncio.sleep(0.5)
    if not project.is_file() or project.stat().st_size == 0:
        raise RuntimeError("Live Blender plan completed without a valid project file")
    for output in outputs:
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(f"Live Blender plan completed without output: {output}")


def _number(arguments: dict[str, Any], key: str, default: float) -> float:
    value = arguments.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Blender argument {key} must be numeric")
    return float(value)


def _primitive_script(operation: str, arguments: dict[str, Any]) -> str:
    operators = {
        "add_cube": "bpy.ops.mesh.primitive_cube_add()",
        "add_sphere": "bpy.ops.mesh.primitive_uv_sphere_add()",
        "add_cylinder": "bpy.ops.mesh.primitive_cylinder_add()",
        "add_cone": "bpy.ops.mesh.primitive_cone_add()",
        "add_torus": "bpy.ops.mesh.primitive_torus_add()",
        "add_plane": "bpy.ops.mesh.primitive_plane_add()",
    }
    return operators[operation] + "\n" + _object_transform_script(arguments)


def _object_transform_script(arguments: dict[str, Any]) -> str:
    name = arguments.get("name")
    if name is not None and (not isinstance(name, str) or not name.strip()):
        raise ValueError("Object name must be a non-empty string")
    transform = _transform_script(arguments)
    rename = f"\nbpy.context.active_object.name={name.strip()!r}" if name else ""
    return transform + rename


def _transform_script(arguments: dict[str, Any]) -> str:
    location = arguments.get("location", [0, 0, 0])
    scale = arguments.get("scale", [1, 1, 1])
    rotation = arguments.get("rotation", [0, 0, 0])
    values = (location, scale, rotation)
    if any(not isinstance(item, list) or len(item) != 3
           or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in item)
           for item in values):
        raise ValueError("location, scale, and rotation must be numeric 3-item arrays")
    return (
        "obj=bpy.context.active_object\n"
        f"obj.location={tuple(float(value) for value in location)!r}\n"
        f"obj.scale={tuple(float(value) for value in scale)!r}\n"
        f"obj.rotation_euler={tuple(float(value) for value in rotation)!r}"
    )


def _material_script(arguments: dict[str, Any]) -> str:
    name = arguments.get("name", "Material")
    color = arguments.get("color", [0.2, 0.4, 0.8, 1.0])
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Material name must be a non-empty string")
    if not isinstance(color, list) or len(color) not in (3, 4):
        raise ValueError("Material color must contain 3 or 4 numeric values")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in color):
        raise ValueError("Material color must contain numeric values")
    rgba = tuple(float(value) for value in color)
    if len(rgba) == 3:
        rgba += (1.0,)
    return (
        f"m=bpy.data.materials.get({name!r}) or bpy.data.materials.new({name!r})\n"
        f"m.diffuse_color={rgba!r}\n"
        "m.use_nodes=True\n"
        f"m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value={rgba!r}\n"
        "obj=bpy.context.active_object\n"
        "if obj and hasattr(obj.data, 'materials'):\n"
        "    obj.data.materials.append(m)"
    )


def _car_body_script() -> str:
    return """
def mat(name, color, metallic=0.0, roughness=0.45):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.metallic=metallic
    m.roughness=roughness
    return m
body_mat=mat("CarPaint",(0.08,0.22,0.65),0.65,0.25)
bpy.ops.mesh.primitive_cube_add(location=(0,0,1.05), scale=(2.2,1.0,0.38))
body=bpy.context.object
body.name="Car_Body"
body.data.materials.append(body_mat)
bpy.ops.object.modifier_add(type='BEVEL')
body.modifiers[-1].width=0.18
body.modifiers[-1].segments=4
bpy.ops.mesh.primitive_cube_add(location=(0.15,0,1.62), scale=(1.15,0.9,0.32))
cabin=bpy.context.object
cabin.name="Car_Cabin"
cabin.data.materials.append(body_mat)
bpy.ops.object.modifier_add(type='BEVEL')
cabin.modifiers[-1].width=0.22
cabin.modifiers[-1].segments=4
"""


def _car_wheels_script() -> str:
    return """
wheel_mat=bpy.data.materials.get("Rubber") or bpy.data.materials.new("Rubber")
wheel_mat.diffuse_color=(0.015,0.015,0.02,1)
for x in (-1.45,1.45):
    for y in (-1.05,1.05):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.42, depth=0.22,
                                            location=(x,y,0.62), rotation=(1.5708,0,0))
        wheel=bpy.context.object
        wheel.name=f"Car_Wheel_{x}_{y}"
        wheel.data.materials.append(wheel_mat)
"""


def _car_windows_script() -> str:
    return """
glass=bpy.data.materials.get("Glass") or bpy.data.materials.new("Glass")
glass.diffuse_color=(0.03,0.12,0.2,1)
glass.metallic=0.15
glass.roughness=0.08
for x in (-0.55,0.75):
    bpy.ops.mesh.primitive_cube_add(location=(x,0,1.67), scale=(0.48,0.92,0.18))
    window=bpy.context.object
    window.name="Car_Window"
    window.data.materials.append(glass)
"""


def _car_lights_script() -> str:
    return """
lamp=bpy.data.materials.get("Headlight") or bpy.data.materials.new("Headlight")
lamp.diffuse_color=(1.0,0.9,0.55,1)
for y in (-0.58,0.58):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12,
                                         location=(2.18,y,1.08), scale=(0.12,0.22,0.12))
    light=bpy.context.object
    light.name="Car_Headlight"
    light.data.materials.append(lamp)
"""


def _car_materials_script() -> str:
    return """
for obj in bpy.context.scene.objects:
    if obj.name.startswith("Car_Body") or obj.name.startswith("Car_Cabin"):
        if not obj.data.materials:
            m=bpy.data.materials.get("CarPaint") or bpy.data.materials.new("CarPaint")
            m.diffuse_color=(0.08,0.22,0.65,1)
            obj.data.materials.append(m)
"""


def _car_camera_script() -> str:
    return """
bpy.ops.object.camera_add(location=(7,-8,5), rotation=(0.98,0,0.72))
camera=bpy.context.object
camera.name="Car_Camera"
bpy.context.scene.camera=camera
"""


def _car_lighting_script() -> str:
    return """
bpy.ops.object.light_add(type='AREA', location=(3,-4,6))
key=bpy.context.object
key.name="Car_Key_Light"
key.data.energy=1200
key.data.shape='DISK'
key.data.size=5
bpy.ops.object.light_add(type='AREA', location=(-3,3,3))
fill=bpy.context.object
fill.name="Car_Fill_Light"
fill.data.energy=700
fill.data.size=4
"""
