# app.py — Family Finance (Login revisto P0)
# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
from supabase_client import get_supabase
from ff_shared import bootstrap

st.set_page_config(page_title="Family Finance — Login", layout="wide", page_icon="💸")

# ===== CSS + Estrutura de Grid (sem rolagem, fundo aplicado) =====
st.markdown(
    """
<style>
/* Remove header/footer/sidebar no login */
header[data-testid="stHeader"]{display:none;}
section[data-testid="stSidebar"]{display:none;}
footer{visibility:hidden;}

/* Altura total e sem padding padrão */
html, body, [data-testid="stAppViewContainer"]{height:100%;}
[data-testid="stAppViewContainer"] > .main {padding:0 !important; height:100%;}
.main .block-container{padding:0 !important; height:100%;}

/* Grid de duas colunas preenchendo a tela */
.ff-login-grid{
  display:grid;
  grid-template-columns: 1.1fr 1fr;
  height:100vh;
  width:100vw;
  overflow:hidden;
}

/* Coluna esquerda: background */
.ff-left{
  position:relative;
  background: #171a1f url('assets/Backgroud_FF.png') center/cover no-repeat fixed;
}

/* Logo e powered-by */
.ff-brand{
  position:absolute; top:8%; left:6%;
  display:flex; align-items:center; gap:14px;
}
.ff-brand img{ height:72px; }

.ff-powered{
  position:absolute; left:10px; bottom:6px;
  font-size:11px; opacity:.65; color:#dfe7ff;
}
.ff-powered img{height:14px; vertical-align:middle; opacity:.85;}

/* Coluna direita: formulário */
.ff-right{
  display:flex; align-items:center; justify-content:center;
  padding:24px;
  background: linear-gradient(180deg,#0b2038 0%,#0e2744 100%);
  color:#e8f0ff;
}
.ff-card{
  width:min(460px, 92vw);
  background:rgba(255,255,255,.06);
  backdrop-filter: blur(6px);
  border:1px solid rgba(255,255,255,.12);
  border-radius:18px; padding:22px 22px 16px 22px;
  box-shadow:0 10px 30px rgba(0,0,0,.25);
}
.ff-card h1{ font-size:1.25rem; margin:0 0 8px 0; }
.ff-muted{ font-size:.92rem; opacity:.85; margin-bottom:14px; }

.ff-actions{ display:flex; gap:10px; }
.ff-actions .stButton>button{ flex:1; border-radius:10px; font-weight:700; }

/* Responsivo */
@media (max-width: 980px){
  .ff-login-grid{ grid-template-columns: 1fr; }
  .ff-left{ display:none; }
}
</style>

<div class="ff-login-grid">
  <div class="ff-left">
    <div class="ff-brand">
      <img src="assets/logo_family_finance.png" alt="Family Finance"/>
    </div>
    <div class="ff-powered">
      powered by <img src="assets/logo_automaGO.png" alt="AutomaGO"/>
    </div>
  </div>
  <div class="ff-right">
    <div class="ff-card">
      <h1>Bem-vindo(a) 👋</h1>
      <div class="ff-muted">Controle familiar de receitas e despesas com simplicidade e foco.</div>
      <div id="ff-form-anchor"></div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ===== Formulário no container (evita quebrar layout da grid) =====
with st.container():
    st.write("")  # espaçador visual
    s = get_supabase()

    # Form padrão com ENTER para enviar
    with st.form("ff_login_form", clear_on_submit=False):
        email = st.text_input("E-mail", key="ff_email")
        pwd = st.text_input("Senha", type="password", key="ff_pwd")

        colA, colB = st.columns(2)
        with colA:
            do_login = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        with colB:
            do_signup = st.form_submit_button("Criar conta", use_container_width=True)

    def _valid_inputs() -> bool:
        if not email or "@" not in email:
            st.warning("Informe um e-mail válido.")
            return False
        if not pwd or len(pwd) < 6:
            st.warning("A senha deve ter pelo menos 6 caracteres.")
            return False
        return True

    def _to_entrada():
        # Caminho relativo exato esperado pelo Streamlit
        st.switch_page("pages/1_Entrada.py")

    # ===== Ações =====
    if do_login:
        if _valid_inputs():
            try:
                st.toast("Entrando...", icon="🔐")
                auth = s.auth.sign_in_with_password({"email": email.strip(), "password": pwd})
                user = getattr(auth, "user", None)
                if user and user.id:
                    bootstrap(user.id)
                    _to_entrada()
                else:
                    st.error("Não foi possível autenticar. Verifique e-mail e senha.")
            except Exception as e:
                st.error(f"Falha no login: {e}")

    if do_signup:
        if _valid_inputs():
            try:
                st.toast("Criando sua conta...", icon="🆕")
                s.auth.sign_up({"email": email.strip(), "password": pwd})
                # Opcional: auto-login após cadastro
                auth = s.auth.sign_in_with_password({"email": email.strip(), "password": pwd})
                user = getattr(auth, "user", None)
                if user and user.id:
                    bootstrap(user.id)
                    _to_entrada()
                else:
                    st.success("Conta criada. Verifique seu e-mail para confirmar o cadastro.")
            except Exception as e:
                st.error(f"Falha ao criar conta: {e}")
