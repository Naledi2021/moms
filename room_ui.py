import hashlib
import json
import pandas as pd
import streamlit as st
from room_geometry import WALL_COLUMNS,validate_walls


def render_wall_editor(layout):
    with st.expander('Draw walls and edit wall measurements'):
        st.caption('The measured rectangle remains the room boundary. Draw internal partitions or returns by clicking two endpoints. Wall thickness is centred on each drawn line. Delete or adjust segments in the table. Custom enclosed room outlines and openings in drawn partitions are not supported yet.')
        edited=st.data_editor(pd.DataFrame(st.session_state.get('_job_walls',[]),columns=WALL_COLUMNS),hide_index=True,num_rows='dynamic',key='design_walls_editor',column_config={k:st.column_config.NumberColumn(required=True) for k in WALL_COLUMNS[1:]})
        walls=edited.to_dict(orient='records')
        validate_walls(walls,layout)
        room=dict(layout,walls=walls)
        revision=hashlib.sha256(json.dumps(room,sort_keys=True,allow_nan=False).encode()).hexdigest()
        from designer_ui import _canvas
        event=_canvas(layout=room,units=[],library={},selected=None,revision=revision,locked=False,mode='walls',ack=st.session_state.get('_wall_event'),default=None,key='room_wall_canvas')
        if isinstance(event,dict) and event.get('id')!=st.session_state.get('_wall_event'):
            st.session_state['_wall_event']=event.get('id')
            try:
                if event.get('revision')!=revision:raise ValueError('The room changed. Draw this wall again.')
                if event.get('action')!='wall_add':raise ValueError('Choose the wall drawing tool.')
                from designer_geometry import require_unlocked
                require_unlocked(st.session_state.get('_design_lock'))
                row={'Name':f'Wall {len(walls)+1}','Start X (mm)':round(float(event['x1']),1),'Start Y (mm)':round(float(event['y1']),1),'End X (mm)':round(float(event['x2']),1),'End Y (mm)':round(float(event['y2']),1),'Thickness (mm)':layout['wall_thickness']}
                validate_walls(walls+[row],layout)
                st.session_state['_job_walls']=walls+[row]
                st.session_state.pop('design_walls_editor',None)
                st.session_state.pop('design_layout_signature',None)
                st.rerun()
            except (ValueError,KeyError,TypeError) as error:st.error(str(error))
        return walls
