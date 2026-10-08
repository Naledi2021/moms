from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from supplier_updates import TEMPLATE, read_upload, validate, save, load, current_products


def render_supplier_uploads():
    with st.expander('Upload supplier price updates'):
        st.write('Upload a supplier CSV or Excel workbook, match its columns, then review and save the update. Older revisions and products not mentioned in this update are retained.')
        st.download_button('Download price-list CSV template',TEMPLATE,'supplier_price_template.csv','text/csv')
        st.caption('Template rows are examples. Prices must be positive numbers using decimal points. Units: sheet, m2, each, set or metre. PDF and scanned lists need conversion to CSV or Excel first.')
        supplier=st.selectbox('Supplier for this upload',['Seno SA','Plaza Board','BoardCity','PG Bison','Niemann SA','Roco','Blum','Gelmar','Other'],key='upload_supplier')
        if supplier=='Other':supplier=st.text_input('Supplier name',key='upload_supplier_name')
        effective=st.date_input('Prices effective from',value=datetime.now(ZoneInfo('Africa/Johannesburg')).date(),key='upload_effective')
        vat=st.selectbox('Supplier prices VAT basis',['Not specified','Excluded','Included'],key='upload_vat')
        vat_rate=st.number_input('VAT percentage included in supplier prices',min_value=0.0,value=None,key='upload_vat_rate') if vat=='Included' else None
        file=st.file_uploader('Supplier price list',type=['csv','xlsx'],key='supplier_upload')
        if file:
            try:
                data=file.getvalue(); sheet=None
                if file.name.lower().endswith('.xlsx'):
                    # Validate workbook size before examining its sheet names.
                    read_upload(data,file.name)
                    with pd.ExcelFile(BytesIO(data),engine='openpyxl') as workbook:
                        sheet=st.selectbox('Worksheet',workbook.sheet_names,key='upload_sheet')
                frame=read_upload(data,file.name,sheet)
                st.dataframe(frame.head(20),hide_index=True,width='stretch')
                mapping={}
                for field in ['sku','product','price','unit','length_mm','width_mm','thickness_mm']:
                    optional=field.endswith('_mm')
                    choices=['Not mapped']+list(frame.columns)
                    match=next((c for c in frame.columns if c.casefold()==field),None)
                    selected=st.selectbox(('Optional ' if optional else 'Required ')+field+' column',choices,index=choices.index(match) if match else 0,key='upload_map_'+field)
                    mapping[field]=None if selected=='Not mapped' else selected
                if all(mapping[k] for k in ['sku','product','price','unit']):
                    rows,errors=validate(frame,mapping)
                    if errors:
                        st.error(f'{len(errors)} row errors. Nothing will be saved until all rows are valid.')
                        for error in errors[:20]:st.write(error)
                    else:
                        st.success(f'{len(rows)} products validated. Review the prices below.')
                        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
                        if st.button('Save supplier price update',disabled=not supplier.strip() or (vat=='Included' and vat_rate is None)):
                            added=save(rows,supplier,effective,vat,vat_rate,file.name)
                            st.success('Supplier update saved.' if added else 'This exact update is already saved.')
                else:st.info('Match all four required columns to validate this update.')
            except Exception as error:
                st.error(f'Could not import this file: {error}')
        history=load()
        products=current_products(history,datetime.now(ZoneInfo('Africa/Johannesburg')).date())
        st.subheader('Saved supplier prices')
        if products:
            st.dataframe(pd.DataFrame(products),hide_index=True,width='stretch')
            st.download_button('Download current supplier prices CSV',pd.DataFrame(products).to_csv(index=False).encode(),'current_supplier_prices.csv','text/csv')
        else:st.caption('No supplier prices are effective yet.')
        if history['updates']:
            st.caption('Revision history includes future-dated updates. Future prices activate on their effective date.')
            st.dataframe(pd.DataFrame([{k:u[k] for k in ['supplier','effective_date','uploaded_utc','filename','vat_basis']}|{'products':len(u['products'])} for u in reversed(history['updates'])]),hide_index=True,width='stretch')
