# app.py — Family Finance (Login PRO: background fix, 2 colunas, sem rolagem, redirect direto)
from __future__ import annotations
import streamlit as st
from ff_shared import inject_css, sb, user, bootstrap

st.set_page_config(page_title="Family Finance — Login", layout="wide")

# se já estiver logado, entra direto
_u = user()
if _u:
    try:
        bootstrap(_u.id)
        st.switch_page("pages/1_Entrada.py")
    except Exception:
        pass  # fallback silencioso

# CSS base do projeto
inject_css()

# ===== CSS específico do login =====
st.markdown(f"""
<style>
/* remove header/toolbar/rodapé do Streamlit */
header[data-testid="stHeader"] {{ display:none; }}
section[data-testid="stSidebar"] {{ display:none; }}
footer {{ visibility:hidden; }}

/* ocupar viewport e bloquear rolagem */
html, body, [data-testid="stAppViewContainer"] {{
  height: 100%;
  overflow: hidden;
}}

/* fundo com sua imagem exata (sem 'n') */
[data-testid="stAppViewContainer"] {{
  background-image: url('assets/Backgroud_FF.png');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}}

/* grid 2 colunas, full height */
.ff-login-shell {{
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.25fr 1fr;
  align-items: center;
  gap: 56px;
  padding: 48px 6vw;
  box-sizing: border-box;
}}

/* painel esquerdo (marca) */
.ff-brand {{
  display:flex; align-items:center; gap:24px;
  background: rgba(0, 18, 35, .38);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 18px;
  padding: 28px 30px;
  color:#eaf3ff;
  backdrop-filter: blur(6px);
  box-shadow: 0 24px 60px rgba(0,0,0,.45);
}}
.ff-brand img {{ width: 140px; height:auto; }}
.ff-title {{ font-size: 48px; font-weight: 900; line-height: 1.05; margin: 0; }}
.ff-sub   {{ opacity:.9; margin-top:8px; font-size:14px; }}

/* painel direito (form) */
.ff-form {{
  width: 460px; max-width: 92%;
  background: rgba(0, 18, 35, .62);
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 18px;
  padding: 24px 22px 18px;
  color: #eaf3ff;
  backdrop-filter: blur(8px);
  box-shadow: 0 24px 60px rgba(0,0,0,.45);
}}
.ff-form h4 {{ margin: 0 0 14px 0; font-weight:800; }}

/* inputs escuros */
.ff-form .stTextInput>div>div,
.ff-form .stPassword>div>div {{
  background: rgba(255,255,255,.06) !important;
  border: 1px solid rgba(255,255,255,.16) !important;
  border-radius: 12px !important;
}}
.ff-form input {{ color:#eaf3ff !important; }}

/* botões */
.ff-form .stButton>button {{
  width: 100%;
  border-radius: 12px;
  padding: .85rem;
  font-weight: 800;
  border: 1px solid rgba(255,255,255,.25);
}}
.ff-form .primary>button {{ background:#0ea5e9; color:#fff; border-color:#0ea5e9; }}
.ff-form .primary>button:hover {{ transform: translateY(-1px); background:#0284c7; border-color:#0284c7; }}
.ff-form .ghost>button    {{ background: transparent; color:#eaf3ff; }}
.ff-form .ghost>button:hover {{ background: rgba(255,255,255,.08); }}

/* powered by fixo no canto inferior esquerdo */
.ff-powered {{
  position: fixed; left: 14px; bottom: 10px;
  display:flex; align-items:center; gap:8px;
  font-size: 11.5px; opacity:.9; color:#eaf3ff;
  text-shadow:0 1px 8px rgba(0,0,0,.5);
}}
.ff-powered img {{ height: 16px; width:auto; opacity:.95; }}
</style>
""", unsafe_allow_html=True)

# ===== layout 2 colunas =====
st.markdown('<div class="ff-login-shell">', unsafe_allow_html=True)

# coluna esquerda (logo grande + título)
st.markdown(
    """
    <div class="ff-brand">
      <img src="assets/logo_family_finance.png" />
      <div>
        <h1 class="ff-title">Family<br/>Finance</h1>
        <div class="ff-sub">Gestão financeira familiar — moderna, segura e precisa.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# coluna direita (form)
st.markdown('<div class="ff-form">', unsafe_allow_html=True)
st.markdown("<h4>Acessar sua conta</h4>", unsafe_allow_html=True)

email = st.text_input("E-mail", key="ff_login_email", placeholder="voce@email.com")
pwd   = st.text_input("Senha",  key="ff_login_pwd", type="password", placeholder="••••••••")

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    enter = st.button("Entrar", key="ff_btn_login", use_container_width=True, type="primary")
with col_btn2:
    signup = st.button("Criar conta", key="ff_btn_signup", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)  # fecha ff-form
st.markdown("</div>", unsafe_allow_html=True)  # fecha shell

# powered by
st.markdown(
    """
    <div class="ff-powered">
      <span>powered by</span>
      <img src="assets/logo_automaGO.png" />
    </div>
    """,
    unsafe_allow_html=True
)

# ===== helpers =====
def _validate():
    if not email.strip():
        st.warning("Informe seu e-mail.")
        return False
    if not pwd:
        st.warning("Informe sua senha.")
        return False
    if len(pwd) < 6:
        st.warning("A senha deve ter pelo menos 6 caracteres.")
        return False
    return True

def _go_home(uid: str):
    # entra direto na page 1
    bootstrap(uid)
    st.switch_page("pages/1_Entrada.py")

# ===== ações =====
if enter:
    if _validate():
        try:
            sb.auth.sign_in_with_password({"email": email.strip(), "password": pwd})
            u2 = user()
            if u2:
                _go_home(u2.id)   # REDIRECT DIRETO
            else:
                st.error("Não foi possível autenticar. Verifique e-mail e senha.")
        except Exception as e:
            st.error(f"Falha no login: {e}")

if signup:
    if _validate():
        try:
            # cria conta; se sua política exigir confirmação, o usuário precisará confirmar por e-mail
            sb.auth.sign_up({"email": email.strip(), "password": pwd})
            st.success("Conta criada. Se a confirmação por e-mail estiver ativada, confirme para poder entrar.")
        except Exception as e:
            st.error(f"Falha ao criar conta: {e}")
