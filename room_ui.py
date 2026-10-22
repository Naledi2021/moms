import hashlib
import json
import pandas as pd
import streamlit as st
from room_geometry import WALL_COLUMNS,validate_walls


def render_wall_editor(layout):
    with st.expander('Draw walls and edit wall measurements',key='wall_editor_open',on_change='rerun'):
        st.caption('The measured rectangle remains the room boundary. Draw internal partitions or returns by clicking two endpoints. Wall thickness is centred on each drawn line. Unlock a wall to move it or edit its exact measurements; delete it using the detail controls. Custom enclosed room outlines and openings in drawn partitions are not supported yet.')
        base=st.session_state.get('_job_walls',[])
        frame=pd.DataFrame(base,columns=WALL_COLUMNS+['Locked'])
        frame['Locked']=frame['Locked'].fillna(True).astype(bool)
        st.caption('Walls are locked by default. Untick Locked to enable dragging the wall or either endpoint. Re-tick it when finished. Use the detail controls below for exact coordinates.')
        edited=st.data_editor(frame,hide_index=True,key='design_walls_editor',disabled=WALL_COLUMNS,column_config={'Locked':st.column_config.CheckboxColumn(required=True)})
        walls=edited.to_dict(orient='records')
        if walls:
            chosen=st.selectbox('Wall to edit',range(len(walls)),format_func=lambda i:f'{i+1}: {walls[i]["Name"]}',key='wall_detail_pick')
            selected=walls[chosen];blocked=selected.get('Locked',True)
            def toggle_lock():
                from designer_geometry import require_unlocked
                require_unlocked(st.session_state.get('_design_lock'))
                updated=[dict(w) for w in walls];updated[chosen]['Locked']=not blocked
                st.session_state['_job_walls']=updated
                st.session_state.pop('design_walls_editor',None);st.session_state.pop('design_layout_signature',None)
            st.button('Unlock selected wall' if blocked else 'Lock selected wall',key='toggle_wall_lock',on_click=toggle_lock)
            revision_key=hashlib.sha256(json.dumps(selected,sort_keys=True).encode()).hexdigest()[:12]
            with st.form('wall_detail_'+revision_key):
                name=st.text_input('Wall detail name',value=selected['Name'],disabled=blocked)
                vals={};columns=st.columns(2)
                for i,key in enumerate(WALL_COLUMNS[1:]):vals[key]=columns[i%2].number_input(key,value=float(selected[key]),step=1.,disabled=blocked)
                change=st.form_submit_button('Apply wall measurements',disabled=blocked)
                remove=st.form_submit_button('Delete selected wall',disabled=blocked)
            if change or remove:
                from designer_geometry import require_unlocked
                require_unlocked(st.session_state.get('_design_lock'))
                if blocked:st.error('Unlock this wall before editing it.')
                else:
                    updated=[dict(w) for w in walls]
                    if remove:updated.pop(chosen)
                    else:updated[chosen]=dict(selected,Name=name,**vals)
                    try:
                        validate_walls(updated,layout)
                        st.session_state['_job_walls']=updated
                        st.session_state.pop('design_walls_editor',None)
                        st.session_state.pop('design_layout_signature',None)
                        st.rerun()
                    except (ValueError,TypeError,KeyError) as error:st.error(str(error))
        validate_walls(walls,layout)
        room=dict(layout,walls=walls)
        revision=hashlib.sha256(json.dumps(room,sort_keys=True,allow_nan=False).encode()).hexdigest()
        from designer_ui import _canvas
        event=_canvas(layout=room,units=[],library={},selected=None,revision=revision,locked=False,mode='walls',ack=st.session_state.get('_wall_event'),default=None,key='room_wall_canvas')
        if isinstance(event,dict) and event.get('id')!=st.session_state.get('_wall_event'):
            st.session_state['_wall_event']=event.get('id')
            try:
                if event.get('revision')!=revision:raise ValueError('The room changed. Draw this wall again.')
                if event.get('action') not in ('wall_add','wall_move','wall_start','wall_end'):raise ValueError('Choose a wall action.')
                from designer_geometry import require_unlocked
                require_unlocked(st.session_state.get('_design_lock'))
                if event.get('action')!='wall_add':
                    from room_actions import edit_wall
                    action=event['action'];position=(event.get('x'),event.get('y'))
                    updated=edit_wall(layout,walls,event.get('index'),start=position if action=='wall_start' else None,end=position if action=='wall_end' else None,delta=(event.get('dx'),event.get('dy')) if action=='wall_move' else None)
                    st.session_state['_job_walls']=updated
                    st.session_state.pop('design_walls_editor',None);st.session_state.pop('design_layout_signature',None)
                    st.rerun()
                row={'Name':f'Wall {len(walls)+1}','Start X (mm)':round(float(event['x1']),1),'Start Y (mm)':round(float(event['y1']),1),'End X (mm)':round(float(event['x2']),1),'End Y (mm)':round(float(event['y2']),1),'Thickness (mm)':layout['wall_thickness'],'Locked':True}
                validate_walls(walls+[row],layout)
                st.session_state['_job_walls']=walls+[row]
                st.session_state.pop('design_walls_editor',None)
                st.session_state.pop('design_layout_signature',None)
                st.rerun()
            except (ValueError,KeyError,TypeError) as error:st.error(str(error))
        return walls
