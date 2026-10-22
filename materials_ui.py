import json
import streamlit as st
from materials import load_materials,save_material,restore_material_library,CATEGORIES


def render_material_library():
    with st.expander('Material library — boards, fronts and worktops'):
        data=load_materials();records=data['materials']
        st.caption('Reusable business materials. Starter entries are illustrative colours, not verified supplier products. Prices are optional R/m² excluding VAT; selecting a finish does not automatically price the whole design.')
        pick=st.selectbox('Create or edit material',['New material']+[r['id'] for r in records],format_func=lambda k:k if k=='New material' else next(r['name']+' · '+r['category'] for r in records if r['id']==k),key='material_pick')
        current={} if pick=='New material' else next(r for r in records if r['id']==pick)
        with st.form('material_form_'+pick):
            name=st.text_input('Material name',value=current.get('name',''))
            category=st.selectbox('Material category',CATEGORIES,index=CATEGORIES.index(current.get('category','Carcass')))
            thickness=st.number_input('Material thickness (mm)',min_value=.1,max_value=200.,value=float(current.get('thickness_mm',18)))
            color=st.color_picker('Material colour',value=current.get('color','#eeeae2'))
            finish=st.selectbox('Surface finish',['Matte','Gloss','Wood grain'],index=['Matte','Gloss','Wood grain'].index(current.get('finish','Matte')))
            supplier=st.text_input('Material supplier / range',value=current.get('supplier',''))
            price=st.number_input('Optional material price (R/m² excluding VAT)',min_value=0.,value=current.get('price_m2'))
            save=st.form_submit_button('Save material to library')
        if save:
            try:
                record=dict(name=name,category=category,thickness_mm=thickness,color=color,finish=finish,supplier=supplier,price_m2=price)
                if current:record['id']=current['id']
                save_material(record);st.rerun()
            except ValueError as error:st.error(str(error))
        st.dataframe(records,hide_index=True)
        st.download_button('Download material library backup',json.dumps(data,indent=2),'materials.json','application/json')

        backup=st.file_uploader('Restore material library JSON',type=['json'],key='material_library_backup')
        if st.button('Restore material library',disabled=backup is None,key='restore_material_library'):
            try:
                restore_material_library(backup.getvalue());st.rerun()
            except (ValueError,KeyError,TypeError) as error:st.error(str(error))
