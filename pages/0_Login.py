# pages/0_Login.py — Family Finance • Login (grid 100vh, glass card, sem ruídos)
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

# --------------------------------------------------------------------
# Paths / Assets
# --------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
ASSETS   = BASE_DIR / "assets"

def pick(*names: str) -> Path | None:
    for n in names:
        p = ASSETS / n
        if p.exists():
            return p
    return None

LOGO = pick("logo_family_finance.png", "logo.png")
BG   = pick("Backgroud_FF.png", "Background_FF.png", "background.png")

BRAND_ORANGE = "#F37321"

def _b64(p: Path | None) -> str | None:
    if not p: return None
    try:
        return base64.b64encode(p.read_bytes()).decode("ascii")
    except Exception:
        return None

# --------------------------------------------------------------------
# CSS — grid tela cheia (logo esquerda / form direita), sem rolagem
# --------------------------------------------------------------------
def inject_css_login():
    bg64 = _b64(BG)
    bg_css = (
        f'.stApp{{background:url("data:image/png;base64,{bg64}") no-repeat center/cover fixed;}}'
        if bg64 else
        '.stApp{background:linear-gradient(120deg,#0B2038,#0E2744);}'
    )
    st.markdown(
        f"""
<style>
  /* Limpa header, sidebar e footer só no login */
  header,#MainMenu,footer{{visibility:hidden;}}
  section[data-testid='stSidebar']{{display:none;}}

  {bg_css}

  html,body,.stApp{{height:100%;}}
  /* Zera paddings e garante 100vh */
  [data-testid="stAppViewContainer"] > .main {{ padding:0 !important; height:100%; }}
  .block-container {{
     padding:0 !important; margin:0 auto; height:100%;
  }}

  /* GRID 2 colunas */
  .ff-grid {{
    display:grid; grid-template-columns: 1.1fr 1fr;
    gap:0; height:100vh; width:100vw; overflow:hidden;
    background: radial-gradient(1200px 800px at 10% 15%, rgba(255,255,255,.06), transparent 60%);
  }}

  /* Coluna Esquerda (logo grande, centralizada verticalmente) */
  .ff-left {{ position:relative; display:flex; align-items:center; }}
  .ff-left-inner {{ margin-left:6vw; }}
  .ff-left img {{ width:min(36vw, 440px); max-width:440px; filter:drop-shadow(0 24px 48px rgba(0,0,0,.35)); }}
  .ff-powered {{
     position:absolute; left:16px; bottom:10px; font-size:11px; opacity:.70; color:#dfe7ff;
  }}
  .ff-powered img {{ height:14px; vertical-align:middle; opacity:.9; }}

  /* Coluna Direita (card glass centralizado) */
  .ff-right {{
     display:flex; align-items:center; justify-content:center;
     padding:28px; background: linear-gradient(180deg, rgba(11,32,56,.35), rgba(14,39,68,.55));
     color:#e8f0ff;
  }}
  .ff-card {{
     width: min(480px, 92vw);
     background: rgba(10,25,40,.48);
     -webkit-backdrop-filter: blur(14px); backdrop-filter: blur(14px);
     border: 1px solid rgba(255,255,255,.32);
     border-radius: 22px;
     box-shadow: 0 28px 64px rgba(0,0,0,.35);
     padding: 22px 22px 18px;
  }}
  .ff-card h1 {{ font-size: 1.22rem; margin:0 0 8px 0; font-weight:800; text-shadow:0 2px 8px rgba(0,0,0,.35); }}
  .ff-muted {{ font-size:.92rem; opacity:.88; margin-bottom:14px; }}

  /* Inputs/Botões */
  .stTextInput>div>div>input, .stPassword>div>div>input {{ height:46px; font-size:16px; }}
  .stButton>button {{
     height:46px; font-size:16px; font-weight:800; border:none; border-radius:12px;
     background:{BRAND_ORANGE} !important; color:#fff !important;
     box-shadow:0 6px 18px rgba(243,115,33,.35);
  }}

  /* Some espaços fantasmas do Streamlit */
  div[data-testid="stVerticalBlock"]>div:empty{{display:none;}}
  .element-container:has(> .stAlert) {{ margin-top: 8px; }}
  /* Responsivo: em <= 980px vira 1 coluna (só o form) */
  @media (max-width: 980px) {{
     .ff-grid {{ grid-template-columns: 1fr; }}
     .ff-left {{ display:none; }}
  }}
</style>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------
# Supabase (sem quebrar UI se faltar secret)
# --------------------------------------------------------------------
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

# --------------------------------------------------------------------
# UI
# --------------------------------------------------------------------
inject_css_login()

# Estrutura HTML da grade
st.markdown(
    """
<div class="ff-grid">
  <div class="ff-left">
     <div class="ff-left-inner">
       <img src="assets/logo_family_finance.png" alt="Family Finance"/>
     </div>
     <div class="ff-powered">powered by <img src="assets/logo_automaGO.png" alt="AutomaGO"/></div>
  </div>
  <div class="ff-right">
     <div class="ff-card">
       <h1>Entrar no Family Finance</h1>
       <div class="ff-muted">Use suas credenciais para continuar.</div>
     </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Após o HTML acima, criamos os widgets (card container)
card = st.container()
with card:
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("E-mail", placeholder="seu e-mail")
        password = st.text_input("Senha", type="password", placeholder="sua senha")
        c1, c2 = st.columns(2)
        btn_login  = c1.form_submit_button("Entrar", type="primary", use_container_width=True)
        btn_signup = c2.form_submit_button("Criar conta", use_container_width=True)
    feedback = st.empty()

# Falta de credenciais: instrução enxuta, sem ocupar a tela toda
if not supabase_ok:
    with st.expander("⚙️ Configurar Supabase (clique para ver)", expanded=False):
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
