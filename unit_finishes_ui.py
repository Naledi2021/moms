import json
import pandas as pd
import streamlit as st
from materials import details,load_materials
from room_geometry import RECT_COLUMNS,worktop_rectangles


def render_unit_finishes(layout,rows,index,lock):
    import hashlib
    tag=hashlib.sha256(repr(rows[index]).encode()).hexdigest()[:12]
    row=rows[index];meta=details(row);available=load_materials()['materials']
    with st.expander('Unit materials and custom worktop',expanded=row['Type']=='Worktop'):
        st.caption('Finish selections are saved with this unit. Existing designs retain their material record when the shared library changes. Colours affect presentation; construction thickness and prices are not changed automatically.')
        refresh=st.checkbox('Use latest library versions for this unit',key='refresh_materials_'+tag,disabled=bool(lock))
        roles=['Worktop'] if row['Type']=='Worktop' else ['Carcass','Front']
        selected={}
        for role in roles:
            records={r['id']:r for r in available if r['category']==role}
            old=meta.get('materials',{}).get(role)
            if old and (not refresh or old['id'] not in records):records[old['id']]=old
            keys=['']+list(records)
            choice=st.selectbox(role+' material for this unit',keys,index=keys.index(old['id']) if old and old['id'] in keys else 0,format_func=lambda key:'Use preview colour' if not key else records[key]['name'],key=f'finish_{role}_{tag}',disabled=bool(lock))
            if choice:selected[role]=records[choice]
        if st.button('Apply unit materials',key='apply_unit_materials',disabled=bool(lock)):
            from designer_geometry import require_unlocked
            require_unlocked(lock)
            updated=list(rows);config=dict(meta,materials=selected)
            updated[index]=dict(row,**{'Design details':json.dumps(config,sort_keys=True)})
            from layout_ui import commit_scene
            commit_scene(updated)
        if row['Type']!='Worktop':return
        st.caption('Define a custom top as a union of rectangular sections, including L and U shapes. Cut-outs are rectangular and use local coordinates before unit rotation. Width/depth above define the overall envelope. This is a design model, not a stone-fabrication template.')
        existing=meta.get('worktop',{})
        shape=st.selectbox('Worktop starting shape',['Rectangle','L shape','U shape','Custom sections'],key=f'worktop_shape_{tag}',disabled=bool(lock))
        w,d=float(row['Width (mm)']),float(row['Depth (mm)'])
        arm=st.number_input('Worktop arm depth (mm)',min_value=1.,value=max(1.,min(600.,w/3,d/2)),key=f'worktop_arm_{tag}',disabled=bool(lock))
        if st.button('Load worktop starting shape',disabled=bool(lock),key='load_worktop_shape'):
            from designer_geometry import require_unlocked
            require_unlocked(lock)
            a=arm
            if a>min(w,d):st.error('Arm depth must fit inside the worktop.');return
            if shape=='L shape' and a>=min(w,d) or shape=='U shape' and (2*a>=w or a>=d):st.error('Reduce arm depth to leave an open inner corner.');return
            sections=[dict(zip(RECT_COLUMNS,[0,0,w,d]))]
            if shape in ('L shape','U shape'):sections=[dict(zip(RECT_COLUMNS,[0,0,w,a])),dict(zip(RECT_COLUMNS,[0,0,a,d]))]
            if shape=='U shape':sections.append(dict(zip(RECT_COLUMNS,[w-a,0,a,d])))
            config=dict(meta,worktop={'sections':sections,'cutouts':existing.get('cutouts',[])})
            try:worktop_rectangles(w,d,config['worktop'])
            except ValueError as error:st.error(str(error));return
            changed=list(rows);changed[index]=dict(row,**{'Design details':json.dumps(config,sort_keys=True)})
            st.session_state.pop('worktop_sections_editor',None);st.session_state.pop('worktop_cutouts_editor',None)
            from layout_ui import commit_scene
            commit_scene(changed)
        base=existing.get('sections') or [dict(zip(RECT_COLUMNS,[0,0,w,d]))]
        sections=st.data_editor(pd.DataFrame(base,columns=RECT_COLUMNS),num_rows='dynamic',hide_index=True,key='worktop_sections_editor_'+tag,disabled=bool(lock))
        st.caption('Sink / hob cut-outs — local X and Y, width and depth in mm.')
        holes=st.data_editor(pd.DataFrame(existing.get('cutouts',[]),columns=RECT_COLUMNS),num_rows='dynamic',hide_index=True,key='worktop_cutouts_editor_'+tag,disabled=bool(lock))
        if st.button('Apply custom worktop sections and cut-outs',key='apply_custom_worktop',disabled=bool(lock)):
            try:
                from designer_geometry import require_unlocked
                require_unlocked(lock)
                config={'sections':sections.to_dict(orient='records'),'cutouts':holes.to_dict(orient='records')}
                tiles=worktop_rectangles(w,d,config)
                changed=list(rows);changed[index]=dict(row,**{'Design details':json.dumps(dict(meta,worktop=config),sort_keys=True)})
                from layout_ui import commit_scene
                commit_scene(changed)
            except (ValueError,TypeError,KeyError) as error:st.error(str(error))
        try:
            tiles=worktop_rectangles(w,d,existing)
            area=sum((x2-x1)*(y2-y1) for x1,y1,x2,y2 in tiles)/1e6
            st.write(f'Net worktop plan area: {area:.3f} m²')
            material=meta.get('materials',{}).get('Worktop',{})
            if material.get('price_m2') is not None:st.caption(f"Area × material rate only: R {area*material['price_m2']:,.2f} excluding VAT. Excludes waste, slabs, joints, edge profiles, fabrication and installation; not included in the base-unit quote.")
        except ValueError as error:st.error(str(error))
