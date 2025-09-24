# pages/0_Login.py — Family Finance • Login (ajustes anti-rolagem + logo menor)
from __future__ import annotations

import base64
from pathlib import Path
import streamlit as st

from supabase_client import get_supabase, FFConfigError
from ff_shared import bootstrap

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
# CSS helpers
# ------------------------------------------------------------
def _b64(p: Path | None) -> str | None:
    if not p: return None
    try:
        return base64.b64encode(p.read_bytes()).decode("ascii")
    except Exception:
        return None

def inject_css_login():
    """Tela de login (sem rolagem), logo menor e card glass alinhado."""
    bg64 = _b64(BG)
    if bg64:
        bg_css = f'''.stApp{{background:url("data:image/png;base64,{bg64}") no-repeat center/cover fixed;}}'''
    else:
        bg_css = '''.stApp{background:linear-gradient(120deg,#0B2038,#0E2744);}'''

    st.markdown(f"""
<style>
  /* Some tudo que gera barra e mantém 100vh real */
  html, body {{ height:100%; overflow:hidden; }}
  .stApp {{ height:100%; overflow:hidden; }}
  header,#MainMenu,footer{{display:none !important;}}
  section[data-testid='stSidebar']{{display:none !important;}}

  {bg_css}

  /* Remove paddings da view e garante 100vh */
  [data-testid="stAppViewContainer"] > .main {{
      padding:0 !important; height:100%;
  }}
  .block-container {{
      padding:0 !important; margin:0 !important; height:100%;
  }}

  /* GRID 2 colunas ocupando a tela inteira */
  .wrap-screen {{
      display:grid; grid-template-columns: 1.1fr 1fr;
      height:100vh; width:100vw; overflow:hidden;
  }}

  /* Coluna esquerda: logo */
  .left {{
      display:flex; align-items:center; justify-content:flex-start;
  }}
  .left-inner {{ margin-left:6vw; }}
  /* LOGO MENOR (clamp reduzido) */
  .left-inner img {{
      width:clamp(180px, 24vw, 300px);
      filter:drop-shadow(0 24px 48px rgba(0,0,0,.35));
      margin:0;
  }}

  /* Coluna direita: card centralizado */
  .right {{
      display:flex; align-items:center; justify-content:center;
      background: linear-gradient(180deg, rgba(11,32,56,.35), rgba(14,39,68,.55));
      padding: 0 28px;
      color:#e8f0ff;
  }}
  .glass {{
      width:min(480px, 92vw);
      background:rgba(10,25,40,.44);
      -webkit-backdrop-filter:blur(14px); backdrop-filter:blur(14px);
      border:1px solid rgba(255,255,255,.45);
      border-radius:22px; box-shadow:0 24px 60px rgba(0,0,0,.35);
      padding:22px 22px 18px;
      margin:0;  /* sem margens extras */
  }}
  .glass h3{{margin:0 0 10px;font-weight:800;text-shadow:0 2px 8px rgba(0,0,0,.35);}}
  .glass [data-testid="stCaptionContainer"]{{opacity:.98;text-shadow:0 1px 6px rgba(0,0,0,.35);}}

  /* Inputs e botões */
  .stTextInput>div>div>input,.stPassword>div>div>input{{height:46px;font-size:16px;}}
  .stButton>button{{
      height:46px;font-size:16px;background:{BRAND_ORANGE}!important;color:#fff;border:none;border-radius:12px;
      box-shadow:0 6px 18px rgba(243,115,33,.35); font-weight:800;
  }}

  /* Tira espaços “fantasmas” do Streamlit */
  div[data-testid="stVerticalBlock"]>div:empty{{display:none;}}
  .element-container:has(> .stAlert) {{ margin-top:8px; }}

  /* Responsivo: em telas menores, só o form (sem logo) */
  @media (max-width: 980px) {{
     .wrap-screen {{ grid-template-columns: 1fr; }}
     .left {{ display:none; }}
  }}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# Supabase client (sem quebrar a UI se faltar credencial)
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
# UI — LOGIN (estrutura HTML fixa + widgets)
# ------------------------------------------------------------
inject_css_login()

st.markdown(
    """
<div class="wrap-screen">
  <div class="left">
    <div class="left-inner">
      <img src="assets/logo_family_finance.png" alt="Family Finance"/>
    </div>
  </div>
  <div class="right">
    <div class="glass">
      <h3>Entrar no Family Finance</h3>
      <div class="ff-muted">Use suas credenciais para continuar.</div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Renderiza o form dentro do card, sem criar blocos acima/abaixo
card = st.container()
with card:
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("E-mail", placeholder="seu e-mail")
        password = st.text_input("Senha", type="password", placeholder="sua senha")
        c1, c2 = st.columns(2)
        btn_login  = c1.form_submit_button("Entrar", type="primary", use_container_width=True)
        btn_signup = c2.form_submit_button("Criar conta", use_container_width=True)
    feedback = st.empty()

# Sem secrets? mostra instruções compactas (não poluir layout)
if not supabase_ok:
    with st.expander("⚙️ Como configurar o Supabase (clique)"):
        st.code(
            """[supabase]
url = "https://SEU-PROJETO.supabase.co"
# aceita 'key' ou 'anon_key'
key = "SUA_KEY_AQUI"
""",
            language="toml",
        )
        st.text(config_msg)
    st.stop()

def _valid():
    if not email or "@" not in email:
        feedback.warning("Informe um e-mail válido."); return False
    if not password or len(password) < 6:
        feedback.warning("A senha deve ter pelo menos 6 caracteres."); return False
    return True

def _go_home():
    st.switch_page("pages/1_Entrada.py")

# Ações
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
        auth = s.auth.sign_in_with_password({"email": email.strip(), "password": password})
        user = getattr(auth, "user", None)
        if user and user.id:
            bootstrap(user.id); _go_home()
        else:
            feedback.success("Conta criada. Verifique seu e-mail para confirmar.")
    except Exception as e:
        feedback.error(f"Falha ao criar conta: {e}")
