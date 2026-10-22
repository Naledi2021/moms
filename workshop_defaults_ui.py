import json
import streamlit as st
from workshop_defaults import load_workshop,save_workshop,seed_workshop,BUILTIN


def render_workshop_defaults():
    defaults=load_workshop()
    if '_job_workshop_defaults' not in st.session_state:
        st.session_state['_job_workshop_defaults']=defaults if not st.session_state.get('_active_job_id') else {'settings':{}}
    seed_workshop(st.session_state,st.session_state['_job_workshop_defaults'])
    with st.expander('Workshop construction defaults — set once'):
        st.caption('Board thickness already deducts both sides automatically. The extra shelf fitting gap normally stays at 0 mm. Save your normal construction once; new jobs use it, while saved jobs keep their own settings. Fixed workshop rules remain two 100 mm rails, a 3 mm rear-fixed back and 4 mm total door deductions.')
        settings=defaults['settings']
        st.write(f"Standard: {settings['job_thickness']:g} mm {settings['job_material']}; base {settings['job_width']:g} × {settings['job_height']:g} × {settings['job_depth']:g} mm; extra shelf gap {settings['job_clearance']:g} mm; edging {settings['job_carcass_edging']} mm; {settings['job_hinges_per_door']} hinges per door.")
        st.caption('Change the cabinet and hinge settings below, then use Save current construction as workshop defaults. Room measurements, customer details, cabinet quantities and prices are not copied.')
        if st.session_state.get('_workshop_message'):st.success(st.session_state.pop('_workshop_message'))
        if st.button('Use latest workshop defaults for this job',disabled=bool(st.session_state.get('_design_lock')),key='refresh_workshop_defaults'):
            st.session_state['_job_workshop_defaults']=load_workshop()
            for key in BUILTIN:st.session_state.pop(key,None)
            st.rerun()
        st.download_button('Download workshop defaults backup',json.dumps(defaults,indent=2),'workshop_defaults.json','application/json')
        upload=st.file_uploader('Restore workshop defaults JSON',type=['json'],key='workshop_defaults_upload')
        if st.button('Restore workshop defaults',disabled=upload is None,key='restore_workshop_defaults'):
            try:
                if len(upload.getvalue())>100_000:raise ValueError('Workshop backup exceeds 100 KB.')
                save_workshop(json.loads(upload.getvalue())['settings'])
                st.session_state['_workshop_message']='Workshop defaults restored. Saved jobs are unchanged.';st.rerun()
            except (ValueError,KeyError,TypeError) as error:st.error(str(error))


def render_save_workshop():
    if st.button('Save current construction as workshop defaults',key='save_workshop_defaults'):
        try:
            data=save_workshop({key:st.session_state[key] for key in BUILTIN if key in st.session_state})
            st.session_state['_workshop_message']='Construction defaults saved for future jobs. Existing saved jobs were not changed.'
            st.rerun()
        except ValueError as error:st.error(str(error))
