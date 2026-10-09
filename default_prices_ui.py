import json
import pandas as pd
import streamlit as st
from default_prices import load_defaults,save_defaults,seed_defaults,capture_defaults,ALLOWANCES


def render_shared_defaults():
    shared=load_defaults()
    if '_job_default_prices' not in st.session_state:st.session_state['_job_default_prices']=shared
    with st.expander('Shared default prices — all customers'):
        if st.session_state.get('_shared_prices_message'):st.success(st.session_state.pop('_shared_prices_message'))
        st.caption('These are business-wide defaults, excluding VAT. Board prices are stored separately by material and thickness, hinge/plate prices by brand. Material defaults use R/m², including prices originally entered per sheet. Edit a quotation without changing defaults; explicitly save defaults to change future jobs. Saved quotations retain their price snapshot.')
        st.write(f'{len(shared["prices"])} shared settings saved. Last updated: {shared["updated_utc"] or "Not saved yet"}')
        if shared['prices']:
            edited=st.data_editor(pd.DataFrame([{'Setting':k,'Default value':v} for k,v in sorted(shared['prices'].items())]),hide_index=True,disabled=['Setting'],key='shared_prices_editor',column_config={'Default value':st.column_config.NumberColumn(min_value=0,required=True)})
            if st.button('Save edited shared defaults',key='save_edited_defaults'):
                try:
                    save_defaults(dict(zip(edited['Setting'],edited['Default value'])))
                    st.session_state['_shared_prices_message']='Shared defaults updated. Existing jobs are unchanged.'
                    st.rerun()
                except ValueError as error:st.error(str(error))
        st.download_button('Download shared default prices backup',json.dumps(shared,indent=2),'default_prices.json','application/json')
        backup=st.file_uploader('Restore shared default prices JSON',type=['json'],key='shared_prices_backup')
        if st.button('Restore shared price defaults',disabled=backup is None,key='restore_shared_prices'):
            try:
                if len(backup.getvalue())>1_000_000:raise ValueError('Backup exceeds 1 MB.')
                data=json.loads(backup.getvalue())
                save_defaults(data['prices'])
                st.session_state['_shared_prices_message']='Defaults restored. Existing quotation prices are unchanged.'
                st.rerun()
            except (ValueError,KeyError,TypeError) as error:st.error(str(error))
        if st.button('Use latest shared defaults for this job',key='refresh_shared_defaults'):
            st.session_state['_job_default_prices']=load_defaults()
            for key in list(st.session_state):
                if key in ALLOWANCES or key.startswith(('carcass_supplier_','back_supplier_','door_supplier_','hinge_price_','plate_price_','_default_profile_')):st.session_state.pop(key,None)
            st.session_state.pop('_job_manual_accessories',None)
            st.session_state.pop('blum_accessories',None)
            st.rerun()


def save_current_defaults(carcass_rate,back_rate,door_rate,hinge,plate,accessories):
    st.caption('Prices above are editable for this job. Saving shared defaults also makes them available to all new customer jobs. Customer details, unit quantities and accessory quantities are excluded.')
    if st.button('Save these prices as shared defaults',key='save_current_defaults'):
        try:
            prices=capture_defaults(st.session_state,carcass_rate,back_rate,door_rate,hinge,plate,accessories)
            save_defaults(prices)
            st.session_state['_shared_prices_message']='Defaults saved for all new jobs. Other saved quotations were not repriced.'
            st.rerun()
        except ValueError as error:st.error(str(error))
