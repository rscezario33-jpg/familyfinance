# app.py — Family Finance (Login PRO: background, 2 colunas, redirecionamento robusto)
from __future__ import annotations
import os
import streamlit as st
from ff_shared import inject_css, sb, user, bootstrap

st.set_page_config(page_title="Family Finance — Login", layout="wide")
inject_css()

# ==== helpers de navegação ====
def switch_to_entrada():
    """
    Tenta redirecionar para a página 'Entrada' independentemente de variações de nome.
    """
    # Verifica se o arquivo está lá (ajuda a diagnosticar)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    entrada_path = os.path.join(base_dir, "pages", "1_Entrada.py")
    entrada_exists = os.path.exists(entrada_path)

    # alvos possíveis (ordem de tentativa)
    candidates = [
        "pages/1_Entrada.py",  # caminho padrão
        "1_Entrada",           # pelo nome do arquivo (Streamlit aceita em algumas versões)
        "Entrada",             # rótulo derivado
        "pages/Entrada.py",    # caso alguém tenha renomeado o arquivo
    ]
    for target in candidates:
        try:
            st.switch_page(target)
            return
        except Exception:
            pass

    # Se chegou aqui, não conseguiu — dá um diagnóstico claro
    if not entrada_exists:
        st.error(
            "Não encontrei **pages/1_Entrada.py**.\n\n"
            "Verifique se o arquivo existe exatamente com esse nome e dentro da pasta **pages/** "
            "(sensível a maiúsculas/minúsculas e acentos)."
        )
    else:
        st.error(
            "Não consegui alternar para a página **Entrada**.\n"
            "Isso pode ocorrer por diferenças de versão do Streamlit. "
            "Abra o menu de páginas e clique manualmente em **Entrada** para confirmar que está listada."
        )

# ==== se já houver sessão válida, entra direto ====
_u = user()
if _u:
    try:
        bootstrap(_u.id)
        switch_to_entrada()
    except Exception:
        pass

# ==== CSS do login (fundo + layout sem rolagem) ====
st.markdown("""
<style>
header[data-testid="stHeader"] { display:none; }
section[data-testid="stSidebar"] { display:none; }
footer { visibility:hidden; }
html, body, [data-testid="stAppViewContainer"] { height:100%; overflow:hidden; }
[data-testid="stAppViewContainer"] {
  background-image: url('assets/Backgroud_FF.png');
  background-size: cover; background-position: center; background-repeat: no-repeat;
}

/* Grid de duas colunas ocupando a tela */
.ff-login-shell {
  min-height: 100vh;
  display: grid; grid-template-columns: 1.25fr 1fr;
  align-items: center; gap: 56px;
  padding: 48px 6vw; box-sizing: border-box;
}

/* Esquerda (marca) */
.ff-brand {
  display:flex; align-items:center; gap:24px;
  background: rgba(0,18,35,.38); border:1px solid rgba(255,255,255,.08);
  border-radius:18px; padding:28px 30px; color:#eaf3ff;
  backdrop-filter: blur(6px); box-shadow:0 24px 60px rgba(0,0,0,.45);
}
.ff-brand img { width:140px; height:auto; }
.ff-title { font-size:48px; font-weight:900; line-height:1.05; margin:0; }
.ff-sub { opacity:.9; margin-top:8px; font-size:14px; }

/* Direita (form) */
.ff-form {
  width:460px; max-width:92%;
  background: rgba(0,18,35,.62); border:1px solid rgba(255,255,255,.12);
  border-radius:18px; padding:24px 22px 18px; color:#eaf3ff;
  backdrop-filter: blur(8px); box-shadow:0 24px 60px rgba(0,0,0,.45);
}
.ff-form h4 { margin:0 0 14px 0; font-weight:800; }

/* Inputs escuros */
.ff-form .stTextInput>div>div, .ff-form .stPassword>div>div {
  background: rgba(255,255,255,.06) !important;
  border: 1px solid rgba(255,255,255,.16) !important;
  border-radius: 12px !important;
}
.ff-form input { color:#eaf3ff !important; }

/* Botões */
.ff-form .stButton>button {
  width:100%; border-radius:12px; padding:.85rem; font-weight:800;
  border:1px solid rgba(255,255,255,.25);
}
.ff-form .primary>button { background:#0ea5e9; color:#fff; border-color:#0ea5e9; }
.ff-form .primary>button:hover { transform:translateY(-1px); background:#0284c7; border-color:#0284c7; }
.ff-form .ghost>button { background:transparent; color:#eaf3ff; }
.ff-form .ghost>button:hover { background:rgba(255,255,255,.08); }

/* Powered by */
.ff-powered {
  position:fixed; left:14px; bottom:10px;
  display:flex; align-items:center; gap:8px;
  font-size:11.5px; opacity:.9; color:#eaf3ff; text-shadow:0 1px 8px rgba(0,0,0,.5);
}
.ff-powered img { height:16px; width:auto; opacity:.95; }
</style>
""", unsafe_allow_html=True)

# ==== layout 2 colunas ====
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

# ==== validação simples ====
def _ok():
    if not email.strip():
        st.warning("Informe seu e-mail."); return False
    if not pwd:
        st.warning("Informe sua senha."); return False
    if len(pwd) < 6:
        st.warning("A senha deve ter pelo menos 6 caracteres."); return False
    return True

# ==== ações ====
if do_login:
    if _ok():
        try:
            sb.auth.sign_in_with_password({"email": email.strip(), "password": pwd})
            u2 = user()
            if u2:
                bootstrap(u2.id)
                switch_to_entrada()  # entra direto
            else:
                st.error("Não foi possível autenticar. Verifique e-mail e senha.")
        except Exception as e:
            st.error(f"Falha no login: {e}")

if do_signup:
    if _ok():
        try:
            sb.auth.sign_up({"email": email.strip(), "password": pwd})
            st.success("Conta criada. Se a confirmação por e-mail estiver ativada, confirme para poder entrar.")
        except Exception as e:
            st.error(f"Falha ao criar conta: {e}")
