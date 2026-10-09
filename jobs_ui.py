import base64
import pandas as pd
import streamlit as st
from jobs import load_jobs, restore_revision, clear_job, capture_state, save_job, import_job_history


def render_saved_jobs():
    with st.expander('Saved customer jobs and quotations'):
        if st.button('Start a new job',key='new_job'):
            clear_job(st.session_state);st.rerun()
        with st.expander('Restore a downloaded job history'):
            archive=st.file_uploader('Exported job-history JSON',type=['json'],key='job_history_upload')
            if st.button('Restore job history',disabled=archive is None,key='restore_job_history'):
                try:
                    changed=import_job_history(archive.getvalue())
                    st.session_state['_job_save_message']='History restored. Existing revisions were preserved.' if changed else 'This history is already saved.'
                    st.rerun()
                except (ValueError,KeyError,TypeError,OSError) as error:st.error(f'Could not restore history: {error}')
        data=load_jobs()
        if not data['jobs']:
            st.caption('No jobs saved yet. Enter customer details and cabinet settings, then save at the bottom of the estimate.')
            return
        query=st.text_input('Search saved jobs',key='job_search').strip().casefold()
        jobs=[j for j in reversed(data['jobs']) if query in (j['name']+' '+str(j['revisions'][-1]['state'].get('customer_name',''))+' '+str(j['revisions'][-1]['state'].get('customer_phone',''))).casefold()]
        if not jobs:st.info('No matching jobs.');return
        selected=st.selectbox('Saved job',[j['id'] for j in jobs],format_func=lambda key:next(j['name']+' · '+j['id'][:8] for j in jobs if j['id']==key),key='saved_job_pick')
        job=next(j for j in jobs if j['id']==selected)
        number=st.selectbox('Quotation revision',[r['number'] for r in reversed(job['revisions'])],key='saved_revision_pick')
        revision=next(r for r in job['revisions'] if r['number']==number)
        snapshot=revision['snapshot']
        st.write(f"Saved {revision['saved_utc']} · {snapshot['pricing_status']} · Total R {snapshot['total']:,.2f}")
        st.caption('Opening restores the saved supplier prices. Downloading an earlier revision returns its original PDF and cutting list.')
        if st.button('Open saved job',key='open_saved_job'):
            restore_revision(st.session_state,job['id'],revision);st.rerun()
        st.download_button('Download saved quotation PDF',base64.b64decode(revision['pdf_base64']),f"quotation_{job['id'][:8]}_r{number}.pdf",'application/pdf')
        st.download_button('Download saved cutting list',revision['cutting_csv'].encode(),f"cutting_list_{job['id'][:8]}_r{number}.csv",'text/csv')
        views=snapshot.get('design_views',{})
        if views.get('line_svg'):
            st.download_button('Download saved line drawing',views['line_svg'],f"lines_{job['id'][:8]}_r{number}.svg",'image/svg+xml')
            st.download_button('Download saved sketch',views['sketch_svg'],f"sketch_{job['id'][:8]}_r{number}.svg",'image/svg+xml')
        if views.get('video_base64'):
            st.download_button('Download saved video',base64.b64decode(views['video_base64']),f"video_{job['id'][:8]}_r{number}.mp4",'video/mp4')
        st.download_button('Export saved job history',__import__('json').dumps(job,indent=2),f"job_{job['id'][:8]}.json",'application/json')
        st.dataframe(pd.DataFrame([{'Revision':r['number'],'Saved (UTC)':r['saved_utc'],'Status':r['state'].get('job_status','Enquiry'),'Total (R)':r['snapshot']['total'],'Pricing':r['snapshot']['pricing_status']} for r in reversed(job['revisions'])]),hide_index=True,width='stretch')
    if st.session_state.get('_active_job_id'):
        st.info(f"Editing saved job · opened revision {st.session_state['_active_revision']}. Saving appends a new revision.")
    if '_job_supplier_snapshot' in st.session_state:
        st.caption('Supplier prices are held at the saved revision. Refresh them explicitly to use current price lists.')
        if st.button('Use current supplier prices for this job',key='refresh_job_prices'):
            del st.session_state['_job_supplier_snapshot'];st.rerun()


def render_save_job(name,snapshot,pdf,cutting_csv):
    st.subheader('Save customer job and quotation')
    st.caption('Save keeps the current cabinet settings, customer details, supplier price snapshot, PDF and cutting list. Revisions are preserved.')
    active=st.session_state.get('_active_job_id')
    label='Save new quotation revision' if active else 'Save new customer job'
    if st.button(label,key='save_job',disabled=not name.strip()):
        try:
            job_id,number=save_job(name,capture_state(dict(st.session_state)),snapshot,pdf,cutting_csv,active)
            st.session_state['_active_job_id']=job_id
            st.session_state['_active_revision']=number
            st.session_state['_job_save_message']=f'Job saved — quotation revision {number}.'
            st.rerun()
        except (ValueError,OSError) as error:st.error(f'Could not save job: {error}')
    if st.session_state.get('_job_save_message'):
        st.success(st.session_state.pop('_job_save_message'))
