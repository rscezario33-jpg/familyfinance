# supabase_client.py
from __future__ import annotations
import os, re, socket
import streamlit as st
from supabase import create_client, Client

_URL_RE = re.compile(r"^https://[a-z0-9\-]+\.supabase\.co$", re.I)

def _sanitize(s: str) -> str:
    if not s:
        return s
    # remove caracteres invisíveis comuns de copy/paste
    for ch in ["\u200b", "\u200c", "\u200d", "\uFEFF", "\u00A0"]:
        s = s.replace(ch, "")
    return s.strip().rstrip("/")

@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    cfg = st.secrets.get("supabase", {}) if hasattr(st, "secrets") else {}
    url = _sanitize(cfg.get("url") or os.getenv("SUPABASE_URL") or "")
    key = _sanitize(cfg.get("anon_key") or os.getenv("SUPABASE_ANON_KEY") or "")

    if not url or not key:
        st.error("Defina `supabase.url` e `supabase.anon_key` em `.streamlit/secrets.toml`.")
        st.stop()

    if ".supabase.com" in url:
        st.error("`SUPABASE_URL` inválida: use `.supabase.co` (não `.com`).")
        st.stop()

    if not _URL_RE.match(url):
        st.error(f"`SUPABASE_URL` parece inválida: `{url}`")
        st.stop()

    # Diagnóstico DNS antes do client
    try:
        host = url.replace("https://", "")
        socket.gethostbyname(host)  # deve resolver p/ um IP
    except Exception as e:
        st.error(f"Falha de DNS para `{host}`. Detalhes: {e}")
        st.stop()

    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"Não foi possível inicializar o Supabase: {e}")
        st.stop()
