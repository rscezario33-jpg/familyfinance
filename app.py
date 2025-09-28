# app.py — Login Fullscreen (profissional) + redirect pós-login
from __future__ import annotations
import streamlit as st
from supabase_client import get_supabase

# ---------- Página sem sidebar ----------
st.set_page_config(page_title="Family Finance — Login", layout="wide", initial_sidebar_state="collapsed")

# Oculta sidebar, hamburger e ajusta a página pra ocupar 100vh com o background
st.markdown("""
<style>
/* Esconde sidebar e botão de colapso */
section[data-testid="stSidebar"]{ display:none !important; }
div[data-testid="collapsedControl"]{ display:none !important; }

/* Zera paddings laterais do layout wide */
div[data-testid="stAppViewContainer"] > div:first-child { padding-left: 0 !important; padding-right: 0 !important; }

/* Container raiz com imagem de fundo */
.ff-login-bg{
  min-height: 100vh;
  background: 
    linear-gradient(180deg, rgba(8,18,32,.55) 0%, rgba(12,28,48,.55) 50%, rgba(12,28,48,.65) 100%),
    url("assets/Backgroud_FF.png") no-repeat center center / cover;
  display:flex; align-items:center; justify-content:center;
}

/* Grade: esquerda (brand) / direita (form) — responsivo */
.ff-login-wrap{
  width: 100%;
  max-width: 1200px;
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 36px;
  padding: 36px;
}
@media (max-width: 980px){
  .ff-login-wrap{ grid-template-columns: 1fr; gap: 24px; padding: 24px; }
}

/* Cartões de vidro */
.ff-glass{
  background: rgba(255,255,255,.10);
  border: 1px solid rgba(255,255,255,.18);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 18px;
  box-shadow: 0 20px 50px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.18);
}

/* Box da marca (esquerda) */
.ff-brand-box{
  color: #eaf2ff;
  padding: 28px 28px 22px 28px;
  display:flex; flex-direction:column; justify-content:center;
}
.ff-brand-box img.logo{
  width: 260px; max-width: 60%; height:auto; display:block; margin: 0 0 18px 0;
  filter: drop-shadow(0 6px 18px rgba(0,0,0,.35));
}
.ff-title{
  font-size: 42px; font-weight: 800; margin: 2px 0 6px 0; letter-spacing: .2px;
}
.ff-sub{
  opacity: .90; font-size: 18px; line-height: 1.6; margin-bottom: 14px;
}

/* Box do formulário (direita) */
.ff-form-box{
  padding: 26px 24px 20px 24px;
  background: rgba(255,255,255,.96);
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 16px 40px rgba(0,0,0,.18);
}

/* Botões */
.stButton>button{
  border-radius: 12px; padding: .70rem 1rem; font-weight: 700;
  background: #0ea5e9; border: 1px solid #0ea5e9; color: #fff;
  box-shadow: 0 6px 16px rgba(0,165,233,.25);
  transition: transform .16s ease, background .16s ease, border-color .16s ease, box-shadow .16s ease;
}
.stButton>button:hover{
  transform: translateY(-1px);
  background: #0284c7; border-color: #0284c7;
  box-shadow: 0 10px 24px rgba(2,132,199,.28);
}

/* Rodapé powered by (bem discreto) */
.ff-powered{
  position: fixed; left: 12px; bottom: 10px; z-index: 5;
  color: #dbeafe; font-size: 11px; opacity: .85;
  display:flex; align-items:center; gap:8px;
}
.ff-powered img{ height: 16px; width:auto; filter: drop-shadow(0 1px 2px rgba(0,0,0,.35)); }
</style>
""", unsafe_allow_html=True)

# ---------- Supabase ----------
if "sb" not in st.session_state:
    st.session_state.sb = get_supabase()
sb = st.session_state.sb

def _signin(email: str, password: str):
    return sb.auth.sign_in_with_password({"email": email, "password": password})

def _signup(email: str, password: str):
    return sb.auth.sign_up({"email": email, "password": password})

def _user():
    sess = sb.auth.get_session()
    return sess.user if sess and sess.user else None

# Se já estiver logado, manda direto para Dashboards
u = _user()
if u:
    try:
        st.switch_page("pages/📊_Dashboards.py")
    except Exception:
        # fallback se o arquivo não tiver o emoji no nome
        st.switch_page("pages/_Dashboards.py")

# ---------- UI: Login Fullscreen ----------
st.markdown('<div class="ff-login-bg"><div class="ff-login-wrap">', unsafe_allow_html=True)

# COLUNA ESQUERDA — Marca
with st.container():
    st.markdown('<div class="ff-glass ff-brand-box">', unsafe_allow_html=True)
    st.image("assets/logo_family_finance.png", use_column_width=False, width=260)
    st.markdown('<div class="ff-title">Family Finance</div>', unsafe_allow_html=True)
    st.markdown('<div class="ff-sub">Plataforma de finanças familiares com colaboração, controle e inteligência — tudo em um só lugar.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# COLUNA DIREITA — Form
with st.container():
    st.markdown('<div class="ff-form-box">', unsafe_allow_html=True)
    st.markdown("### Acesse sua conta")
    email = st.text_input("Email", key="login_email").strip()
    pwd   = st.text_input("Senha", type="password", key="login_pwd")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Entrar", use_container_width=True):
            if not email:
                st.warning("Informe um e-mail.")
            elif not pwd or len(pwd) < 6:
                st.warning("Informe uma senha (mín. 6 caracteres).")
            else:
                try:
                    _signin(email, pwd)
                    # garante sessão e redireciona
                    if _user():
                        st.session_state.auth_ok = True
                        try:
                            st.switch_page("pages/📊_Dashboards.py")
                        except Exception:
                            st.switch_page("pages/_Dashboards.py")
                    else:
                        st.error("Não foi possível autenticar. Verifique suas credenciais.")
                except Exception as e:
                    st.error(f"Falha no login: {e}")

    with c2:
        if st.button("Criar conta", use_container_width=True):
            if not email:
                st.warning("Informe um e-mail.")
            elif not pwd or len(pwd) < 6:
                st.warning("Defina uma senha com pelo menos 6 caracteres.")
            else:
                try:
                    _signup(email, pwd)
                    st.success("Conta criada. Confirme o e-mail (se exigido) e entre.")
                except Exception as e:
                    st.error(f"Falha ao criar conta: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# Fecha containers raiz
st.markdown('</div></div>', unsafe_allow_html=True)

# Rodapé "powered by"
st.markdown(
    '<div class="ff-powered">Powered by <img src="assets/logo_automaGO.png" alt="automaGO"/></div>',
    unsafe_allow_html=True
)
