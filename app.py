# app.py — Family Finance (Login PRO: background + layout 2 colunas + acesso robusto)
from __future__ import annotations
import streamlit as st
from ff_shared import inject_css, sb, user, bootstrap

st.set_page_config(page_title="Family Finance — Login", layout="wide")

# CSS base (contraste geral)
inject_css()

# ========== CSS do Login (fundo + layout sem rolagem + card/form) ==========
st.markdown("""
<style>
/* Sem rolagem, 100% viewport */
html, body, [data-testid="stAppViewContainer"] { height: 100%; overflow: hidden; }

/* Fundo com imagem (fallback png/jpg/svg) */
[data-testid="stAppViewContainer"] {
  background-image:
    url('assets/Backgroud_FF.png'),
    url('assets/Backgroud_FF.jpg'),
    url('assets/Backgroud_FF.svg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

/* Grid 2 colunas full-height */
.login-shell {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 48px;
  align-items: center;
  min-height: 100vh;
  padding: 48px 5vw;
  box-sizing: border-box;
}

/* Coluna esquerda (marca) */
.brand-col { display:flex; align-items:center; justify-content:flex-start; }
.brand-card {
  display:flex; gap:20px; align-items:center;
  background: rgba(0, 20, 40, .35);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 18px;
  padding: 28px 28px;
  backdrop-filter: blur(6px);
  color: #eaf3ff;
}
.brand-logo { width: 120px; height:auto; }
.brand-title {
  font-size: 44px; line-height: 1.1; font-weight: 900; letter-spacing:.2px;
  margin: 0;
  text-shadow: 0 8px 28px rgba(0,0,0,.45);
}

/* Coluna direita (form) */
.form-col { display:flex; justify-content:flex-start; }
.form-card {
  width: 440px; max-width: 92%;
  background: rgba(0, 18, 35, .60);
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 18px;
  box-shadow: 0 24px 60px rgba(0,0,0,.45);
  backdrop-filter: blur(8px);
  padding: 22px 22px 18px;
  color: #eaf3ff;
}

/* Inputs “neumórficos” escuros */
.form-card .stTextInput>div>div,
.form-card .stPassword>div>div {
  background: rgba(255,255,255,.06) !important;
  border: 1px solid rgba(255,255,255,.14) !important;
  border-radius: 12px !important;
}
.form-card input { color:#eaf3ff !important; }

/* Botões principais */
.form-card .stButton>button {
  width: 100%;
  border-radius: 12px;
  padding: .85rem;
  font-weight: 800;
  border: 1px solid rgba(255,255,255,.25);
}
.form-card .primary>button {
  background:#0ea5e9; color:#fff; border-color:#0ea5e9;
}
.form-card .primary>button:hover { transform: translateY(-1px); background:#0284c7; border-color:#0284c7; }
.form-card .ghost>button {
  background: transparent; color:#eaf3ff;
}
.form-card .ghost>button:hover { background: rgba(255,255,255,.06); }

/* Ações secundárias (esqueci/criar conta) */
.actions {
  display:flex; justify-content:space-between; align-items:center; gap:16px;
  font-size: 13.5px; opacity:.95; margin-top: 6px;
}
.actions .link { color:#84ff6a; font-weight:700; text-decoration:none; }

/* Powered by fixo, canto inferior esquerdo */
.powered {
  position: fixed; left: 16px; bottom: 10px;
  display:flex; align-items:center; gap:8px;
  font-size: 11.5px; opacity:.85; color:#e8f2ff;
  text-shadow: 0 1px 8px rgba(0,0,0,.5);
}
.powered img { height: 16px; width:auto; opacity:.9; }
</style>
""", unsafe_allow_html=True)

# ========== Cabeça de sessão (se houver sessão pendurada) ==========
u = user()
session_bar = st.container()
with session_bar:
    if u:
        email_logado = getattr(u, "email", "") or "(usuário autenticado)"
        cA, cB, cC = st.columns([3,1,1])
        with cA:
            st.success(f"Você já está logado como **{email_logado}**.")
        with cB:
            if st.button("Entrar no sistema"):
                try:
                    bootstrap(u.id)
                    st.switch_page("pages/1_Entrada.py")
                except Exception:
                    st.info("Login ok. Abra o menu (☰) e entre em ‘Entrada’.")
        with cC:
            if st.button("Sair"):
                sb.auth.sign_out()
                st.session_state.clear()
                st.rerun()

# ========== Corpo (2 colunas) ==========
st.markdown('<div class="login-shell">', unsafe_allow_html=True)

# Coluna esquerda — Marca
left = st.container()
with left:
    st.markdown('<div class="brand-col">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="brand-card">
          <img class="brand-logo" src="assets/logo_family_finance.png" />
          <div>
            <h1 class="brand-title">Family<br/>Finance</h1>
            <div style="opacity:.85;margin-top:6px;font-size:14px">Gestão financeira familiar, com precisão e elegância.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

# Coluna direita — Formulário
right = st.container()
with right:
    st.markdown('<div class="form-col"><div class="form-card">', unsafe_allow_html=True)

    st.markdown("#### Acessar sua conta")
    email = st.text_input("E-mail", key="login_email", placeholder="voce@email.com")
    pwd   = st.text_input("Senha", key="login_pwd", type="password", placeholder="••••••••")

    c1, c2 = st.columns(2)
    with c1:
        # Entrar
        enter = st.button("Entrar", key="btn_login", use_container_width=True, type="primary")
    with c2:
        # Criar conta
        signup = st.button("Criar conta", key="btn_signup", use_container_width=True)

    # Esqueci a senha / lembrar
    cc1, cc2 = st.columns([1,1])
    with cc1:
        forgot = st.button("Esqueci minha senha", key="btn_forgot", use_container_width=True)
    with cc2:
        # entrar como já logado (se sessão válida)
        if u:
            go = st.button("Entrar no sistema", key="btn_go", use_container_width=True)
            if go:
                try:
                    bootstrap(u.id)
                    st.switch_page("pages/1_Entrada.py")
                except Exception:
                    st.info("Login ok. Abra o menu (☰) e entre em ‘Entrada’.")
        else:
            st.write("")

    st.markdown('</div></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # fecha .login-shell

# Powered by
st.markdown(
    """
    <div class="powered">
      <span>powered by</span>
      <img src="assets/logo_automaGO.png" />
    </div>
    """,
    unsafe_allow_html=True
)

# ========== Lógica de autenticação (robusta) ==========
def _go_home(uid: str):
    try:
        bootstrap(uid)
        st.switch_page("pages/1_Entrada.py")
    except Exception:
        # fallback sem page_link (evita KeyError em certos ambientes)
        st.success("Login ok! Abra o menu (☰) e vá para ‘Entrada’.")
        st.rerun()

def _validate_fields() -> bool:
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

# Entrar
if enter:
    if _validate_fields():
        with st.spinner("Validando suas credenciais..."):
            try:
                sb.auth.sign_in_with_password({"email": email.strip(), "password": pwd})
                u2 = user()
                if u2:
                    # opcional: validar confirmação de e-mail, quando a política exigir
                    # if getattr(u2, "email_confirmed_at", None) is None: ...
                    _go_home(u2.id)
                else:
                    st.error("Não foi possível autenticar. Verifique e-mail e senha.")
            except Exception as e:
                st.error(f"Falha no login: {e}")

# Criar conta
if signup:
    if _validate_fields():
        with st.spinner("Criando sua conta..."):
            try:
                sb.auth.sign_up({"email": email.strip(), "password": pwd})
                st.info("Conta criada. Confirme o e-mail (se exigido nas configurações) e depois faça login.")
            except Exception as e:
                st.error(f"Falha ao criar conta: {e}")

# Esqueci a senha
if forgot:
    if not email.strip():
        st.warning("Informe seu e-mail no campo acima para enviar o link de redefinição.")
    else:
        with st.spinner("Enviando link de redefinição..."):
            try:
                redirect = (st.secrets.get("app", {}).get("url") + "/") if hasattr(st, "secrets") else None
                opts = {"email_redirect_to": redirect} if redirect else None
                if opts: sb.auth.reset_password_email(email.strip(), options=opts)
                else:    sb.auth.reset_password_email(email.strip())
                st.success("Se o e-mail existir, você receberá um link para redefinir a senha.")
            except Exception as e:
                st.error(f"Erro ao solicitar redefinição: {e}")
