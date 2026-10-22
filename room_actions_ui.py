import streamlit as st
from room_actions import add_feature,editor_rows
from room_geometry import WALL_COLUMNS

OPENING_COLUMNS=['Type','Wall','Offset (mm)','Width (mm)','Height (mm)','Sill (mm)']


def render_add_room_feature(layout):
    st.subheader('Add room features')
    kind=st.radio('What would you like to add?',['Wall','Window','Door'],horizontal=True,key='room_feature_kind')
    with st.form('room_feature_form_'+kind):
        if kind=='Wall':
            st.caption(f"Add a partition or return within the measured room. It uses the room height of {layout['height']:g} mm. The four outer walls are already defined by Room length and Room depth above.")
            name=st.text_input('Wall name (optional)',key='room_feature_wall_name')
            a,b=st.columns(2)
            x=a.number_input('Wall start X (mm)',min_value=0.,value=min(500.,layout['length']/4),step=1.,key='room_feature_wall_x')
            y=b.number_input('Wall start Y (mm)',min_value=0.,value=min(500.,layout['width']/4),step=1.,key='room_feature_wall_y')
            length=a.number_input('Wall length (mm)',min_value=50.,value=min(1000.,layout['length']/2),step=1.,key='room_feature_wall_length')
            direction=b.selectbox('Wall direction',['Right (+X)','Back (+Y)','Left (−X)','Front (−Y)'],key='room_feature_wall_direction')
            thickness=st.number_input('New wall thickness (mm)',min_value=20.,max_value=500.,value=float(layout['wall_thickness']),step=1.,key='room_feature_wall_thickness')
            locked=st.checkbox('Keep new wall locked',value=True,key='room_feature_wall_locked')
            values=dict(locked=locked,name=name,x=x,y=y,length=length,angle={'Right (+X)':0,'Back (+Y)':90,'Left (−X)':180,'Front (−Y)':270}[direction],thickness=thickness)
        else:
            st.caption(f'Place this {kind.lower()} on an outer room wall. Opening length is its width along that wall. Offsets start at x=0 on Front/Back and y=0 on Left/Right. Openings in drawn partitions are not supported yet.')
            wall=st.selectbox('Opening wall',['Front','Back','Left','Right'],key='room_feature_'+kind+'_wall')
            a,b=st.columns(2)
            offset=a.number_input('Opening offset along wall (mm)',min_value=0.,value=0.,step=1.,key='room_feature_'+kind+'_offset')
            length=b.number_input(kind+' width / opening length (mm)',min_value=1.,value=min(900.,layout['length']/2,layout['width']/2),step=1.,key='room_feature_'+kind+'_length')
            height=a.number_input(kind+' height (mm)',min_value=1.,value=min(900.,layout['height']/2) if kind=='Window' else min(2100.,layout['height']),step=1.,key='room_feature_'+kind+'_height')
            sill=b.number_input('Window sill above floor (mm)',min_value=0.,value=min(900.,layout['height']/2),step=1.,key='room_feature_Window_sill') if kind=='Window' else 0.
            values=dict(wall=wall,offset=offset,length=length,height=height,sill=sill)
        submitted=st.form_submit_button('Add '+kind.lower(),key='add_room_'+kind.lower())
    if submitted:
        try:
            current=editor_rows(st.session_state.get('_job_room_openings',[]),OPENING_COLUMNS,st.session_state.get('design_openings_editor',{}))
            walls=editor_rows(st.session_state.get('_job_walls',[]),WALL_COLUMNS+['Locked'],st.session_state.get('design_walls_editor',{}))
            openings,walls=add_feature(layout,current,walls,kind,values,st.session_state.get('_design_lock'))
            st.session_state['_job_room_openings']=openings;st.session_state['_job_walls']=walls
            st.session_state.pop('design_openings_editor',None);st.session_state.pop('design_walls_editor',None)
            st.session_state.pop('design_layout_signature',None)
            st.session_state['_room_feature_message']=kind+' added. Review the plan and confirm the room layout.'
            st.rerun()
        except (ValueError,KeyError,TypeError) as error:st.error(str(error))
    if st.session_state.get('_room_feature_message'):st.success(st.session_state.pop('_room_feature_message'))
