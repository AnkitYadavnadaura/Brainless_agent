"""Deterministic starter assemblies when a supported landmark plan needs repair."""
import re


def landmark_starter(objective):
    """Return an explicitly approximate Taj Mahal assembly, or no fallback."""
    if not re.search(r'\btaj\s*mahal\b',objective,re.I):
        return None
    steps=[dict(operation='create_scene',args={},label='New landmark scene')]
    marble=[.86,.85,.79,1]
    stone=[.57,.5,.4,1]
    def add(operation,name,location,scale,color=marble,rotation=None):
        steps.append(dict(operation=operation,args=dict(name=name,location=location,scale=scale,
                          rotation=rotation or [0,0,0]),label=name+' / geometry'))
        steps.append(dict(operation='add_material',args=dict(target=name,name=name+'_material',color=color),label=name+' / material'))
    add('add_cube','GardenGround',[0,-12,-.25],[32,45,.25],[.12,.22,.08,1])
    add('add_cube','MarbleTerrace',[0,0,.75],[17,17,.75])
    add('add_cube','Mausoleum',[0,0,5.5],[10,10,4])
    steps.append(dict(operation='bevel',args=dict(target='Mausoleum',width=.12,segments=3),label='Mausoleum / softened edges'))
    add('add_cylinder','CentralDrum',[0,0,10.4],[4.6,4.6,.9])
    add('add_dome','CentralDome',[0,0,11.3],[5,5,4.3])
    add('add_cone','CentralFinial',[0,0,20.6],[.25,.25,.7],[.65,.48,.14,1])
    for x in (-14,14):
        for y in (-14,14):
            suffix=f'{"West" if x<0 else "East"}{"Front" if y<0 else "Rear"}'
            add('add_cylinder',suffix+'Minaret',[x,y,8],[.9,.9,6.5])
            for level,z in enumerate((4.5,8.5,12.5)):
                add('add_torus',suffix+f'Balcony{level}',[x,y,z],[1.2,1.2,.35])
            add('add_dome',suffix+'MinaretDome',[x,y,14.6],[1.25,1.25,1.1])
            add('add_dome',suffix+'CornerDome',[x/2,y/2,9.5],[2.1,2.1,2])
    for side,y,rotation in (('Front',-10.2,[0,0,0]),('Rear',10.2,[0,0,3.14159265])):
        add('add_arch',side+'MainArch',[0,y,1.5],[3.1,1.5,2.55],rotation=rotation)
        for x in (-6.7,6.7):
            for level,z in enumerate((1.6,5.6)):
                add('add_arch',side+f'Arch{x}_{level}',[x,y,z],[1.5,1,1.1],rotation=rotation)
    add('add_cube','GardenWalk',[0,-34,.03],[4.2,16,.05],stone)
    add('add_cube','ReflectingPool',[0,-34,.09],[1.8,14,.04],[.1,.32,.42,1])
    for x in (-8,8):
        for index,y in enumerate((-24,-32,-40,-48)):
            add('add_cone',f'Cypress{x}_{index}',[x,y,2],[.8,.8,2],[.05,.16,.045,1])
    steps.extend([
        dict(operation='add_camera',args=dict(name='Overview',location=[46,-64,38],rotation=[1.18,0,.623])),
        dict(operation='add_light',args=dict(name='Key',location=[8,-12,36],rotation=[0,0,0],energy=65000)),
        dict(operation='add_light',args=dict(name='Fill',location=[-20,5,24],rotation=[0,0,0],energy=35000)),
        dict(operation='render',args=dict(samples=256,resolution=2560),label='Landmark / final render'),
    ])
    return dict(ordered_steps=steps,unsupported=[
        'Procedural Taj Mahal approximation: surveyed proportions, carved marble ornament and inlay are not reproduced exactly.'])
