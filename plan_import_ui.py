import hashlib
import math
import os
import pandas as pd
import streamlit as st
from plan_import import document_pages,local_ocr,vision_read,measurement_candidates


def render_plan_import():
    with st.expander('Read a sketch, plan or PDF'):
        st.write('Upload a photo of a sketch or a PDF plan. Review the extracted text and measurements before using them in the room layout.')
        file=st.file_uploader('Sketch or plan document',type=['png','jpg','jpeg','pdf'],key='plan_document_upload')
        method=st.selectbox('Reading method',['PDF text / local OCR','AI handwriting reading'],key='plan_reading_method')
        if method=='AI handwriting reading' and not os.environ.get('KITCHEN_VISION_API_KEY'):
            st.info('AI handwriting reading needs a configured AI service. Local OCR remains available but can struggle with handwriting.')
        st.caption('Local reading stays on this server. AI reading sends document images to the configured AI service only when you click Read document. PDFs: up to 5 pages; uploads: up to 15 MB. No dimensions are inferred from drawing scale.')
        if file:
            digest=hashlib.sha256(file.getvalue()).hexdigest()
            if st.button('Read document',key='read_plan_document'):
                try:
                    with st.spinner('Reading document annotations…'):
                        embedded,pages=document_pages(file.getvalue(),file.name)
                        if method=='AI handwriting reading':result=vision_read(pages)
                        else:
                            text=embedded if embedded.strip() else local_ocr(pages)
                            result={'text':text,'uncertainties':['Local OCR may misread handwriting or miss annotations. Confirm all dimensions against the original.']}
                    st.session_state['_plan_draft']={'filename':file.name,'digest':digest,**result}
                    st.session_state['plan_review_text']=result['text']
                    st.session_state['_plan_page_previews']=pages
                except Exception as error:st.error(f'Could not read document: {error}')
            draft=st.session_state.get('_plan_draft')
            if draft and draft['digest']==digest:
                for page in st.session_state.get('_plan_page_previews',[])[:5]:st.image(page,width=500)
                text=st.text_area('Review and correct extracted text',height=200,key='plan_review_text')
                for uncertainty in draft['uncertainties']:st.warning(str(uncertainty))
                candidates=measurement_candidates(text)
                if candidates:
                    st.dataframe(pd.DataFrame(candidates),hide_index=True,width='stretch')
                    index=st.selectbox('Measurement annotation to use for room dimensions',range(len(candidates)),format_func=lambda i:candidates[i]['annotation'],key='plan_candidate')
                    candidate=candidates[index]
                    purpose=st.selectbox('What does this annotation describe?',['Room dimensions','Base cabinet','Wardrobe','Panel','Worktop','Appliance'],key='plan_measurement_purpose')
                    orders=['Room length × depth','Room length × depth × height'] if purpose=='Room dimensions' else ['Width × height × depth','Width × depth × height']
                    order=st.selectbox('Meaning of these dimensions',orders,key='plan_dimension_order')
                    unit=st.selectbox('Confirm measurement unit',['mm','cm','m'],index=['mm','cm','m'].index(candidate['unit']) if candidate['unit'] in ('mm','cm','m') else 0,key='plan_confirmed_unit')
                    signature=repr((digest,text,index,order,unit,purpose))
                    if st.session_state.get('_plan_verification_context')!=signature:
                        st.session_state['plan_annotation_verified']=False
                        st.session_state['_plan_verification_context']=signature
                    verified=st.checkbox('I checked this annotation and its units against the original',key='plan_annotation_verified')
                    needed=2 if order=='Room length × depth' else 3
                    if st.button('Apply reviewed measurement',disabled=not verified or len(candidate['values'])!=needed,key='apply_plan_dimensions'):
                        multiplier={'mm':1,'cm':10,'m':1000}[unit];values=[v*multiplier for v in candidate['values']]
                        if not all(math.isfinite(v) and v>0 for v in values) or (purpose=='Room dimensions' and (min(values[:2])<500 or (needed==3 and values[2]<1000))):
                            st.error('Check units: room dimensions must be at least 500 mm horizontally and 1000 mm high.');return
                        st.session_state['_job_plan_import']={'filename':draft['filename'],'text':text,'reviewed_annotation':candidate['annotation'],'confirmed_unit':unit,'dimension_order':order,'purpose':purpose}
                        if purpose=='Room dimensions':
                            st.session_state['design_room_length']=values[0];st.session_state['design_room_width']=values[1]
                            if needed==3:st.session_state['design_room_height']=values[2]
                            st.session_state.pop('design_layout_signature',None)
                            st.success('Reviewed room dimensions applied. Review and confirm the room layout below.')
                        else:
                            w,h,d=values if order=='Width × height × depth' else (values[0],values[2],values[1])
                            pending=st.session_state.get('_job_import_units',[])
                            entry={'Name':'Imported '+purpose,'Type':purpose,'Width (mm)':w,'Height (mm)':h,'Depth (mm)':d,'X (mm)':0,'Y (mm)':0,'Z (mm)':0,'Rotation (deg)':0,'Shelves':1 if purpose in ('Base cabinet','Wardrobe') else 0}
                            if entry not in pending:pending.append(entry)
                            st.session_state['_job_import_units']=pending
                            st.success('Reviewed item staged. Confirm the room layout, then add it in unit placement and set its position.')
                else:st.info('No dimension groups were detected. Correct the text or enter measured room dimensions below.')
                st.download_button('Download reviewed plan text',text,'reviewed_plan_text.txt','text/plain')
