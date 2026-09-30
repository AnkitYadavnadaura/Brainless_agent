"""Shared spatial contracts for website-planned, connected settlement districts."""
from __future__ import annotations

import math

KINDS = ('house', 'villa', 'tree', 'plants', 'stairs', 'gate', 'door', 'drum', 'water')
ATTACHMENTS = {'stairs', 'gate', 'door'}
INFRASTRUCTURE_PARTS = ('block', 'gully_east_west', 'gully_north_south', 'drainage')
HOUSE_PARTS = ('foundation', 'wall_south', 'wall_north', 'wall_west', 'wall_east', 'roof', 'entrance')


def validate_component(job):
    component = job.get('component')
    if component is None:
        return
    allowed = INFRASTRUCTURE_PARTS if job.get('phase') == 'infrastructure' else (
        HOUSE_PARTS if job.get('phase') == 'create' and
        job.get('object', {}).get('kind') in ('house', 'villa') else ())
    if component not in allowed:
        raise ValueError('Unsupported district component')


def master_plan(config, grid=4):
    if type(grid) is not int or not 2 <= grid <= 8:
        raise ValueError('District grid must be between 2 and 8')
    extent = config['extent']
    size = 2 * extent / grid
    if size < 24:
        raise ValueError('Districts require at least 24 metres per side')
    edges, areas = {}, []
    for row in range(grid):
        for col in range(grid):
            ident = f'area-{row}-{col}'
            xmin, ymin = -extent + col*size, -extent + row*size
            bounds = [xmin, ymin, xmin+size, ymin+size]
            edge_ids = {}
            for side, key, point in (
                ('west', f'v-{row}-{col}', [xmin, ymin+size/2, 0]),
                ('east', f'v-{row}-{col+1}', [xmin+size, ymin+size/2, 0]),
                ('south', f'h-{row}-{col}', [xmin+size/2, ymin, 0]),
                ('north', f'h-{row+1}-{col}', [xmin+size/2, ymin+size, 0])):
                # One canonical record: both neighbours reference the same border.
                edges.setdefault(key, dict(id=key, road_port=point, road_width=4,
                    elevation=0, verge_width=1, palette='weathered rural stone/plaster/timber'))
                edge_ids[side] = key
            # A global drainage channel crosses every column at the same Y and water level.
            areas.append(dict(id=ident, row=row, col=col, bounds=bounds, edges=edge_ids,
                center=[xmin+size/2, ymin+size/2],
                channel_y=ymin+size*.16, channel_width=1.2, water_level=-.16,
                neighbours=[f'area-{r}-{c}' for r,c in ((row-1,col),(row,col-1),(row,col+1),(row+1,col))
                            if 0 <= r < grid and 0 <= c < grid]))
    return dict(version=2, units='metres', coordinates='global XYZ; Z up',
                grid=grid, extent=extent, edges=edges, areas=areas,
                continuity='Shared world coordinates, road ports, flat settlement elevation and drainage levels')


def area_context(master, area, plans):
    return dict(area=area, borders={k: master['edges'][v] for k,v in area['edges'].items()},
        neighbours={ident: plans.get(ident, {'status': 'not yet planned; shared borders already fixed'})
                    for ident in area['neighbours']},
        global_style='Coherent rural village; aged plaster, stone, timber, terracotta, local vegetation',
        constraints='Keep roads, verges and channel clear; footprints in global metres; no border edits')


def number(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'Expected finite number in [{low}, {high}]')
    return float(value)


def starter_area_plan(area):
    """A sparse, validated layout that fits even the minimum 24m district."""
    xmin, ymin, xmax, ymax = area['bounds']
    cx, cy = area['center']
    # Upper quadrants avoid the drainage channel. Include the full 2m
    # house clearance, 3m road verge and .5m district border setback.
    objects = []
    for index, (left, right) in enumerate(((xmin+.5, cx-3), (cx+3, xmax-.5))):
        bottom, top = cy+3, ymax-.5
        ident = f'home{index+1}'
        objects.extend([
            dict(id=ident, kind='house', x=(left+right)/2, y=(bottom+top)/2,
                 width=min(6, right-left-4), depth=min(6, top-bottom-4), height=4),
            dict(id=f'{ident}_door', kind='door', parent=ident),
            dict(id=f'{ident}_stairs', kind='stairs', parent=ident),
        ])
    return validate_area(dict(objects=objects,
        rationale='Sparse runtime layout with two homes and connected entrances; additional scenery omitted.'), area)


def validate_area(value, area):
    if not isinstance(value, dict) or not isinstance(value.get('objects'), list) or not 1 <= len(value['objects']) <= 80:
        raise ValueError('Area requires 1..80 structured objects')
    result, used = [], {}
    xmin,ymin,xmax,ymax = area['bounds']
    cx,cy = area['center']
    for index, raw in enumerate(value['objects']):
        if not isinstance(raw, dict) or not isinstance(raw.get('kind'), str) or raw.get('kind') not in KINDS:
            raise ValueError('Unsupported district object')
        ident = raw.get('id')
        if not isinstance(ident, str) or not ident.isascii() or not ident.replace('_','').replace('-','').isalnum() or len(ident)>50 or ident in used:
            raise ValueError('Object IDs must be unique simple identifiers')
        kind = raw['kind']
        if kind in ATTACHMENTS:
            if not isinstance(raw.get('parent'), str):
                raise ValueError('Doors, gates and stairs need an earlier house/villa parent')
            parent = used.get(raw.get('parent'))
            if parent is None or parent['kind'] not in ('house','villa'):
                raise ValueError('Doors, gates and stairs need an earlier house/villa parent')
            # Attachment positions are runtime-owned so entrances cannot float or disconnect.
            x,y = parent['x'], parent['y']-parent['depth']/2
            width,depth,height = (1.2, .2, 2.1) if kind=='door' else (1.8, 1.2, .45) if kind=='stairs' else (2.4,.2,1.4)
        else:
            x,y = number(raw.get('x'),xmin+2,xmax-2), number(raw.get('y'),ymin+2,ymax-2)
            width = number(raw.get('width'), .3, 16)
            depth = number(raw.get('depth'), .3, 16)
            height = number(raw.get('height'), .2, 14)
            # Reserve space for roof overhangs, entrance steps and future object polishing.
            margin = 2 if kind in ('house','villa') else .5
            left,right,bottom,top = x-width/2-margin,x+width/2+margin,y-depth/2-margin,y+depth/2+margin
            if left<xmin+.5 or right>xmax-.5 or bottom<ymin+.5 or top>ymax-.5:
                raise ValueError(
                    f'Object footprint crosses district border: {ident!r} in {area["id"]}; '
                    f'padded bounds {[left,bottom,right,top]}, district bounds {area["bounds"]}. '
                    f'For width={width}, depth={depth}, margin={margin}, center must satisfy '
                    f'x in [{max(xmin+2,xmin+.5+width/2+margin)}, '
                    f'{min(xmax-2,xmax-.5-width/2-margin)}], '
                    f'y in [{max(ymin+2,ymin+.5+depth/2+margin)}, '
                    f'{min(ymax-2,ymax-.5-depth/2-margin)}]. Roads/channel/overlaps still apply.')
            if left<cx+3 and right>cx-3 or bottom<cy+3 and top>cy-3:
                raise ValueError('Object blocks shared road or verge')
            if bottom<area['channel_y']+1 and top>area['channel_y']-1:
                raise ValueError('Object blocks connected drainage channel')
            for other in result:
                if other['kind'] in ATTACHMENTS:
                    continue
                pad = 2 if other['kind'] in ('house','villa') else .5
                if left<other['x']+other['width']/2+pad and right>other['x']-other['width']/2-pad and bottom<other['y']+other['depth']/2+pad and top>other['y']-other['depth']/2-pad:
                    raise ValueError('Independent object footprints overlap')
        obj = dict(id=ident, kind=kind, x=x,y=y,width=width,depth=depth,height=height,
                   parent=raw.get('parent') if kind in ATTACHMENTS else None)
        used[ident]=obj
        result.append(obj)
    # Entrance-to-road corridors may be shared, but must not run through another object.
    for home in result:
        if home['kind'] not in ('house','villa'):
            continue
        path_y=home['y']-home['depth']/2-1.25
        left,right=sorted((home['x'],cx))
        for other in result:
            if other['id']==home['id'] or other['kind'] in ATTACHMENTS:
                continue
            if left<other['x']+other['width']/2+.25 and right>other['x']-other['width']/2-.25 and path_y-.5<other['y']+other['depth']/2+.25 and path_y+.5>other['y']-other['depth']/2-.25:
                raise ValueError('Object blocks an entrance-to-road access corridor')
    return dict(objects=result, rationale=str(value.get('rationale',''))[:2000])


def validate_polish(value):
    if not isinstance(value, dict):
        raise ValueError('Polish must be structured data')
    return dict(weathering=number(value.get('weathering', .4),0,1),
        detail=number(value.get('detail', 2),1,4),
        roughness=number(value.get('roughness', .7),.05,1),
        reason=str(value.get('reason',''))[:2000])
