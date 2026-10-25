"""Validated room-feature additions shared by the simple forms and tests."""
from copy import deepcopy
import math
import pandas as pd
from designer_geometry import require_unlocked
from room_geometry import validate_walls


def editor_rows(rows,columns,changes):
    frame=pd.DataFrame(rows,columns=columns)
    if 'Locked' in columns:frame['Locked']=frame['Locked'].fillna(True).astype(bool)
    for index,edits in changes.get('edited_rows',{}).items():
        for column,value in edits.items():frame.loc[int(index),column]=value
    if changes.get('deleted_rows'):frame=frame.drop(changes['deleted_rows'],errors='ignore')
    if changes.get('added_rows'):frame=pd.concat([frame,pd.DataFrame(changes['added_rows'])],ignore_index=True)
    return frame.to_dict(orient='records')


def add_feature(layout,openings,walls,kind,values,lock=None):
    require_unlocked(lock)
    openings=deepcopy(openings);walls=deepcopy(walls)
    if kind=='Wall':
        length=float(values['length']);angle=float(values['angle']);x=float(values['x']);y=float(values['y']);thickness=float(values['thickness'])
        if not all(math.isfinite(v) for v in (length,angle,x,y,thickness)) or length<50:raise ValueError('Wall length must be at least 50 mm and all measurements must be finite.')
        r=math.radians(angle)
        walls.append({'Name':str(values.get('name') or f'Wall {len(walls)+1}'),'Start X (mm)':x,'Start Y (mm)':y,'End X (mm)':round(x+length*math.cos(r),3),'End Y (mm)':round(y+length*math.sin(r),3),'Thickness (mm)':thickness,'Locked':bool(values.get('locked',True))})
    elif kind in ('Window','Door'):
        openings.append({'Type':kind,'Wall':values['wall'],'Offset (mm)':float(values['offset']),'Width (mm)':float(values['length']),'Height (mm)':float(values['height']),'Sill (mm)':float(values.get('sill',0))})
    else:raise ValueError('Choose Wall, Window or Door.')
    from layout_ui import validate_layout
    validate_layout(layout['length'],layout['width'],layout['height'],openings)
    validate_walls(walls,layout)
    return openings,walls


def edit_wall(layout,walls,index,start=None,end=None,delta=None,lock=None):
    require_unlocked(lock)
    if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(walls):raise ValueError('Select a current wall.')
    if walls[index].get('Locked',True):raise ValueError('This wall is locked. Use Unlock selected wall before dragging it.')
    result=deepcopy(walls);wall=result[index]
    if delta is not None:
        dx,dy=map(float,delta)
        for key,amount in (('Start X (mm)',dx),('End X (mm)',dx),('Start Y (mm)',dy),('End Y (mm)',dy)):wall[key]=round(float(wall[key])+amount,3)
    for point,keys in ((start,('Start X (mm)','Start Y (mm)')),(end,('End X (mm)','End Y (mm)'))):
        if point is not None:
            for key,value in zip(keys,point):wall[key]=round(float(value),3)
    validate_walls(result,layout)
    return result


def correct_wall(layout,walls,index,x,y,length,angle,thickness=None,name=None,lock=None):
    """An explicit measured correction, followed by re-locking the corrected wall."""
    require_unlocked(lock)
    if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(walls):raise ValueError('Select a current wall.')
    x,y,length,angle=map(float,(x,y,length,angle))
    if not all(math.isfinite(v) for v in (x,y,length,angle)) or length<50:raise ValueError('Use finite measurements and a wall length of at least 50 mm.')
    result=deepcopy(walls);wall=result[index];r=math.radians(angle)
    wall.update({'Start X (mm)':x,'Start Y (mm)':y,'End X (mm)':round(x+length*math.cos(r),3),'End Y (mm)':round(y+length*math.sin(r),3),'Locked':True})
    if thickness is not None:wall['Thickness (mm)']=float(thickness)
    if name is not None:wall['Name']=name
    validate_walls(result,layout)
    return result
