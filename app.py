# app.py — Login simples + menu quando logado (sem sidebar)
from __future__ import annotations
import streamlit as st
from supabase_client import get_supabase

# ----- Página e CSS -----
st.set_page_config(page_title="Family Finance — Login", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
/* Esconde sidebar e botão hambúrguer */
section[data-testid="stSidebar"]{display:none!important;}
div[data-testid="collapsedControl"]{display:none!important;}
/* Layout central sem rolagem extra */
html, body, [data-testid="stAppViewContainer"]{height:100%;}
.full {min-height:100vh; display:flex; align-items:flex-start; justify-content:center; padding:40px 16px;}
.card { width:100%; max-width:520px; background:#fff; border:1px solid #e5e7eb; border-radius:14px;
        padding:22px 18px; box-shadow:0 12px 28px rgba(0,0,0,.08); }
h1.title { font-weight:800; color:#0b2038; margin:0 0 18px 0; text-align:center; }
.welcome { font-size:1.0rem; margin-bottom:.4rem; }
.menu-grid .stButton>button{ width:100%; padding:14px; border-radius:12px; font-weight:700; }
.stButton>button{ border-radius:10px; background:#0ea5e9; border:1px solid #0ea5e9; color:#fff; font-weight:700;}
.stButton>button:hover{ background:#0284c7; border-color:#0284c7; }
footer{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ----- Supabase -----
if "sb" not in st.session_state:
    st.session_state.sb = get_supabase()
sb = st.session_state.sb

def _user():
    sess = sb.auth.get_session()
    return sess.user if sess and sess.user else None

def _signin(email: str, password: str):
    sb.auth.sign_in_with_password({"email": email, "password": password})

def _signout():
    sb.auth.sign_out()
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.experimental_rerun()

# ----- Helpers de navegação (tenta com/sem emoji) -----
def go_financeiro():
    try: st.switch_page("pages/💼_Financeiro.py")
    except Exception: st.switch_page("pages/_Financeiro.py")

def go_dashboards():
    try: st.switch_page("pages/📊_Dashboards.py")
    except Exception: st.switch_page("pages/_Dashboards.py")

def go_admin():
    try: st.switch_page("pages/🧰_Administracao.py")
    except Exception: st.switch_page("pages/_Administracao.py")

# =========================
# Se já logado: MENU simples
# =========================
u = _user()
if u:
    st.markdown("<h1 class='title'>Family Finance</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='welcome'>Bem-vindo(a), <b>{u.email}</b>!</div>", unsafe_allow_html=True)
    st.caption("Escolha uma área para continuar:")

    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        if st.button("💼 Financeiro", use_container_width=True):
            go_financeiro()
    with c2:
        if st.button("📊 Dashboards", use_container_width=True):
            go_dashboards()
    with c3:
        if st.button("🧰 Administração", use_container_width=True):
            go_admin()

    st.divider()
    if st.button("Sair"):
        _signout()
    st.stop()

# =========================
# Login (quando não logado)
# =========================
st.markdown('<div class="full"><div class="card">', unsafe_allow_html=True)
st.markdown("<h1 class='title'>Family Finance</h1>", unsafe_allow_html=True)

email = st.text_input("E-mail")
pw    = st.text_input("Senha", type="password")

if st.button("Entrar", use_container_width=True):
    if not email or not pw:
        st.warning("Informe e-mail e senha.")
    elif len(pw) < 6:
        st.warning("A senha deve ter pelo menos 6 caracteres.")
    else:
        try:
            _signin(email.strip(), pw)
            if _user():
                st.experimental_rerun()   # volta e mostra o menu
            else:
                st.error("Credenciais inválidas.")
        except Exception as e:
            st.error(f"Falha no login: {e}")

st.markdown('</div></div>', unsafe_allow_html=True)
