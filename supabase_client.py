# supabase_client.py
from supabase import create_client, Client
import streamlit as st

@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)
