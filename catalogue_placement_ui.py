import streamlit as st
from materials import load_materials,CATEGORIES
from catalogue_placement import place_product


def render_product_placement(layout,rows,lock):
    with st.expander('Place library finishes, fixtures and appliances'):
        st.caption('Create products in Materials and fixtures library above. Place a labelled dimensional model, then select it on the plan to move, rotate or delete it. Surfaces use panels; sinks, taps and lights use simple solid envelopes. No cut-outs, plumbing, electrical or purchase quantities are generated. Prices remain reference values and are not added to the cabinet quotation.')
        category=st.selectbox('Placement library category',CATEGORIES,key='product_placement_category',disabled=bool(lock))
        records={r['id']:r for r in load_materials()['materials'] if r['category']==category}
        if not records:
            st.info('No products in this category yet. Add your own in Materials and fixtures library.');return
        pick=st.selectbox('Library product',list(records),format_func=lambda k:records[k]['name'],key='product_placement_pick',disabled=bool(lock))
        record=records[pick]
        st.write(record.get('notes',''))
        st.caption('Coordinates use the same room origin as cabinets. Set elevation above the floor for wall lights, taps and extractors. Review overlap warnings; intentional intersections need workshop review.')
        with st.form('place_catalogue_product'):
            c=st.columns(3)
            x=c[0].number_input('Product X (mm)',min_value=0.,value=0.,disabled=bool(lock))
            y=c[1].number_input('Product Y (mm)',min_value=0.,value=0.,disabled=bool(lock))
            z=c[2].number_input('Product elevation (mm)',min_value=0.,value=0.,disabled=bool(lock))
            add=st.form_submit_button('Place library product',disabled=bool(lock))
        if add:
            try:
                updated=place_product(record,layout,rows,x,y,z,lock)
                from layout_ui import commit_scene
                st.session_state['_designer_selected']=len(updated)-1
                commit_scene(updated)
            except (ValueError,KeyError,TypeError) as error:st.error(str(error))
