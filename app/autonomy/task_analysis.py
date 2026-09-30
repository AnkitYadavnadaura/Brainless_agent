"""Conservative software selection before the existing capability workflow."""
import re

from app.autonomy.model_workflow import model_requested
from app.autonomy.village_workflow import village_requested


def analyse_task(task):
    names = {'Blender': r'\bblender\b', 'Unreal Engine': r'\bunreal(?: engine)?\b',
             'Unity': r'\bunity\b', 'Maya': r'\bmaya\b', '3ds Max': r'\b3ds\s*max\b',
             'Cinema 4D': r'\bcinema\s*4d\b', 'SketchUp': r'\bsketchup\b',
             'Photoshop': r'\bphotoshop\b', 'FreeCAD': r'\bfreecad\b', 'AutoCAD': r'\bautocad\b'}
    explicit = [name for name, expression in names.items() if re.search(expression, task, re.I)]
    modelling = model_requested(task) or village_requested(task)
    software = explicit[0] if len(explicit) == 1 else ' + '.join(explicit) if explicit else 'Blender' if modelling else 'none'
    return {'software': software, 'explicit': bool(explicit),
            'workflow': 'blender' if software == 'Blender' else 'general',
            'assumption': 'Software supplied in task' if explicit else
                          'Blender inferred for 3D construction' if modelling else
                          'Software is not specified; the team will analyse requirements before proposing tools'}
