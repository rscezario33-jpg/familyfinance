# app.py — Login simples (fullscreen) + redirect
from __future__ import annotations
import streamlit as st
from supabase_client import get_supabase

# --------- Página sem sidebar ----------
st.set_page_config(page_title="Family Finance — Login", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
/* Oculta sidebar e botão hambúrguer */
section[data-testid="stSidebar"]{display:none!important;}
div[data-testid="collapsedControl"]{display:none!important;}
/* Centraliza tudo na tela, sem rolagem extra */
html, body, [data-testid="stAppViewContainer"]{height:100%;}
.fullscreen{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:0 16px;}
.card{width:100%;max-width:420px;background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:22px 18px;box-shadow:0 10px 30px rgba(0,0,0,.08);}
h1{margin:6px 0 14px 0;font-weight:800;text-align:center;color:#0b2038;}
.small{font-size:.85rem;color:#64748b;text-align:center;margin-top:8px}
.stButton>button{width:100%;border-radius:10px;background:#0ea5e9;border:1px solid #0ea5e9;color:#fff;font-weight:700;padding:.7rem;}
.stButton>button:hover{background:#0284c7;border-color:#0284c7;}
.logo{display:block;margin:0 auto 8px auto;max-width:140px;height:auto;}
</style>
""", unsafe_allow_html=True)

# --------- Supabase ----------
if "sb" not in st.session_state:
    st.session_state.sb = get_supabase()
sb = st.session_state.sb

def _user():
    sess = sb.auth.get_session()
    return sess.user if sess and sess.user else None

def _signin(email, password):
    sb.auth.sign_in_with_password({"email": email, "password": password})

def _signup(email, password):
    sb.auth.sign_up({"email": email, "password": password})

# Se já logado, manda para Dashboards
if _user():
    try:
        st.switch_page("pages/_Dashboards.py")
    except Exception:
        st.switch_page("pages/📊_Dashboards.py")

# --------- UI: cartão simples ----------
st.markdown('<div class="fullscreen"><div class="card">', unsafe_allow_html=True)

st.image("assets/logo_family_finance.png", use_column_width=False, width=140)
st.markdown("<h1>Family Finance</h1>", unsafe_allow_html=True)

email = st.text_input("Email")
pwd   = st.text_input("Senha", type="password")

col1, col2 = st.columns(2)
with col1:
    if st.button("Entrar"):
        if not email or not pwd:
            st.warning("Informe e-mail e senha.")
        elif len(pwd) < 6:
            st.warning("Senha deve ter pelo menos 6 caracteres.")
        else:
            try:
                _signin(email.strip(), pwd)
                if _user():
                    try:
                        st.switch_page("pages/_Dashboards.py")
                    except Exception:
                        st.switch_page("pages/📊_Dashboards.py")
                else:
                    st.error("Credenciais inválidas.")
            except Exception as e:
                st.error(f"Falha no login: {e}")

with col2:
    if st.button("Criar conta"):
        if not email or not pwd:
            st.warning("Informe e-mail e senha.")
        elif len(pwd) < 6:
            st.warning("Senha deve ter pelo menos 6 caracteres.")
        else:
            try:
                _signup(email.strip(), pwd)
                st.success("Conta criada. Confirme o e-mail (se exigido) e entre.")
            except Exception as e:
                st.error(f"Falha ao criar conta: {e}")

st.markdown('<div class="small">Powered by</div>', unsafe_allow_html=True)
st.image("assets/logo_automaGO.png", use_column_width=False, width=80)

st.markdown('</div></div>', unsafe_allow_html=True)
