"""Presentation only: no widget identity or saved design changes."""
import streamlit as st


def apply_studio_style():
    st.markdown('''<style>
    .stApp {background:#f5f7fa;color:#203348}
    .block-container {max-width:1440px;padding-top:2rem;padding-bottom:4rem}
    h1,h2,h3 {color:#132d46;letter-spacing:-.025em}
    h1 {font-size:2.15rem!important} h2 {font-size:1.55rem!important}
    [data-testid="stSidebar"] {background:#eaf0f5;border-right:1px solid #d6e0e8}
    [data-testid="stSidebar"] h2 {font-size:1.15rem!important}
    [data-testid="stExpander"] {background:#fff;border:1px solid #d9e2e9;border-radius:12px;box-shadow:0 2px 8px #18344b05;margin-bottom:.7rem}
    [data-testid="stExpander"] summary {font-weight:600;color:#17354d}
    [data-testid="stForm"] {background:#fff;border-color:#d9e2e9;border-radius:12px}
    [data-testid="stMetric"] {background:#fff;border:1px solid #d9e2e9;border-radius:10px;padding:1rem}
    [data-testid="stButton"] button,[data-testid="stDownloadButton"] button {border-radius:8px;min-height:2.65rem;font-weight:500}
    [data-testid="stButton"] button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] {background:#173b57;border-color:#173b57;color:#fff}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {color:#52677a!important}
    .studio-eyebrow {font-size:.72rem;letter-spacing:.16em;color:#936a25;font-weight:700;margin-top:.4rem}
    .studio-steps {display:flex;flex-wrap:wrap;gap:12px;margin:12px 0 24px}
    .studio-steps span {background:#fff;border:1px solid #d9e2e9;border-radius:8px;padding:10px 16px;color:#38536a;font-size:.85rem}
    @media(max-width:800px){.block-container{padding-top:1rem}.studio-steps{gap:6px}.studio-steps span{padding:8px}}
    </style>''',unsafe_allow_html=True)


def studio_workflow():
    st.markdown('''<div class="studio-steps"><span>01 &nbsp; Measure the room</span><span>02 &nbsp; Place & refine units</span><span>03 &nbsp; Review finishes</span><span>04 &nbsp; Save & quote</span></div>''',unsafe_allow_html=True)
