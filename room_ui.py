import hashlib
import json
import math
from copy import deepcopy
import streamlit as st
from room_geometry import WALL_COLUMNS,validate_walls


def render_wall_editor(layout):
    with st.expander('Draw walls and edit wall measurements',expanded=True,key='wall_editor_open',on_change='rerun'):
        st.caption('Select a wall on the plan or by name. Correct its start position, length and direction below, then Apply position. The wall locks again after a measured correction. Unlock only when you want to drag it or its endpoints.')
        base=st.session_state.get('_job_walls',[])
        # Keep the legacy editor state compatible with saved sessions.
        from room_actions import editor_rows
        walls=editor_rows(base,WALL_COLUMNS+['Locked'],st.session_state.get('design_walls_editor',{}))
        def persist(updated,remember=True):
            from designer_geometry import require_unlocked
            require_unlocked(st.session_state.get('_design_lock'))
            validate_walls(updated,layout)
            if remember:st.session_state['_wall_undo']={'before':deepcopy(walls),'after':deepcopy(updated)}
            st.session_state['_job_walls']=updated
            st.session_state.pop('design_walls_editor',None);st.session_state.pop('design_layout_signature',None)
            st.session_state['_wall_notice']='Wall updated. Review the plan and confirm the room layout.'
        undo=st.session_state.get('_wall_undo')
        if st.button('Undo last wall change',key='undo_wall_change',disabled=not undo or undo.get('after')!=walls):
            try:
                persist(undo['before'],remember=False);st.session_state.pop('_wall_undo',None);st.rerun()
            except ValueError as error:st.error(str(error))
        if st.session_state.get('_wall_notice'):st.success(st.session_state.pop('_wall_notice'))
        controls,plan=st.columns([1,1.7],gap='large')
        with controls:
            if walls:
                if '_wall_pick_pending' in st.session_state:st.session_state['wall_detail_pick']=st.session_state.pop('_wall_pick_pending')
                if st.session_state.get('wall_detail_pick',0)>=len(walls):st.session_state['wall_detail_pick']=0
                chosen=st.selectbox('Wall to edit',range(len(walls)),format_func=lambda i:f'{i+1}: {walls[i]["Name"]}',key='wall_detail_pick')
                selected=walls[chosen];blocked=selected.get('Locked',True)
                def toggle_lock():
                    from designer_geometry import require_unlocked
                    require_unlocked(st.session_state.get('_design_lock'))
                    updated=[dict(w) for w in walls];updated[chosen]['Locked']=not blocked
                    st.session_state['_job_walls']=updated
                    st.session_state.pop('design_walls_editor',None);st.session_state.pop('design_layout_signature',None)
                st.button('Unlock selected wall' if blocked else 'Lock selected wall',key='toggle_wall_lock',on_click=toggle_lock)
                dx=float(selected['End X (mm)'])-float(selected['Start X (mm)'])
                dy=float(selected['End Y (mm)'])-float(selected['Start Y (mm)'])
                tag=hashlib.sha256(json.dumps(selected,sort_keys=True).encode()).hexdigest()[:12]
                with st.form('wall_position_'+str(chosen)+'_'+tag):
                    st.markdown('**Correct wall position**')
                    c=st.columns(2)
                    x=c[0].number_input('Position X (mm)',value=float(selected['Start X (mm)']),step=10.)
                    y=c[1].number_input('Position Y (mm)',value=float(selected['Start Y (mm)']),step=10.)
                    length=c[0].number_input('Selected wall length (mm)',min_value=50.,value=math.hypot(dx,dy),step=10.)
                    angle=c[1].number_input('Wall direction (degrees)',value=math.degrees(math.atan2(dy,dx)),step=90.)
                    st.caption('0° = right · 90° = back · 180° = left · −90° = front. Moving the start point keeps the length and direction.')
                    correct=st.form_submit_button('Apply position and lock wall',type='primary')
                if correct:
                    try:
                        from room_actions import correct_wall
                        persist(correct_wall(layout,walls,chosen,x,y,length,angle,lock=st.session_state.get('_design_lock')))
                        st.rerun()
                    except (ValueError,TypeError) as error:st.error(str(error))
                with st.expander('Advanced endpoints, wall thickness and deletion'):
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
                                persist(updated)
                                st.rerun()
                            except (ValueError,TypeError,KeyError) as error:st.error(str(error))
        with plan:
            validate_walls(walls,layout)
            room=dict(layout,walls=walls)
            revision=hashlib.sha256(json.dumps(room,sort_keys=True,allow_nan=False).encode()).hexdigest()
            from designer_ui import _canvas
            event=_canvas(layout=room,units=[],library={},selected=st.session_state.get('wall_detail_pick'),revision=revision,locked=False,mode='walls',ack=st.session_state.get('_wall_event'),default=None,key='room_wall_canvas')
            if isinstance(event,dict) and event.get('id')!=st.session_state.get('_wall_event'):
                st.session_state['_wall_event']=event.get('id')
                try:
                    if event.get('revision')!=revision:raise ValueError('The room changed. Draw this wall again.')
                    if event.get('action') not in ('wall_add','wall_move','wall_start','wall_end','wall_select'):raise ValueError('Choose a wall action.')
                    from designer_geometry import require_unlocked
                    require_unlocked(st.session_state.get('_design_lock'))
                    if event['action']=='wall_select':
                        index=event.get('index')
                        if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(walls):raise ValueError('Select a current wall.')
                        st.session_state['_wall_pick_pending']=index;st.rerun()
                    if event.get('action')!='wall_add':
                        from room_actions import edit_wall
                        action=event['action'];position=(event.get('x'),event.get('y'))
                        updated=edit_wall(layout,walls,event.get('index'),start=position if action=='wall_start' else None,end=position if action=='wall_end' else None,delta=(event.get('dx'),event.get('dy')) if action=='wall_move' else None)
                        persist(updated)
                        st.rerun()
                    row={'Name':f'Wall {len(walls)+1}','Start X (mm)':round(float(event['x1']),1),'Start Y (mm)':round(float(event['y1']),1),'End X (mm)':round(float(event['x2']),1),'End Y (mm)':round(float(event['y2']),1),'Thickness (mm)':layout['wall_thickness'],'Locked':True}
                    validate_walls(walls+[row],layout)
                    persist(walls+[row])
                    st.rerun()
                except (ValueError,KeyError,TypeError) as error:st.error(str(error))
        st.caption('The rectangle is the clear room boundary. These walls are internal partitions or returns; openings in partitions and custom enclosed outlines are not supported yet.')
        return walls
