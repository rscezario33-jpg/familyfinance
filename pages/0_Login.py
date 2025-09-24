# pages/0_Login.py — Family Finance • Responsive Login with Supabase + Glass Layout
from __future__ import annotations

import base64
from pathlib import Path
import streamlit as st

from supabase_client import get_supabase, FFConfigError  # project integration
from ff_shared import bootstrap  # project integration

st.set_page_config(
    page_title="Login • Family Finance",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ------------------------------------------------------------
# Paths / Brand
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
ASSETS   = BASE_DIR / "assets"

def pick(*names: str) -> Path | None:
    for n in names:
        p = ASSETS / n
        if p.exists():
            return p
    return None

LOGO = pick("logo_family_finance.png", "logo_family_finance.jpg", "logo.png")
BG   = pick("Backgroud_FF.png", "Background_FF.png", "background.png")

BRAND_ORANGE = "#F37321"

# ------------------------------------------------------------
# CSS helpers — Responsive adjustments for all screens
# ------------------------------------------------------------
def _b64(p: Path | None) -> str | None:
    if not p: return None
    try:
        return base64.b64encode(p.read_bytes()).decode("ascii")
    except Exception:
        return None

def inject_css_login():
    """Responsive login: background, glass card, and responsive layout."""
    bg64 = _b64(BG)
    if bg64:
        bg_css = f'''.stApp{{background:url("data:image/png;base64,{bg64}") no-repeat center/cover fixed;}}'''
    else:
        bg_css = '''.stApp{background:linear-gradient(120deg,#0B2038,#0E2744);}'''

    st.markdown(f"""
<style>
  header,#MainMenu,footer{{visibility:hidden;}}
  section[data-testid='stSidebar']{{display:none;}}
  {bg_css}
  html,body,.stApp{{height:100%;}}

  .block-container {{
      min-height:100vh;
      padding:0 5vw !important;
      /* display:flex; */
      /* align-items:center; */
      /* justify-content:center; */
      /* overflow:hidden; */
  }}
  .wrap-max {{
      width:min(1200px,96vw);
      display: flex;
      flex-direction: row;
      gap: 5vw;
      justify-content: center;
      align-items: center;
  }}
  /* Mobile responsive styles */
  @media (max-width: 800px) {{
    .wrap-max {{
      flex-direction: column !important;
      gap: 36px !important;
    }}
    .logo img {{
      width: clamp(160px,35vw,240px) !important;
    }}
    .glass {{
      width: 100% !important;
      max-width: 450px !important;
      margin: 0 auto !important;
      padding: 18px 8px !important;
    }}
  }}
  @media (max-width: 480px) {{
    .block-container {{
      padding: 0 2vw !important;
    }}
    .wrap-max {{
      gap: 20px !important;
    }}
    .logo img {{
      width: 80vw !important;
      min-width: 120px !important;
      max-width: 220px !important;
    }}
    .glass {{
      padding: 12px 4px !important;
    }}
  }}
  .logo img{{
    width:clamp(200px,28vw,380px);
    filter:drop-shadow(0 24px 48px rgba(0,0,0,.35));
    display:block;
    margin:0 auto 12px auto;
  }}
  .glass{{
    background:rgba(10,25,40,.44);
    -webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);
    border:1px solid rgba(255,255,255,.45);
    border-radius:22px;
    box-shadow:0 24px 60px rgba(0,0,0,.35);
    padding:24px;
    color:#fff;
    width: 375px;
    max-width: 98vw;
    margin: 0 auto;
  }}
  .glass h3{{margin:0 0 10px;font-weight:800;text-shadow:0 2px 8px rgba(0,0,0,.35);}}
  .glass [data-testid="stCaptionContainer"]{{opacity:.98;text-shadow:0 1px 6px rgba(0,0,0,.35);}}
  .stTextInput>div>div>input,.stPassword>div>div>input{{height:46px;font-size:16px;}}
  .stButton>button{{
    height:46px;font-size:16px;background:{BRAND_ORANGE}!important;color:#fff;border:none;border-radius:12px;
    box-shadow:0 6px 18px rgba(243,115,33,.35); font-weight:800;
  }}
  div[data-testid="stVerticalBlock"]>div:empty{{display:none;}}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# Supabase client (connection)
# ------------------------------------------------------------
supabase_ok = True
s = None
config_msg = ""
try:
    s = get_supabase()
except FFConfigError as e:
    supabase_ok = False
    config_msg = str(e)
except Exception as e:
    supabase_ok = False
    config_msg = f"Erro inesperado: {e}"

# ------------------------------------------------------------
# UI — Responsive LOGIN
# ------------------------------------------------------------
inject_css_login()
st.markdown('<div class="wrap-max">', unsafe_allow_html=True)
# Responsive: use columns only for wide screens, stack otherwise (handled by CSS)
c1, c2 = st.columns([1, 1], gap="large")

with c1:
    st.markdown('<div class="logo">', unsafe_allow_html=True)
    if LOGO: st.image(str(LOGO))
    else: st.markdown('<h1 style="color:#fff;font-weight:900;margin:0;">Family Finance</h1>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("<h3>Entrar no Family Finance</h3>", unsafe_allow_html=True)
    st.caption("Use suas credenciais para continuar.")
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("E-mail", placeholder="seu e-mail")
        password = st.text_input("Senha", type="password", placeholder="sua senha")
        a, b = st.columns([1, 1])
        btn_login  = a.form_submit_button("Entrar", type="primary", use_container_width=True)
        btn_signup = b.form_submit_button("Criar conta", use_container_width=True)
    feedback = st.empty()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# Supabase config missing
if not supabase_ok:
    st.warning("Configuração do Supabase ausente.")
    with st.expander("Como configurar (Streamlit Cloud ou local)"):
        st.code(
            """[supabase]
url = "https://uqblgzkffoyotqgsdski.supabase.co"
# aceite 'key' ou 'anon_key'
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVxYmxnemtmZm95b3RxZ3Nkc2tpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTg2NTIwNDcsImV4cCI6MjA3NDIyODA0N30.jZVyC-hAZLgxSCeoUxPlHNfFg8dZKEsYqJlpPn7NPKo"
""", language="toml")
    st.error(config_msg)
    st.stop()

def _valid():
    if not email or "@" not in email:
        feedback.warning("Informe um e-mail válido."); return False
    if not password or len(password) < 6:
        feedback.warning("A senha deve ter pelo menos 6 caracteres."); return False
    return True

def _go_home():
    st.switch_page("pages/1_Entrada.py")

# Actions
if btn_login and _valid():
    try:
        st.toast("Entrando...", icon="🔐")
        auth = s.auth.sign_in_with_password({"email": email.strip(), "password": password})
        user = getattr(auth, "user", None)
        if user and user.id:
            bootstrap(user.id)
            _go_home()
        else:
            feedback.error("Não foi possível autenticar. Verifique credenciais.")
    except Exception as e:
        feedback.error(f"Falha no login: {e}")

if btn_signup and _valid():
    try:
        st.toast("Criando sua conta...", icon="🆕")
        s.auth.sign_up({"email": email.strip(), "password": password})
        # opcional: auto-login
        auth = s.auth.sign_in_with_password({"email": email.strip(), "password": password})
        user = getattr(auth, "user", None)
        if user and user.id:
            bootstrap(user.id)
            _go_home()
        else:
            feedback.success("Conta criada. Verifique seu e-mail para confirmar.")
    except Exception as e:
        feedback.error(f"Falha ao criar conta: {e}")
