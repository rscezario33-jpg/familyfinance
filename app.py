# app.py — Family Finance (Login fullscreen, sem page_link)
from __future__ import annotations
import streamlit as st
from ff_shared import inject_css, sb, user, bootstrap

st.set_page_config(page_title="Family Finance — Login", layout="wide")
inject_css()

# ======= Se já logado, tenta ir para Entrada =======
u = user()
if u:
    try:
        bootstrap(u.id)
        st.switch_page("pages/1_Entrada.py")
    except Exception:
        # sem page_link para evitar KeyError
        st.success("Você já está logado. Abra o menu de páginas (☰) e entre em ‘Entrada’.")
    st.stop()

# ======= CSS do mockup =======
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] { height: 100%; }
div.login-bg {
  min-height: 100vh; display:flex; align-items:center; justify-content:center;
  background: radial-gradient(1200px 600px at 50% 10%, #37b34a 0%, #0c7a3c 25%, #0b2038 70%);
}
div.login-card {
  width: 460px; max-width: 92%;
  background: rgba(10,20,30,.55); backdrop-filter: blur(6px);
  border-radius: 18px; border: 1px solid rgba(255,255,255,.08);
  box-shadow: 0 18px 50px rgba(0,0,0,.45); padding: 28px 26px 24px; color: #eaf3ff;
}
.logo-wrap { text-align:center; margin-top: -6px; }
.logo-wrap img { width: 130px; height:auto; }
.login-title { font-size: 42px; font-weight: 800; text-align:center; letter-spacing:.5px; margin: 8px 0 22px; }
.login-input .stTextInput>div>div, .login-input .stPassword>div>div {
  background: rgba(255,255,255,.08)!important; border: 1px solid rgba(255,255,255,.15)!important; border-radius: 12px!important;
}
.login-input input { color:#eaf3ff!important; }
.login-actions { display:flex; align-items:center; justify-content:space-between; font-size:14px; opacity:.9; margin: 6px 0 2px; }
.login-actions a { color:#84ff6a; text-decoration:none; font-weight:600; }
.login-button .stButton>button {
  width:100%; border-radius:12px; padding:.85rem;
  background:#0f233d; border:1px solid rgba(255,255,255,.2);
  color:#fff; font-size:20px; font-weight:800;
}
.login-button .stButton>button:hover { transform:translateY(-1px); }
</style>
""", unsafe_allow_html=True)

# ======= Layout =======
st.markdown('<div class="login-bg"><div class="login-card">', unsafe_allow_html=True)
st.markdown('<div class="logo-wrap"><img src="assets/logo_family_finance.png"/></div>', unsafe_allow_html=True)
st.markdown('<div class="login-title">Family Finance</div>', unsafe_allow_html=True)

st.markdown('<div class="login-input">', unsafe_allow_html=True)
email = st.text_input("Username", placeholder="you@email.com", key="login_email")
pwd = st.text_input("Password", placeholder="••••••••", type="password", key="login_pwd")
st.markdown('</div>', unsafe_allow_html=True)

c1, c2 = st.columns([1, 1])
with c1:
    forgot = st.button("Forgot password?")
with c2:
    signup = st.button("Sign Up")

st.markdown('<div class="login-button">', unsafe_allow_html=True)
signin = st.button("Sign in", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ======= Ações =======
def go_home():
    try:
        st.switch_page("pages/1_Entrada.py")
    except Exception:
        # nada de page_link aqui; só instrução segura
        st.success("Login ok! Abra o menu de páginas (☰) e vá para ‘Entrada’.")
        # como fallback, força um rerun (às vezes o multipage aparece após primeiro run)
        st.experimental_rerun()

if signin:
    try:
        sb.auth.sign_in_with_password({"email": email.strip(), "password": pwd})
        u2 = user()
        if u2:
            bootstrap(u2.id)
            go_home()
        else:
            st.error("Falha ao autenticar.")
    except Exception as e:
        st.error(f"Falha no login: {e}")

if signup:
    try:
        sb.auth.sign_up({"email": email.strip(), "password": pwd})
        st.info("Conta criada. Confirme o e-mail (se exigido) e entre.")
    except Exception as e:
        st.error(f"Falha ao criar conta: {e}")

if forgot:
    if not email.strip():
        st.warning("Informe seu e-mail acima para enviar o link de redefinição.")
    else:
        try:
            redirect = (st.secrets.get("app", {}).get("url") + "/") if hasattr(st, "secrets") else None
            opts = {"email_redirect_to": redirect} if redirect else None
            if opts: sb.auth.reset_password_email(email.strip(), options=opts)
            else:    sb.auth.reset_password_email(email.strip())
            st.success("Se o e-mail existir, um link de redefinição foi enviado.")
        except Exception as e:
            st.error(f"Erro ao solicitar redefinição: {e}")

st.markdown('</div></div>', unsafe_allow_html=True)
