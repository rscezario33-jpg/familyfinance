# app.py — Page: Login
import streamlit as st
from ff_shared import inject_css, sb, user, bootstrap

st.set_page_config(page_title="Family Finance — Login", layout="wide")
inject_css()

st.markdown(
    """
    <div style="display:flex;min-height:100vh;align-items:center;justify-content:center;background:linear-gradient(180deg,#0b2038 0%,#122d4f 100%);">
      <div style="background:#ffffff;max-width:520px;width:92%;border-radius:18px;padding:28px 28px 22px;border:1px solid #e2e8f0;box-shadow:0 16px 40px rgba(0,0,0,.25);">
        <div style="text-align:center;margin-bottom:10px;">
          <img src="app/static/logo" style="display:none" />
        </div>
        <h2 style="margin:0 0 8px 0;">Family Finance</h2>
        <p style="margin:0 0 16px 0;opacity:.7">Acesse sua conta</p>
    """,
    unsafe_allow_html=True
)

email = st.text_input("Email", key="login_email")
pwd = st.text_input("Senha", type="password", key="login_pwd")
col1, col2 = st.columns(2)
with col1:
    if st.button("Entrar", use_container_width=True):
        try:
            sb.auth.sign_in_with_password({"email": email.strip(), "password": pwd})
            u = user()
            if u:
                bootstrap(u.id)  # garante household
                st.success("Bem-vindo!")
                st.switch_page("pages/1_Entrada.py")
        except Exception as e:
            st.error(f"Falha no login: {e}")
with col2:
    if st.button("Criar conta", use_container_width=True):
        try:
            sb.auth.sign_up({"email": email.strip(), "password": pwd})
            st.info("Conta criada. Confirme o e-mail (se exigido) e entre.")
        except Exception as e:
            st.error(f"Falha ao criar conta: {e}")

st.markdown(
    """
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# redireciona se já logado
if user():
    try: st.switch_page("pages/1_Entrada.py")
    except Exception: pass
