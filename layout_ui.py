from dataclasses import asdict
import hashlib
import json
import math
from xml.sax.saxutils import escape
import pandas as pd
import streamlit as st
from rendering import Box,cabinet_geometry
from unit_library import ALL_TYPES,BASE_TYPES,LIBRARY,unit_geometry,library_row,next_position

OPENING_COLUMNS=['Type','Wall','Offset (mm)','Width (mm)','Height (mm)','Sill (mm)']


def validate_layout(length,width,height,openings):
    if not all(math.isfinite(v) and v>0 for v in (length,width,height)):
        raise ValueError('Room dimensions must be positive and finite.')
    if len(openings)>100:raise ValueError('Use at most 100 room openings.')
    for row in openings:
        if row['Type'] not in ('Door','Window') or row['Wall'] not in ('Front','Back','Left','Right'):
            raise ValueError('Each opening needs a type and wall.')
        a,b,c,d=(float(row[k]) for k in OPENING_COLUMNS[2:])
        span=length if row['Wall'] in ('Front','Back') else width
        if not all(math.isfinite(v) for v in (a,b,c,d)) or a<0 or b<=0 or c<=0 or d<0 or a+b>span or c+d>height:
            raise ValueError('Opening dimensions must fit its wall and room height.')
    for i,a in enumerate(openings):
        for b in openings[i+1:]:
            if a['Wall']==b['Wall'] and max(a['Offset (mm)'],b['Offset (mm)'])<min(a['Offset (mm)']+a['Width (mm)'],b['Offset (mm)']+b['Width (mm)']) and max(a['Sill (mm)'],b['Sill (mm)'])<min(a['Sill (mm)']+a['Height (mm)'],b['Sill (mm)']+b['Height (mm)']):
                raise ValueError('Two openings overlap on the same wall.')
    return dict(length=length,width=width,height=height,openings=openings)


def plan_svg(layout,boxes=None):
    length=layout['length'];width=layout['width'];scale=min(680/length,520/width);x=80;y=80
    pieces=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 760" role="img" aria-label="Room floor plan"><rect width="900" height="760" fill="white"/>',f'<rect x="{x}" y="{y}" width="{length*scale}" height="{width*scale}" fill="#f5f2eb" stroke="#243b53" stroke-width="5"/>']
    for row in layout['openings']:
        offset=row['Offset (mm)']*scale;size=row['Width (mm)']*scale
        if row['Wall'] in ('Front','Back'):
            a=x+offset;b=y+(width*scale if row['Wall']=='Back' else 0);c=a+size;d=b
        else:
            a=x+(length*scale if row['Wall']=='Right' else 0);b=y+offset;c=a;d=b+size
        colour='#e69840' if row['Type']=='Door' else '#2581b6'
        pieces.append(f'<path d="M {a} {b} L {c} {d}" stroke="{colour}" stroke-width="8"/>')
    if boxes:
        for box in boxes:
            if box.kind in ('floor','wall'):continue
            p=box.vertices()[:4,:2];coords=' '.join(f'{x+a*scale:.1f},{y+b*scale:.1f}' for a,b in p)
            pieces.append(f'<polygon points="{coords}" fill="#ccd7dc" fill-opacity=".3" stroke="#536779" stroke-width="1"/>')
        groups={}
        for box in boxes:
            if box.kind in ('floor','wall'):continue
            name=box.name.split(' — ',1)[0]
            groups.setdefault(name,[]).extend(box.vertices()[:4,:2])
        for name,points in groups.items():
            points=__import__('numpy').array(points);centre=(points.min(axis=0)+points.max(axis=0))/2
            pieces.append(f'<text x="{x+centre[0]*scale:.1f}" y="{y+centre[1]*scale:.1f}" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#243b53">{escape(name)}</text>')

    pieces += [f'<text x="{x}" y="50" font-family="sans-serif" font-size="18">FRONT (y=0) — {length:g} mm</text>',f'<text x="{x}" y="{y+width*scale+32}" font-family="sans-serif" font-size="18">BACK — {width:g} mm room depth</text>',f'<text x="80" y="680" font-family="sans-serif" font-size="16">Room height: {layout["height"]:g} mm · left x=0 · right x={length:g}</text>','<text x="80" y="710" font-family="sans-serif" font-size="15" fill="#e69840">Orange: doors</text><text x="260" y="710" font-family="sans-serif" font-size="15" fill="#2581b6">Blue: windows</text>','<text x="80" y="740" font-family="sans-serif" font-size="14">Offsets measured from x=0 on front/back, and y=0 on left/right.</text></svg>']
    return ''.join(pieces)


def render_room_layout():
    st.header('1. Prepare the room layout')
    st.caption('Enter measured rectangular room dimensions and openings. Confirm this plan before placing units. Irregular room outlines and service points are not supported yet.')
    a,b,c=st.columns(3)
    length=a.number_input('Room length — x (mm)',min_value=500.0,value=3000.0,step=10.0,key='design_room_length')
    width=b.number_input('Room depth — y (mm)',min_value=500.0,value=3000.0,step=10.0,key='design_room_width')
    height=c.number_input('Room height (mm)',min_value=1000.0,value=2400.0,step=10.0,key='design_room_height')
    defaults=st.session_state.get('_job_room_openings',[])
    openings=st.data_editor(pd.DataFrame(defaults,columns=OPENING_COLUMNS),num_rows='dynamic',hide_index=True,key='design_openings_editor',column_config={
        'Type':st.column_config.SelectboxColumn(options=['Door','Window'],required=True),
        'Wall':st.column_config.SelectboxColumn(options=['Front','Back','Left','Right'],required=True),
        **{name:st.column_config.NumberColumn(min_value=0,required=True) for name in OPENING_COLUMNS[2:]}})
    st.caption('Door sill normally 0. Window sill is its height above the floor. No openings are assumed; add all actual doors and windows.')
    try:
        layout=validate_layout(length,width,height,openings.to_dict(orient='records'))
    except (ValueError,TypeError,KeyError) as error:
        st.error(str(error));return None
    signature=hashlib.sha256(json.dumps(layout,sort_keys=True).encode()).hexdigest()
    st.image(plan_svg(layout),width='stretch')
    st.download_button('Download room layout SVG',plan_svg(layout),'room_layout.svg','image/svg+xml')
    confirmed=st.session_state.get('design_layout_signature')==signature
    if not confirmed:
        st.info('Review and confirm this room layout to unlock unit placement.')
    if st.button('Confirm room layout',key='confirm_room_layout'):
        st.session_state['design_layout_signature']=signature
        st.session_state['_job_layout']=layout
        st.rerun()
    if not confirmed:return None
    st.session_state['_job_layout']=layout
    st.success('Room layout confirmed. Unit placement is unlocked.')
    return layout

SCENE_COLUMNS=['Name','Type','Width (mm)','Height (mm)','Depth (mm)','X (mm)','Y (mm)','Z (mm)','Rotation (deg)','Shelves']


def scene_boxes(rows,layout,thickness,clearance,door_thickness,opened,floor=False):
    if not rows:raise ValueError('Add at least one design item.')
    if len(rows)>30:raise ValueError('Use at most 30 design items in this prototype.')
    boxes=[]
    for row in rows:
        if not isinstance(row['Name'],str) or not row['Name'].strip():raise ValueError('Every item needs a name.')
        kind=row['Type']
        if kind not in ALL_TYPES:raise ValueError('Choose a supported item type.')
        w,h,d,x,y,z,angle=(float(row[k]) for k in SCENE_COLUMNS[2:9])
        shelves=float(row['Shelves'])
        if not all(math.isfinite(v) for v in (w,h,d,x,y,z,angle,shelves)) or min(w,h,d)<=0 or z<0 or h+z>layout['height'] or shelves<0 or shelves>20 or not shelves.is_integer():raise ValueError('Item dimensions, height and shelf count must be valid for the room.')
        if kind in (*BASE_TYPES,'Wardrobe'):
            local=unit_geometry(kind,w,h,d,thickness,int(shelves),clearance,door_thickness,opened)
            if kind=='Wardrobe':
                local=[b for b in local if b.name not in ('Front top rail','Rear top rail')]
                local.append(Box('Full top',(thickness,0,h-thickness),(w-2*thickness,d,thickness)))
        else:local=[Box(kind,(0,0,0),(w,d,h),'appliance' if kind=='Appliance' else 'panel')]
        theta=math.radians(angle)
        placed=[]
        for box in local:
            a,b,c=box.origin
            origin=(x+a*math.cos(theta)-b*math.sin(theta),y+a*math.sin(theta)+b*math.cos(theta),z+c)
            placed.append(Box(str(row['Name'])+' — '+box.name,origin,box.size,box.kind,box.angle+angle))
        # Check carcass footprints against room bounds; door reveals may project outward a few mm.
        closed=unit_geometry(kind,w,h,d,thickness,int(shelves),clearance,door_thickness,False) if kind in BASE_TYPES else local
        footprints=[Box(b.name,(x+b.origin[0]*math.cos(theta)-b.origin[1]*math.sin(theta),y+b.origin[0]*math.sin(theta)+b.origin[1]*math.cos(theta),z+b.origin[2]),b.size,b.kind,b.angle+angle) for b in closed]
        points=__import__('numpy').vstack([b.vertices() for b in footprints if b.kind!='door'])
        if points[:,0].min() < -3.1 or points[:,1].min() < -3.1 or points[:,0].max()>layout['length']+3.1 or points[:,1].max()>layout['width']+3.1:
            raise ValueError(str(row['Name'])+' is outside the room. Adjust its position, rotation or dimensions.')
        boxes.extend(placed)
    if floor:boxes.insert(0,Box('Room floor',(0,0,-20),(layout['length'],layout['width'],20),'floor'))
    return boxes


def current_scene_rows():
    rows=st.session_state.get('_job_scene_rows',[])
    current=pd.DataFrame(rows,columns=SCENE_COLUMNS)
    editor=st.session_state.get('design_scene_editor',{})
    for i,changes in editor.get('edited_rows',{}).items():
        for col,value in changes.items():current.loc[int(i),col]=value
    if editor.get('deleted_rows'):current=current.drop(editor['deleted_rows'],errors='ignore')
    if editor.get('added_rows'):current=pd.concat([current,pd.DataFrame(editor['added_rows'])],ignore_index=True)
    return current.to_dict(orient='records')


def commit_scene(rows):
    st.session_state['_job_scene_rows']=rows
    st.session_state.pop('design_scene_editor',None)
    st.rerun()


def render_scene_editor(layout,width,height,depth):
    st.subheader('2. Unit library and placement')
    st.caption('Choose a unit from the library and add it. New units go in the next free space instead of stacking at the same position. Edit positions and rotation below. Library units are presentation models; current quotes still cover the configured base unit times its quantity.')
    current=current_scene_rows()
    with st.expander('Base unit library',expanded=True):
        selected=st.selectbox('Library unit',list(LIBRARY),key='library_selection')
        spec=LIBRARY[selected]
        st.caption(spec['description'])
        a,b,c=st.columns(3)
        w=a.number_input('Library width (mm)',min_value=150.0,max_value=2400.0,value=float(spec['width']),step=50.0,key='library_width_'+selected)
        h=b.number_input('Library height (mm)',min_value=200.0,max_value=2400.0,value=720.0,step=10.0,key='library_height')
        d=c.number_input('Library depth (mm)',min_value=200.0,max_value=1200.0,value=500.0,step=10.0,key='library_depth')
        from rendering import sketch_svg
        try:
            st.image(sketch_svg(unit_geometry(selected,w,h,d,float(st.session_state.get('job_thickness',18)),spec['shelves'],0,float(st.session_state.get('job_door_thickness',18)))),width=240)
        except ValueError as error:st.warning(str(error))
        if st.button('Add library unit',key='add_library_unit'):
            try:
                if len(current)>=30:raise ValueError('Use at most 30 units.')
                commit_scene(current+[library_row(selected,w,h,d,current,layout)])
            except ValueError as error:st.error(str(error))
    template=st.selectbox('Other design item',['Kitchen','Wardrobe','TV unit','Custom'],key='design_template')
    pending=st.session_state.get('_job_import_units',[])
    if pending:
        st.caption(f'{len(pending)} reviewed plan items ready to add.')
        if st.button('Add reviewed plan items to layout',key='add_reviewed_plan_items'):
            try:
                planned=list(current)
                if len(planned)+len(pending)>30:raise ValueError('Use at most 30 units.')
                for item in pending:
                    item=dict(item)
                    x,y=next_position(planned,float(item['Width (mm)']),float(item['Depth (mm)']),layout)
                    item.update({'X (mm)':x,'Y (mm)':y})
                    planned.append(item)
                st.session_state['_job_import_units']=[]
                commit_scene(planned)
            except ValueError as error:st.error(str(error))
    if st.button('Add design item',key='add_design_item'):
        try:
            if len(current)>=30:raise ValueError('Use at most 30 units.')
            row=dict(zip(SCENE_COLUMNS,[f'Unit {len(current)+1}','Base cabinet',width,height,depth,0,0,0,0,1]))
            if template=='Wardrobe':row.update({'Type':'Wardrobe','Height (mm)':min(2100,layout['height']),'Depth (mm)':600,'Shelves':4})
            if template=='TV unit':row.update({'Name':'TV base','Width (mm)':1200,'Height (mm)':450,'Depth (mm)':400})
            if template=='Custom':row.update({'Type':'Panel','Height (mm)':18,'Shelves':0})
            x,y=next_position(current,float(row['Width (mm)']),float(row['Depth (mm)']),layout)
            row.update({'X (mm)':x,'Y (mm)':y})
            commit_scene(current+[row])
        except ValueError as error:st.error(str(error))
    edited=st.data_editor(pd.DataFrame(st.session_state.get('_job_scene_rows',[]),columns=SCENE_COLUMNS),num_rows='dynamic',hide_index=True,key='design_scene_editor',column_config={
       'Type':st.column_config.SelectboxColumn(options=list(ALL_TYPES),required=True),
       **{c:st.column_config.NumberColumn(required=True) for c in SCENE_COLUMNS[2:]}})
    rows=edited.to_dict(orient='records')
    st.caption(f'{len(rows)} units in the design. X runs left to right; Y runs front to back. Rotation is around each unit’s local corner. Adjacent units may touch; check working aisles and opening clearances.')
    from design_assistant import render_assistant
    render_assistant(layout,rows)
    return rows


def scene_preview(rows,layout,thickness,clearance,door_thickness,opened,floor=False):
    """A bad editor row must not hide the rest of the kitchen."""
    boxes=[];warnings=[];footprints=[];valid=[]
    for index,row in enumerate(rows[:30]):
        try:
            placed=scene_boxes([row],layout,thickness,clearance,door_thickness,opened)
            boxes.extend(placed);valid.append(row)
            points=__import__('numpy').vstack([b.vertices() for b in scene_boxes([row],layout,thickness,clearance,door_thickness,False) if b.kind!='door'])
            footprints.append((index,str(row['Name']),points.min(axis=0),points.max(axis=0)))
        except (ValueError,TypeError,KeyError,OverflowError) as error:
            warnings.append(f'Row {index+1} ({row.get("Name") or "unnamed"}): {error}')
    for i,(index,name,low,high) in enumerate(footprints):
        for _,other,lo,hi in footprints[i+1:]:
            if all(min(high[k],hi[k])-max(low[k],lo[k])>3.1 for k in range(3)):
                warnings.append(f'{name} overlaps {other}. Move a unit to see both clearly. Rotated footprints use a conservative bounds check.')
    if len(rows)>30:warnings.append('Only the first 30 units are previewed.')
    if floor and boxes:boxes.insert(0,Box('Room floor',(0,0,-20),(layout['length'],layout['width'],20),'floor'))
    return boxes,warnings,valid
