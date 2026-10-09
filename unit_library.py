"""Editable presentation catalogue; manufacturing rules remain separate."""
import math
from rendering import Box, cabinet_geometry

LIBRARY = {
    'Single door base': {'width':600, 'shelves':1, 'description':'One door and one internal shelf.'},
    'Double door base': {'width':900, 'shelves':1, 'description':'Two equal doors and one internal shelf.'},
    'Three drawer base': {'width':600, 'shelves':0, 'description':'Three equal drawer fronts with illustrative drawer boxes.'},
    'Two drawer base': {'width':600, 'shelves':0, 'description':'Two equal deep drawer fronts.'},
    'Sink base': {'width':900, 'shelves':0, 'description':'Two doors; open internal service space. Sink and plumbing are not modelled.'},
    'Oven base': {'width':600, 'shelves':0, 'description':'Illustrative oven opening and appliance. Verify manufacturer clearances.'},
    'Pull-out base': {'width':300, 'shelves':0, 'description':'Narrow front with illustrative pull-out trays.'},
    'Open shelf base': {'width':600, 'shelves':2, 'description':'Open front and two shelves.'},
}
BASE_TYPES = ('Base cabinet', *LIBRARY)
ALL_TYPES = (*BASE_TYPES, 'Wardrobe', 'Panel', 'Worktop', 'Appliance')


def unit_geometry(kind,w,h,d,t,shelves,clearance,door_t,opened=False):
    count=0 if kind in ('Sink base','Oven base','Pull-out base','Two drawer base','Three drawer base') else shelves
    boxes=cabinet_geometry(w,h,d,t,count,clearance,door_t,opened)
    if kind in ('Base cabinet','Single door base','Wardrobe'):return boxes
    boxes=[b for b in boxes if b.kind!='door']
    front_y=-2-door_t
    if kind in ('Double door base','Sink base'):
        fw=(w-6)/2
        boxes += [Box('Left door',(2,front_y,2),(fw,door_t,h-4),'door',-100 if opened else 0),
                  Box('Right door',(w/2+1,front_y,2),(fw,door_t,h-4),'door')]
    elif kind in ('Three drawer base','Two drawer base'):
        n=3 if kind=='Three drawer base' else 2
        fh=(h-4-2*(n-1))/n
        for i in range(n):
            z=2+i*(fh+2)
            extension=160 if opened else 0
            boxes.append(Box(f'Drawer {i+1} front',(2,front_y-extension,z),(w-4,door_t,fh),'door'))
            inner=w-2*t-26
            if inner<=0:raise ValueError('Drawer unit is too narrow for illustrative runners.')
            boxes.append(Box(f'Drawer {i+1} base',(t+13,20-extension,z+20),(inner,max(100,d-60),t)))
            for x in (t+13,w-t-13-t):
                boxes.append(Box(f'Drawer {i+1} side',(x,20-extension,z+20),(t,max(100,d-60),max(20,fh-40))))
    elif kind=='Pull-out base':
        extension=160 if opened else 0
        boxes.append(Box('Pull-out front',(2,front_y-extension,2),(w-4,door_t,h-4),'door'))
        for i in range(3):
            boxes.append(Box(f'Pull-out tray {i+1}',(t+10,20-extension,70+i*(h-140)/3),(w-2*t-20,d-60,12),'metal'))
    elif kind=='Oven base':
        if h<400 or w<400:raise ValueError('Oven preview needs width and height of at least 400 mm.')
        boxes.append(Box('Oven placeholder',(t+10,-2,80),(w-2*t-20,d-40,h-160),'appliance'))
        boxes.append(Box('Lower oven fascia',(2,front_y,2),(w-4,door_t,74),'door'))
        boxes.append(Box('Upper oven fascia',(2,front_y,h-74),(w-4,door_t,72),'door'))
    return boxes


def next_position(rows,w,d,layout):
    """Find an empty footprint, front row first, with door space inside the room."""
    occupied=[]
    for row in rows:
        try:
            x,y,z=(float(row[k]) for k in ('X (mm)','Y (mm)','Z (mm)'))
            rw,rd,rh=(float(row[k]) for k in ('Width (mm)','Depth (mm)','Height (mm)'))
            angle=float(row['Rotation (deg)'])
            if not all(math.isfinite(v) for v in (x,y,z,rw,rd,rh,angle)):continue
            p=Box('footprint',(x,y,z),(rw,rd,rh),angle=angle).vertices()
            occupied.append((p[:,0].min(),p[:,1].min(),p[:,0].max(),p[:,1].max()))
        except (KeyError,TypeError,ValueError):continue
    xs=sorted({0.,*(float(b[2]) for b in occupied)})
    ys=sorted({25.,*(float(b[3])+600 for b in occupied)})
    for y in ys:
        for x in xs:
            if x+w>layout['length'] or y+d+3>layout['width']:continue
            if not any(x<b[2]-.01 and x+w>b[0]+.01 and y<b[3]-.01 and y+d>b[1]+.01 for b in occupied):return x,y
    raise ValueError('No free space for this unit. Reposition existing units, reduce the width, or revise the room layout.')


def library_row(kind,w,h,d,rows,layout):
    if kind not in LIBRARY:raise ValueError('Select a library unit.')
    if not all(math.isfinite(v) for v in (w,h,d)) or w<150 or h<200 or d<200 or h>layout['height']:
        raise ValueError('Use valid unit dimensions that fit the room height.')
    x,y=next_position(rows,w,d,layout)
    return {'Name':f'{kind} {len(rows)+1}','Type':kind,'Width (mm)':w,'Height (mm)':h,'Depth (mm)':d,
            'X (mm)':x,'Y (mm)':y,'Z (mm)':0,'Rotation (deg)':0,'Shelves':LIBRARY[kind]['shelves']}
