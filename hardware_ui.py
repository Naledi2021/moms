from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import pandas as pd
import streamlit as st
from supplier_updates import load,current_products,unit_price_ex_vat


def available_products(units):
    products=st.session_state['_job_supplier_snapshot'] if '_job_supplier_snapshot' in st.session_state else current_products(load(),datetime.now(ZoneInfo('Africa/Johannesburg')).date())
    return [p for p in products if p['unit'] in units]


def identity(p):
    return p['supplier']+' · '+p['sku']+' · '+p['product']


def select_unit_price(label,key):
    products=available_products(('each',))
    selected=None
    if products:
        source=st.selectbox(label+' source',['Manual entry','Uploaded supplier prices'],key=key+'_source')
        if source=='Uploaded supplier prices':
            by_id={identity(p):p for p in products}
            chosen=st.selectbox(label+' product',list(by_id),key=key+'_product')
            selected=by_id[chosen]
            st.caption(f"{chosen}; effective {selected['effective_date']}; VAT {selected['vat_basis'].lower()}. Confirm this is the correct component, priced individually.")
            try:price=unit_price_ex_vat(selected)
            except ValueError as error:
                st.error(str(error));return None,selected
            st.caption(f'Applied price excluding VAT: R {price:,.2f} each.')
            return price,selected
    return st.number_input(label,min_value=0.0,value=None,key=key+'_manual'),selected


def supplier_accessories():
    products=available_products(('each','set'))
    items=[];invalid=False
    if not products:return items,invalid
    st.subheader('Accessories from uploaded supplier lists')
    st.caption('Quantities are for the entire job. Select exact models and check set contents. Hinge/plate items entered above should not be added here again.')
    by_id={identity(p):p for p in products}
    selected=st.multiselect('Supplier accessories for this job',list(by_id),key='uploaded_accessories')
    for name in selected:
        product=by_id[name]
        key=hashlib.sha256(name.encode()).hexdigest()[:16]
        quantity=st.number_input(name+' — job quantity',min_value=0,value=1,step=1,key='uploaded_qty_'+key)
        if not quantity:continue
        try:price=unit_price_ex_vat(product)
        except ValueError as error:
            st.error(name+': '+str(error));invalid=True;continue
        items.append(dict(supplier=product['supplier'],sku=product['sku'],product=product['product'],unit=product['unit'],quantity=quantity,unit_price_ex_vat=price,total_ex_vat=price*quantity,effective_date=product['effective_date']))
    if items:
        st.dataframe(pd.DataFrame(items),hide_index=True,width='stretch')
        st.download_button('Download selected hardware CSV',pd.DataFrame(items).to_csv(index=False).encode(),'supplier_hardware.csv','text/csv')
    return items,invalid
