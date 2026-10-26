import base64
import json
from io import BytesIO
from PIL import Image,UnidentifiedImageError
import streamlit as st


def render_active_plan(location='room'):
    source=st.session_state.get('_job_plan_import')
    if not source:return
    with st.expander('Active plan reference — '+source.get('filename','Imported plan')):
        st.caption('This first-page reference image and reviewed text belong to the current design. Removing the upload does not remove it. Saved job revisions include the reference and measurements. The image is a reference, not a scaled drawing layer.')
        if source.get('reference_image_base64'):
            try:
                data=base64.b64decode(source['reference_image_base64'],validate=True)
                if len(data)>1_000_000:raise ValueError('Reference exceeds supported size.')
                Image.open(BytesIO(data)).verify()
                st.image(data,width=650)
            except (ValueError,TypeError,OSError,UnidentifiedImageError):st.info('The saved reference image is unavailable. Reviewed text and room measurements are retained.')
        st.text(source.get('text',''))
        st.download_button('Download active room and plan reference',json.dumps({'schema_version':1,'layout':st.session_state.get('_job_layout'),'room_lock':st.session_state.get('_room_lock'),'source':source},indent=2,allow_nan=False),'active_room_plan.json','application/json',key='active_plan_export_'+location,disabled=not bool(st.session_state.get('design_layout_signature')))
