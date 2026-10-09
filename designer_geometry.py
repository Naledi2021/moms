"""Millimetre 2D geometry and validated design mutations, independent of Streamlit."""
from copy import deepcopy
import hashlib
import json
import math
from unit_library import ALL_TYPES

NUMERIC = ('Width (mm)','Height (mm)','Depth (mm)','X (mm)','Y (mm)','Z (mm)','Rotation (deg)','Shelves')


def fingerprint(layout, rows):
    return hashlib.sha256(json.dumps({'layout':layout,'rows':rows},sort_keys=True,allow_nan=False).encode()).hexdigest()


def footprint(row):
    x,y,w,d,a=(float(row[k]) for k in ('X (mm)','Y (mm)','Width (mm)','Depth (mm)','Rotation (deg)'))
    c,s=math.cos(math.radians(a)),math.sin(math.radians(a))
    return [(x+u*c-v*s,y+u*s+v*c) for u,v in ((0,0),(w,0),(w,d),(0,d))]


def bounds(row):
    p=footprint(row)
    return min(x for x,y in p),min(y for x,y in p),max(x for x,y in p),max(y for x,y in p)


def intersects(a,b,tolerance=.01):
    """Separating-axis test for convex polygons; touching edges are not collisions."""
    for polygon in (a,b):
        for p,q in zip(polygon,polygon[1:]+polygon[:1]):
            axis=(q[1]-p[1],p[0]-q[0]);length=math.hypot(*axis)
            if length<1e-9:continue
            axis=(axis[0]/length,axis[1]/length)
            aa=[x*axis[0]+y*axis[1] for x,y in a];bb=[x*axis[0]+y*axis[1] for x,y in b]
            if min(max(aa),max(bb))-max(min(aa),min(bb))<=tolerance:return False
    return True


def vertical_overlap(a,b):
    return min(float(a['Z (mm)'])+float(a['Height (mm)']),float(b['Z (mm)'])+float(b['Height (mm)']))-max(float(a['Z (mm)']),float(b['Z (mm)']))>.01


def validate_unit(row,layout):
    if not isinstance(row.get('Name'),str) or not row['Name'].strip():raise ValueError('Every unit needs a name.')
    if row.get('Type') not in ALL_TYPES:raise ValueError('Choose a supported unit type.')
    try:values=[float(row[k]) for k in NUMERIC]
    except (KeyError,TypeError,ValueError):raise ValueError('Complete every numeric unit field.')
    if not all(math.isfinite(v) for v in values):raise ValueError('Unit measurements must be finite numbers.')
    w,h,d,x,y,z,a,s=values
    if min(w,h,d)<=0 or z<0 or z+h>layout['height'] or s<0 or s>20 or not s.is_integer():raise ValueError('Unit dimensions, elevation or shelf count are invalid.')
    left,top,right,bottom=bounds(row)
    if left<-.01 or top<-.01 or right>layout['length']+.01 or bottom>layout['width']+.01:raise ValueError('Unit footprint is outside the room.')
    return row


def opening_zone(opening,layout):
    offset=float(opening['Offset (mm)']);span=float(opening['Width (mm)'])
    # A keep-clear strip, not a claim about actual hinge direction or door swing.
    inset=min(span,1000) if opening['Type']=='Door' else 100
    wall=opening['Wall'];L=layout['length'];D=layout['width']
    if wall=='Front':return [(offset,0),(offset+span,0),(offset+span,inset),(offset,inset)]
    if wall=='Back':return [(offset,D-inset),(offset+span,D-inset),(offset+span,D),(offset,D)]
    if wall=='Left':return [(0,offset),(inset,offset),(inset,offset+span),(0,offset+span)]
    return [(L-inset,offset),(L,offset),(L,offset+span),(L-inset,offset+span)]


def collision_warnings(rows,layout):
    messages=[];valid=[]
    for i,row in enumerate(rows):
        try:validate_unit(row,layout);valid.append((i,row))
        except ValueError as error:messages.append(f'Row {i+1}: {error}')
    for n,(i,a) in enumerate(valid):
        for j,b in valid[n+1:]:
            if vertical_overlap(a,b) and intersects(footprint(a),footprint(b)):
                messages.append(f'{a["Name"]} overlaps {b["Name"]}.')
        for opening in layout['openings']:
            zone={'Z (mm)':opening['Sill (mm)'],'Height (mm)':opening['Height (mm)']}
            if vertical_overlap(a,zone) and intersects(footprint(a),opening_zone(opening,layout)):
                messages.append(f'{a["Name"]} conflicts with a {opening["Type"].lower()} on the {opening["Wall"].lower()} wall.')
    return messages


def snap_unit(row,rows,index,layout,tolerance=20):
    """Snap bounding edges to walls and nearby neighbours with a shared span."""
    result=dict(row);left,top,right,bottom=bounds(result)
    dx=[-left,layout['length']-right];dy=[-top,layout['width']-bottom]
    for i,other in enumerate(rows):
        if i==index:continue
        try:validate_unit(other,layout)
        except ValueError:continue
        if not vertical_overlap(result,other):continue
        l,t,r,b=bounds(other)
        if min(bottom,b)-max(top,t)>0:dx.extend([r-left,l-right,l-left,r-right])
        if min(right,r)-max(left,l)>0:dy.extend([b-top,t-bottom,t-top,b-bottom])
    for key,options in (('X (mm)',dx),('Y (mm)',dy)):
        candidates=[v for v in options if abs(v)<=tolerance]
        if candidates:result[key]=float(result[key])+min(candidates,key=abs)
    return result


def along_wall(row,wall,offset,layout):
    result=dict(row);w=float(row['Width (mm)']);d=float(row['Depth (mm)']);offset=float(offset)
    if not math.isfinite(offset) or offset<0:raise ValueError('Wall offset must be non-negative and finite.')
    choices={'Front':(offset+w,d,180),'Back':(offset,layout['width']-d,0),
             'Left':(d,offset,90),'Right':(layout['length']-d,offset+w,270)}
    if wall not in choices:raise ValueError('Choose a room wall.')
    x,y,a=choices[wall];result.update({'X (mm)':x,'Y (mm)':y,'Rotation (deg)':a})
    return validate_unit(result,layout)


def approve_design(layout,rows):
    if not rows:raise ValueError('Add at least one unit before approving.')
    warnings=collision_warnings(rows,layout)
    if warnings:raise ValueError('Resolve invalid units and collision warnings before approval.')
    from datetime import datetime,timezone
    return {'layout':deepcopy(layout),'rows':deepcopy(rows),'fingerprint':fingerprint(layout,rows),'approved_utc':datetime.now(timezone.utc).isoformat()}


def require_unlocked(lock):
    if lock:raise ValueError('This design is approved and locked. Explicitly unlock it before editing.')


def apply_event(rows,layout,event,lock=None,snap=True):
    require_unlocked(lock)
    if not isinstance(event,dict) or event.get('revision')!=fingerprint(layout,rows):raise ValueError('This canvas is out of date. Retry on the refreshed plan.')
    if event.get('action')=='add':
        from unit_library import LIBRARY,library_row
        kind=event.get('unit_type')
        if kind not in LIBRARY:raise ValueError('Choose a cabinet from the library.')
        if len(rows)>=30:raise ValueError('The design supports at most 30 units.')
        spec=LIBRARY[kind]
        if 'x' in event or 'y' in event:
            row={'Name':f'{kind} {len(rows)+1}','Type':kind,'Width (mm)':spec['width'],'Height (mm)':spec['height'],'Depth (mm)':spec['depth'],
                 'X (mm)':round(float(event['x']),3),'Y (mm)':round(float(event['y']),3),'Z (mm)':spec['elevation'],'Rotation (deg)':0,'Shelves':spec['shelves']}
            if snap:row=snap_unit(row,rows,len(rows),layout)
            validate_unit(row,layout)
        else:row=library_row(kind,spec['width'],spec['height'],spec['depth'],rows,layout)
        return deepcopy(rows)+[row]
    index=event.get('index')
    if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(rows):raise ValueError('Select a current unit.')
    current=deepcopy(rows);row=current[index];action=event.get('action')
    if action=='delete':return current[:index]+current[index+1:]
    validate_unit(row,layout)
    if action=='move':
        x,y=float(event['x']),float(event['y'])
        if not math.isfinite(x) or not math.isfinite(y):raise ValueError('Coordinates must be finite.')
        row.update({'X (mm)':round(x,3),'Y (mm)':round(y,3)})
        if snap:row=snap_unit(row,current,index,layout)
    elif action=='rotate':
        # Keep the centre fixed, including for non-square units.
        w,d=float(row['Width (mm)']),float(row['Depth (mm)']);a=math.radians(float(row['Rotation (deg)']))
        cx=float(row['X (mm)'])+w/2*math.cos(a)-d/2*math.sin(a)
        cy=float(row['Y (mm)'])+w/2*math.sin(a)+d/2*math.cos(a)
        angle=(float(row['Rotation (deg)'])+90)%360;r=math.radians(angle)
        row.update({'Rotation (deg)':angle,'X (mm)':cx-w/2*math.cos(r)+d/2*math.sin(r),'Y (mm)':cy-w/2*math.sin(r)-d/2*math.cos(r)})
    else:raise ValueError('Unsupported canvas action.')
    validate_unit(row,layout);current[index]=row
    return current


def floor_plan_svg(layout,rows):
    """Export the authoritative 2D footprint, independent of 3D presentation panels."""
    from xml.sax.saxutils import escape
    L,D=layout['length'],layout['width'];font=max(L,D)/65
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-font*5} {-font*4} {L+font*10} {D+font*8}" role="img" aria-label="Dimensioned kitchen floor plan">',
           f'<rect x="{-font*5}" y="{-font*4}" width="{L+font*10}" height="{D+font*8}" fill="white"/>',
           f'<rect width="{L}" height="{D}" fill="#f5f2eb" stroke="#15304a" stroke-width="10"/>',
           f'<text x="{L/2}" y="{-font*1.7}" text-anchor="middle" font-family="sans-serif" font-size="{font}">FRONT — {L:g} mm</text>',
           f'<text x="{L/2}" y="{D+font*2}" text-anchor="middle" font-family="sans-serif" font-size="{font}">BACK — room depth {D:g} mm; height {layout["height"]:g} mm</text>']
    for opening in layout['openings']:
        off,span=float(opening['Offset (mm)']),float(opening['Width (mm)']);wall=opening['Wall']
        if wall in ('Front','Back'):a,b,c,d=off,0 if wall=='Front' else D,off+span,0 if wall=='Front' else D
        else:a,b,c,d=0 if wall=='Left' else L,off,0 if wall=='Left' else L,off+span
        color='#ed9433' if opening['Type']=='Door' else '#258fca'
        parts.append(f'<path d="M {a} {b} L {c} {d}" stroke="{color}" stroke-width="25"/>')
    for row in rows:
        try:validate_unit(row,layout)
        except ValueError:continue
        p=footprint(row);points=' '.join(f'{x:.6f},{y:.6f}' for x,y in p);x=sum(v[0] for v in p)/4;y=sum(v[1] for v in p)/4
        color='#d7e7f5' if float(row['Z (mm)'])>0 else '#d5dfd4'
        parts.append(f'<polygon points="{points}" fill="{color}" fill-opacity=".7" stroke="#385b74" stroke-width="6"/>')
        label=escape(f'{row["Name"]}: {float(row["Width (mm)"]):g} × {float(row["Depth (mm)"]):g} mm; z={float(row["Z (mm)"]):g}')
        parts.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="sans-serif" font-size="{font*.6}">{label}</text>')
    parts.append('</svg>')
    return ''.join(parts)
