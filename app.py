# app.py — Family Finance • Redirect para Login
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Family Finance", layout="wide", initial_sidebar_state="collapsed")

LOGIN_PAGE_REL = "pages/0_Login.py"
login_path = Path(__file__).parent / LOGIN_PAGE_REL

def go_login():
    # 1) garante que o arquivo exista
    if not login_path.exists():
        st.error("Página de login não encontrada em **pages/0_Login.py**. Verifique o nome/posição do arquivo.")
        st.stop()

    # 2) tenta switch_page (Streamlit moderno)
    if hasattr(st, "switch_page"):
        try:
            st.switch_page(LOGIN_PAGE_REL)
            return
        except Exception:
            pass

    # 3) fallback: link direto
    st.title("Family Finance")
    st.info("Clique abaixo para ir à tela de login.")
    try:
        st.page_link(LOGIN_PAGE_REL, label="Ir para Login", icon=":material/login:")
    except Exception:
        st.write("Abra a página **Login** no menu à esquerda.")
    st.stop()

go_login()
