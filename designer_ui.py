"""Stable Streamlit component bridge. Only validated Python state is persisted."""
from pathlib import Path
import math
import streamlit as st
import streamlit.components.v1 as components
from designer_geometry import (fingerprint,validate_unit,apply_event,collision_warnings,along_wall,require_unlocked)

_canvas=components.declare_component('mkp_designer2d',path=str(Path(__file__).with_name('components')/'designer2d'))


def render_designer(layout,rows):
    st.subheader('Interactive 2D floor plan')
    lock=st.session_state.get('_design_lock')
    if lock:layout=lock['layout'];rows=lock['rows']
    warnings=collision_warnings(rows,layout)
    for warning in warnings:st.warning(warning)
    st.caption('Drag units; select and rotate or delete with the canvas buttons. Use the precise editor for millimetres, elevation and wall offsets. Door zones reserve up to 1 m inward; windows use a 100 mm wall strip and their actual elevation. These are clearance warnings, not a door-swing simulation.')
    snapping=st.checkbox('Snap to walls and adjacent units (20 mm)',value=True,key='designer_snap',disabled=bool(lock))
    valid=[]
    for i,row in enumerate(rows):
        try:validate_unit(row,layout);valid.append({'index':i,'row':row})
        except ValueError:continue
    try:revision=fingerprint(layout,rows)
    except ValueError:
        st.info('Complete non-finite table measurements to enable the interactive canvas.')
        return rows
    import json
    st.download_button('Export 2D design and approval JSON',json.dumps({'schema_version':1,'layout':layout,'units':rows,'approval':lock},indent=2,allow_nan=False),'kitchen_design_2d.json','application/json')
    selected=st.session_state.get('_designer_selected')
    if selected is not None and not 0<=selected<len(rows):selected=None
    event=_canvas(layout=layout,units=valid,selected=selected,revision=revision,locked=bool(lock),ack=st.session_state.get('_designer_event'),default=None,key='designer_canvas')
    if event and isinstance(event,dict) and event.get('id')!=st.session_state.get('_designer_event'):
        st.session_state['_designer_event']=event.get('id')
        try:
            index=event.get('index')
            if event.get('revision')!=revision:raise ValueError('The canvas changed. Please select the unit again.')
            if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(rows):raise ValueError('Select a current unit.')
            st.session_state['_designer_selected']=index
            st.session_state['unit_pick_'+revision[:12]]=index
            if event.get('action')!='select':
                updated=apply_event(rows,layout,event,lock,snapping)
                if event.get('action')=='delete':st.session_state['_designer_selected']=None
                from layout_ui import commit_scene
                commit_scene(updated)
            st.rerun()
        except (ValueError,KeyError,TypeError) as error:
            st.session_state['_designer_feedback']=str(error)
            st.rerun()
    if st.session_state.get('_designer_feedback'):st.error(st.session_state.pop('_designer_feedback'))
    if not rows:return rows
    chosen=st.selectbox('Selected unit',range(len(rows)),index=selected or 0,format_func=lambda i:f'{i+1}: {rows[i].get("Name", "Unnamed")}',key='unit_pick_'+revision[:12])
    if chosen!=selected:
        st.session_state['_designer_selected']=chosen
        st.rerun()
    row=rows[chosen]
    # Invalid rows remain repairable in the placement table.
    try:
        numbers={k:float(row[k]) for k in ('Width (mm)','Height (mm)','Depth (mm)','X (mm)','Y (mm)','Z (mm)','Rotation (deg)')}
        if not all(math.isfinite(v) for v in numbers.values()):return rows
    except (TypeError,ValueError,KeyError):return rows
    with st.expander('Precise unit dimensions and placement',expanded=True):
        with st.form('unit_details_'+revision[:12]):
            name=st.text_input('Unit name',value=row['Name'],disabled=bool(lock))
            cols=st.columns(3);values={}
            for i,(key,value) in enumerate(numbers.items()):
                values[key]=cols[i%3].number_input(key,value=value,step=1.0,format='%.2f',disabled=bool(lock))
            submitted=st.form_submit_button('Apply precise dimensions',disabled=bool(lock))
        if submitted:
            try:
                require_unlocked(lock)
                replacement=dict(row,Name=name,**values);validate_unit(replacement,layout)
                updated=list(rows);updated[chosen]=replacement
                from layout_ui import commit_scene
                commit_scene(updated)
            except ValueError as error:st.error(str(error))
        with st.form('wall_placement_'+revision[:12]):
            wall=st.selectbox('Place against wall',['Front','Back','Left','Right'],disabled=bool(lock))
            offset=st.number_input('Offset along wall (mm)',min_value=0.0,value=0.0,step=1.0,disabled=bool(lock))
            wall_submitted=st.form_submit_button('Place along wall',disabled=bool(lock))
        if wall_submitted:
            try:
                require_unlocked(lock);replacement=along_wall(row,wall,offset,layout)
                updated=list(rows);updated[chosen]=replacement
                from layout_ui import commit_scene
                commit_scene(updated)
            except ValueError as error:st.error(str(error))
    return rows
