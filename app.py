# app.py — Family Finance (Login PRO: background responsivo, 2 colunas, sem rolagem, redirect robusto)
from __future__ import annotations
import os
import streamlit as st
from ff_shared import inject_css, sb, user, bootstrap

st.set_page_config(page_title="Family Finance — Login", layout="wide")

# ===== util =====
def switch_to_entrada():
    """Redireciona para 'Entrada' tentando variações de caminho/rotulo."""
    base = os.path.dirname(os.path.abspath(__file__))
    exists_default = os.path.exists(os.path.join(base, "pages", "1_Entrada.py"))
    targets = [
        "pages/1_Entrada.py",  # padrão
        "1_Entrada",           # por rótulo (algumas versões aceitam)
        "Entrada",
        "pages/Entrada.py",    # caso tenha sido renomeado
    ]
    for t in targets:
        try:
            st.switch_page(t)
            return
        except Exception:
            pass
    if not exists_default:
        st.error("Arquivo **pages/1_Entrada.py** não encontrado. Verifique nome e pasta.")
    else:
        st.error("Não consegui abrir a página **Entrada**. Abra pelo menu de páginas para confirmar que está listada.")

# se já houver sessão válida, entra direto
_u = user()
if _u:
    try:
        bootstrap(_u.id)
        switch_to_entrada()
    except Exception:
        pass

# ===== estilo base do projeto (sidebar etc.) =====
inject_css()

# ===== CSS do login (remove paddings, sem rolagem, background correto) =====
st.markdown("""
<style>
/* Oculta header/rodapé e qualquer sidebar */
header[data-testid="stHeader"] { display:none; }
section[data-testid="stSidebar"] { display:none; }
footer { visibility:hidden; }

/* Remove paddings do container principal e evita rolagem */
html, body, [data-testid="stAppViewContainer"] { height: 100%; overflow: hidden; }
[data-testid="stAppViewContainer"] > .main { padding: 0 !important; }
.main .block-container { padding-top: 0 !important; padding-bottom: 0 !important; }

/* Fundo com sua imagem exata */
[data-testid="stAppViewContainer"] {
  background-image: url('assets/Backgroud_FF.png');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

/* Shell em tela cheia (sem scroll) */
.ff-login-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.25fr 1fr;
  align-items: center;
  gap: 56px;
  padding: 48px 6vw;
  box-sizing: border-box;
}

/* Coluna esquerda (marca) */
.ff-brand {
  display:flex; align-items:center; gap:24px;
  background: rgba(0,18,35,.38);
  border:1px solid rgba(255,255,255,.08);
  border-radius:18px;
  padding:28px 30px; color:#eaf3ff;
  backdrop-filter: blur(6px);
  box-shadow:0 24px 60px rgba(0,0,0,.45);
}
.ff-brand img { width: 140px; height:auto; }
.ff-title { font-size: 48px; font-weight: 900; line-height: 1.05; margin: 0; }
.ff-sub { opacity:.9; margin-top:8px; font-size:14px; }

/* Coluna direita (form) */
.ff-form {
  width: 460px; max-width: 92%;
  background: rgba(0,18,35,.62);
  border:1px solid rgba(255,255,255,.12);
  border-radius:18px;
  padding:24px 22px 18px;
  color:#eaf3ff;
  backdrop-filter: blur(8px);
  box-shadow:0 24px 60px rgba(0,0,0,.45);
}
.ff-form h4 { margin: 0 0 14px 0; font-weight: 800; }

/* Inputs escuros */
.ff-form .stTextInput>div>div, .ff-form .stPassword>div>div {
  background: rgba(255,255,255,.06) !important;
  border: 1px solid rgba(255,255,255,.16) !important;
  border-radius: 12px !important;
}
.ff-form input { color:#eaf3ff !important; }

/* Botões */
.ff-form .stButton>button {
  width: 100%;
  border-radius:12px;
  padding:.85rem;
  font-weight: 800;
  border:1px solid rgba(255,255,255,.25);
}
.ff-form .primary>button { background:#0ea5e9; color:#fff; border-color:#0ea5e9; }
.ff-form .primary>button:hover { transform: translateY(-1px); background:#0284c7; border-color:#0284c7; }
.ff-form .ghost>button    { background: transparent; color:#eaf3ff; }
.ff-form .ghost>button:hover { background: rgba(255,255,255,.08); }

/* Powered by */
.ff-powered {
  position: fixed; left: 14px; bottom: 10px;
  display:flex; align-items:center; gap:8px;
  font-size: 11.5px; opacity: .9; color:#eaf3ff;
  text-shadow: 0 1px 8px rgba(0,0,0,.5);
}
.ff-powered img { height: 16px; width: auto; opacity: .95; }

/* ===== Responsividade ===== */
/* Notebooks menores */
@media (max-width: 1200px) {
  .ff-login-shell { gap: 40px; grid-template-columns: 1.1fr 1fr; padding: 32px 4vw; }
  .ff-brand img { width:120px; }
  .ff-title { font-size: 42px; }
}
/* Tablets */
@media (max-width: 900px) {
  .ff-login-shell { grid-template-columns: 1fr; gap: 24px; justify-items: start; }
  .ff-form { width: 520px; max-width: 96%; }
}
/* Celulares */
@media (max-width: 600px) {
  .ff-brand { gap:16px; padding:18px; }
  .ff-brand img { width: 90px; }
  .ff-title { font-size: 34px; }
  .ff-form { width: 100%; max-width: calc(100vw - 32px); padding:18px 16px; }
  .ff-login-shell { padding: 18px; gap: 18px; }
}
</style>
""", unsafe_allow_html=True)

# ===== layout =====
st.markdown('<div class="ff-login-shell">', unsafe_allow_html=True)

# Esquerda — logo + título
st.markdown("""
<div class="ff-brand">
  <img src="assets/logo_family_finance.png" />
  <div>
    <h1 class="ff-title">Family<br/>Finance</h1>
    <div class="ff-sub">Gestão financeira familiar — moderna, segura e precisa.</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Direita — formulário
st.markdown('<div class="ff-form">', unsafe_allow_html=True)
st.markdown("<h4>Acessar sua conta</h4>", unsafe_allow_html=True)

email = st.text_input("E-mail", key="ff_login_email", placeholder="voce@email.com")
pwd   = st.text_input("Senha", key="ff_login_pwd", type="password", placeholder="••••••••")

c1, c2 = st.columns(2)
with c1:
    do_login = st.button("Entrar", key="ff_btn_login", use_container_width=True, type="primary")
with c2:
    do_signup = st.button("Criar conta", key="ff_btn_signup", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)   # fecha ff-form
st.markdown("</div>", unsafe_allow_html=True)   # fecha shell

# Powered by
st.markdown('<div class="ff-powered">powered by <img src="assets/logo_automaGO.png"/></div>', unsafe_allow_html=True)

# ===== validação e redirecionamento =====
def _valid():
    if not email.strip():
        st.warning("Informe seu e-mail."); return False
    if not pwd:
        st.warning("Informe sua senha."); return False
    if len(pwd) < 6:
        st.warning("A senha deve ter pelo menos 6 caracteres."); return False
    return True

if do_login:
    if _valid():
        try:
            sb.auth.sign_in_with_password({"email": email.strip(), "password": pwd})
            me = user()
            if me:
                bootstrap(me.id)
                switch_to_entrada()  # entra direto
            else:
                st.error("Não foi possível autenticar. Verifique e-mail e senha.")
        except Exception as e:
            st.error(f"Falha no login: {e}")

if do_signup:
    if _valid():
        try:
            sb.auth.sign_up({"email": email.strip(), "password": pwd})
            st.success("Conta criada. Se a confirmação por e-mail estiver ativada, confirme para poder entrar.")
        except Exception as e:
            st.error(f"Falha ao criar conta: {e}")
