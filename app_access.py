"""Optional local access; hosting requires a password supplied through secrets."""
import os
import secrets
import hashlib

import streamlit as st


def require_access():
    password = os.environ.get('KITCHEN_APP_PASSWORD', '')
    required = os.environ.get('KITCHEN_REQUIRE_PASSWORD', '').lower() in {'1', 'true', 'yes'}
    if not password:
        if required:
            st.error('The app owner must configure KITCHEN_APP_PASSWORD in hosting secrets before access is available.')
            st.stop()
        return
    fingerprint = hashlib.sha256(password.encode()).hexdigest()
    if st.session_state.get('_access_password') == fingerprint:
        return
    st.title('Moms Kitchens and Projects')
    with st.form('sign_in'):
        entered = st.text_input('Password', type='password')
        submitted = st.form_submit_button('Sign in')
    if submitted:
        if secrets.compare_digest(entered.encode(), password.encode()):
            st.session_state['_access_password'] = fingerprint
            st.rerun()
        st.error('Incorrect password.')
    st.stop()
