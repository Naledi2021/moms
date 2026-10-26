"""Human-reviewed conversion from OCR annotations to editable room geometry."""
import hashlib
import json
import pandas as pd
import streamlit as st
from plan_import import single_measurements,reviewed_room
from room_actions import editor_rows
from room_geometry import WALL_COLUMNS

COLUMNS=['Type','Wall','Offset (mm)','Width (mm)','Height (mm)','Sill (mm)']


def render_plan_layout(draft,text):
    st.subheader('Build an editable room from this plan')
    st.caption('Text reading alone does not place geometry. Assign annotations to the room and openings below. Drawing position, door height and window sill cannot be determined reliably from OCR text; confirm them from the plan or site measurements. X starts at the left; Y starts at the front/top of the plan.')
    if st.session_state.get('_plan_layout_digest')!=draft['digest']:
        st.session_state['_plan_layout_digest']=draft['digest']
        st.session_state['_plan_layout_openings']=[]
        for key in list(st.session_state):
            if key.startswith('plan_room_') or key.startswith('plan_opening_') or key in ('plan_layout_editor','plan_geometry_verified'):st.session_state.pop(key,None)
    annotations=single_measurements(text)
    if annotations:st.caption('Found '+str(len(annotations))+' individual dimensions, including annotations not written as width × depth.')
    def dimension(label,key,minimum):
        pick=st.selectbox(label+' annotation',[None,*range(len(annotations))],format_func=lambda i:'Enter measured value manually' if i is None else annotations[i]['annotation']+' · '+annotations[i]['context'],key=key+'_source')
        # A source-specific widget retains manual corrections without stale values from a different annotation.
        return st.number_input(label+' (mm)',min_value=float(minimum),value=None if pick is None else float(annotations[pick]['mm']),step=1.,key=key+'_'+str(pick)+'_'+hashlib.sha256(text.encode()).hexdigest()[:10])
    a,b,c=st.columns(3)
    with a:length=dimension('Plan room length','plan_room_length',1)
    with b:depth=dimension('Plan room depth','plan_room_depth',1)
    with c:height=st.number_input('Plan room height (mm)',min_value=1000.,value=None,step=1.,key='plan_room_height',help='Enter the measured ceiling height; a floor plan usually does not show it.')
    with st.expander('Add a door or window from the plan',expanded=True):
        a,b=st.columns(2)
        kind=a.selectbox('Plan opening type',['Door','Window'],key='plan_opening_type')
        wall=b.selectbox('Plan opening wall',['Front','Back','Left','Right'],key='plan_opening_wall')
        width=dimension('Plan opening width','plan_opening_width',1)
        a,b,c=st.columns(3)
        offset=a.number_input('Plan opening offset (mm)',min_value=0.,value=None,key='plan_opening_offset',help='Distance from x=0 on Front/Back, or y=0 on Left/Right. This is not inferred from OCR order.')
        opening_height=b.number_input('Plan opening height (mm)',min_value=1.,value=None,key='plan_opening_height')
        sill=0. if kind=='Door' else c.number_input('Plan window sill above floor (mm)',min_value=0.,value=None,key='plan_opening_sill')
        if st.button('Stage opening from plan',key='plan_stage_opening'):
            if any(value is None for value in (width,offset,opening_height,sill)):st.error('Enter width, offset, height and window sill before staging this opening.')
            else:
                pending=editor_rows(st.session_state.get('_plan_layout_openings',[]),COLUMNS,st.session_state.get('plan_layout_editor',{}))
                pending.append(dict(zip(COLUMNS,[kind,wall,offset,width,opening_height,sill])))
                st.session_state['_plan_layout_openings']=pending;st.session_state.pop('plan_layout_editor',None)
                st.success('Opening staged. Review its row below.')
    st.caption('Reviewed plan openings — edit or remove rows here before applying. Door sills must be 0. Window height is separate from sill height.')
    opening_frame=st.data_editor(pd.DataFrame(st.session_state.get('_plan_layout_openings',[]),columns=COLUMNS),key='plan_layout_editor',hide_index=True,num_rows='dynamic',column_config={'Type':st.column_config.SelectboxColumn(options=['Door','Window'],required=True),'Wall':st.column_config.SelectboxColumn(options=['Front','Back','Left','Right'],required=True)})
    openings=opening_frame.to_dict(orient='records')
    replace=st.checkbox('Replace existing room doors and windows with these reviewed openings',key='plan_room_replace_openings',help='Otherwise new openings are added to existing ones. Existing cabinets and internal walls are retained.')
    def stable(value):
        if isinstance(value,bool) or value is None:return value
        if isinstance(value,(int,float)):return float(value)
        if isinstance(value,dict):return {k:stable(v) for k,v in value.items()}
        if isinstance(value,list):return [stable(v) for v in value]
        return value
    context=json.dumps(stable([draft['digest'],text,length,depth,height,openings,replace]),sort_keys=True,default=str)
    token=hashlib.sha256(context.encode()).hexdigest()[:16]
    verified=st.checkbox('I checked the room dimensions, opening positions, heights and sill levels against the original',key='plan_geometry_verified_'+token)
    if st.button('Create editable room from reviewed plan',key='plan_create_room',type='primary',disabled=not verified):
        try:
            if any(v is None for v in (length,depth,height)):raise ValueError('Enter room length, depth and measured ceiling height.')
            from layout_ui import OPENING_COLUMNS
            old=editor_rows(st.session_state.get('_job_room_openings',[]),OPENING_COLUMNS,st.session_state.get('design_openings_editor',{}))
            walls=editor_rows(st.session_state.get('_job_walls',[]),WALL_COLUMNS+['Locked'],st.session_state.get('design_walls_editor',{}))
            merged=openings if replace else old+[o for o in openings if o not in old]
            room=reviewed_room({'wall_thickness':st.session_state.get('design_wall_thickness',110)},length,depth,height,merged,walls,st.session_state.get('_design_lock'))
            st.session_state.update(design_room_length=float(length),design_room_width=float(depth),design_room_height=float(height),_job_room_openings=room['openings'],_job_walls=room['walls'])
            st.session_state['_job_plan_import']={'filename':draft['filename'],'text':text,'purpose':'Reviewed room layout','confirmed_unit':'mm','reviewed_layout':room}
            for key in ('design_openings_editor','design_walls_editor','design_layout_signature'):st.session_state.pop(key,None)
            st.success('Editable room created below, including reviewed doors and windows. Confirm room layout to start placing cabinets. Existing cabinets retain their positions; review warnings if the room changed.')
            from layout_ui import plan_svg
            st.image(plan_svg(room),width='stretch')
        except (ValueError,KeyError,TypeError) as error:st.error(str(error))
