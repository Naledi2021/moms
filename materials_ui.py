import json
import streamlit as st
from materials import load_materials,save_material,restore_material_library,CATEGORIES,starter_products


def render_material_library():
    with st.expander('Materials and fixtures library'):
        data=load_materials();records=data['materials']
        st.caption('Reusable business materials. Starter entries are illustrative colours, not verified supplier products. Prices are optional R/m² or R/item excluding VAT; selecting a finish does not automatically price the whole design.')
        st.caption('Includes boards, fronts, worktops, tiles, paint colours, splashbacks, glass, lighting, sinks, taps, appliances, extractors, handles and accessories. Dimensions describe a simple presentation envelope; verify manufacturer installation requirements.')
        if st.button('Add illustrative starter products',key='add_starter_products'):
            existing={r['id'] for r in records}
            for record in starter_products():
                if record['id'] not in existing:save_material(record)
            st.rerun()
        category_filter=st.selectbox('Browse library category',['All',*CATEGORIES],key='library_category_filter')
        visible=[r for r in records if category_filter=='All' or r['category']==category_filter]
        pick=st.selectbox('Create or edit material',['New material']+[r['id'] for r in visible],format_func=lambda k:k if k=='New material' else next(r['name']+' · '+r['category'] for r in records if r['id']==k),key='material_pick')
        current={} if pick=='New material' else next(r for r in records if r['id']==pick)
        with st.form('material_form_'+pick):
            name=st.text_input('Material name',value=current.get('name',''))
            category=st.selectbox('Material category',CATEGORIES,index=CATEGORIES.index(current.get('category','Carcass' if category_filter=='All' else category_filter)))
            thickness=st.number_input('Material thickness (mm)',min_value=.1,max_value=200.,value=float(current.get('thickness_mm',18)))
            color=st.color_picker('Material colour',value=current.get('color','#eeeae2'))
            finish=st.selectbox('Surface finish',['Matte','Gloss','Wood grain'],index=['Matte','Gloss','Wood grain'].index(current.get('finish','Matte')))
            supplier=st.text_input('Material supplier / range',value=current.get('supplier',''))
            price=st.number_input('Optional material price (R/m² excluding VAT)',min_value=0.,value=current.get('price_m2'))
            st.caption('Product envelope for placement (millimetres). Surface products are placed as panels; dimensions do not calculate purchased quantity.')
            dimensions={}
            for field,label,default in [('width_mm','Product width',600),('height_mm','Product height',600),('depth_mm','Product depth',20)]:
                dimensions[field]=st.number_input(label+' (mm)',min_value=.1,max_value=20000.,value=float(current.get(field,default)))
            price_each=st.number_input('Optional product price (R/item excluding VAT)',min_value=0.,value=current.get('price_each'))
            sku=st.text_input('Product code / SKU',value=current.get('sku',''))
            notes=st.text_area('Product notes / installation requirements',value=current.get('notes',''))
            save=st.form_submit_button('Save material to library')
        if save:
            try:
                record=dict(name=name,category=category,thickness_mm=thickness,color=color,finish=finish,supplier=supplier,price_m2=price,price_each=price_each,sku=sku,notes=notes,**dimensions)
                if current:record['id']=current['id']
                save_material(record);st.rerun()
            except ValueError as error:st.error(str(error))
        st.dataframe(visible,hide_index=True)
        st.download_button('Download material library backup',json.dumps(data,indent=2),'materials.json','application/json')

        backup=st.file_uploader('Restore material library JSON',type=['json'],key='material_library_backup')
        if st.button('Restore material library',disabled=backup is None,key='restore_material_library'):
            try:
                restore_material_library(backup.getvalue());st.rerun()
            except (ValueError,KeyError,TypeError) as error:st.error(str(error))
