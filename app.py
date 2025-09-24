# app.py — Family Finance v8.1.0 # (sidebar contraste + logos 50% + fixas com valor pago + anexos + lembretes por e-mail)
from __future__ import annotations
from datetime import date, datetime, timedelta
import uuid
import io
import os
from typing import List, Optional
import pandas as pd
import streamlit as st
from supabase_client import get_supabase
from utils import to_brl, _to_date_safe, fetch_tx, fetch_members, notify_due_bills

st.set_page_config(page_title="Family Finance", layout="wide")

# ========================= # CSS (visual + contraste sidebar) # =========================
st.markdown("""
<style>
/* Sidebar fundo azul escuro */
section[data-testid="stSidebar"] > div {
    background: #0b2038 !important;
    color: #f0f6ff !important;
    padding-top: 14px;
}
/* Contraste nos textos da sidebar */
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > div, section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span {
    color:#f0f6ff !important;
}
/* Imagens e títulos */
section[data-testid="stSidebar"] img {
    display:block;
    margin: 6px auto 14px auto;
}
.sidebar-title {
    color:#e6f0ff;
    font-weight:700;
    letter-spacing:.6px;
    text-transform:uppercase;
    font-size:.80rem;
    margin: 6px 0 6px 6px;
}
.sidebar-group {
    border-top:1px solid rgba(255,255,255,.08);
    margin:10px 0 8px 0;
    padding-top:8px;
}
/* Botões/inputs */
.stButton>button, .stDownloadButton>button {
    border-radius:10px;
    padding:.55rem .9rem;
    font-weight:600;
    border:1px solid #0ea5e9;
    background:#0ea5e9;
    color:white;
}
.stButton>button:hover {
    transform: translateY(-1px);
    background:#0284c7;
    border-color:#0284c7;
}
.stSelectbox div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input, .stDateInput input {
    border-radius:10px !important;
}
/* Cards e badges */
.card {
    background: linear-gradient(180deg,#fff 0%,#f8fafc 100%);
    border:1px solid #e2e8f0;
    border-radius:16px;
    padding:16px 18px;
    box-shadow:0 6px 20px rgba(0,0,0,.06);
    margin-bottom:12px;
}
.badge {
    display:inline-flex;
    align-items:center;
    gap:.5rem;
    background:#eef6ff;
    color:#0369a1;
    border:1px solid #bfdbfe;
    padding:.35rem .6rem;
    border-radius:999px;
    font-weight:600;
    margin:4px 6px 0 0;
}
.badge.red{background:#fff1f2;color:#9f1239;border-color:#fecdd3;}
.badge.green{background:#ecfdf5;color:#065f46;border-color:#bbf7d0;}
.small {
    font-size:.85rem;
    opacity:.75;
}
</style>
""", unsafe_allow_html=True)

# ========================= # Conexão Supabase # =========================
# O cliente Supabase é inicializado uma vez e armazenado na sessão
if "sb" not in st.session_state:
    st.session_state.sb = get_supabase()
sb = st.session_state.sb

# ========================= # Auth wrappers # =========================
def _signin(email, password):
    sb.auth.sign_in_with_password({"email": email, "password": password})

def _signup(email, password):
    try:
        sb.auth.sign_up({"email": email, "password": password})
    except OSError as e:
        if getattr(e, "errno", None) == -2:
            raise RuntimeError("Falha de rede/DNS ao contatar o Supabase.")
        raise

def _signout():
    sb.auth.sign_out()
    # Limpa a sessão para garantir que o usuário precise fazer login novamente
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.auth_ok = False # Força a re-autenticação

def _user():
    sess = sb.auth.get_session()
    return sess.user if sess and sess.user else None

# ========================= # Sidebar (logos 50% + Powered by) # =========================
with st.sidebar:
    st.image("assets/logo_family_finance.png", width=110)
    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if not st.session_state.auth_ok:
        st.markdown('<div class="sidebar-title">Acesso</div>', unsafe_allow_html=True)
        email = st.text_input("Email").strip()
        pwd = st.text_input("Senha", type="password")

        def _validate_inputs() -> bool:
            if not email:
                st.warning("Informe um e-mail.")
                return False
            if not pwd:
                st.warning("Informe uma senha.")
                return False
            if len(pwd) < 6:
                st.warning("A senha deve ter pelo menos 6 caracteres.")
                return False
            return True

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Entrar"):
                if _validate_inputs():
                    try:
                        _signin(email, pwd)
                        st.session_state.auth_ok = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Falha no login: {e}")
        with c2:
            if st.button("Criar conta"):
                if _validate_inputs():
                    try:
                        _signup(email, pwd)
                        st.success("Conta criada. Confirme o e-mail (se exigido nas configurações) e faça login.")
                    except Exception as e:
                        st.error(f"Falha ao criar conta: {e}")
        st.stop() # Interrompe a execução se não estiver autenticado

    # Se autenticado, exibe informações do usuário e menu de logout
    user = _user()
    st.session_state.user = user # Armazena o objeto user na sessão
    st.caption(f"Logado: {user.email if user else ''}")
    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-title">Navegação</div>', unsafe_allow_html=True)
    # As páginas serão automaticamente listadas aqui pelo Streamlit devido à estrutura de pastas

    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)
    if st.button("Sair"):
        _signout()
        st.rerun()
    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)
    st.markdown('<div class="small" style="text-align:center;opacity:.9;">Powered by</div>', unsafe_allow_html=True)
    st.image("assets/logo_automaGO.png", width=80)


# ========================= # Bootstrap household/member # =========================
# Esta parte só roda se o usuário estiver autenticado
if st.session_state.auth_ok and "HOUSEHOLD_ID" not in st.session_state:
    @st.cache_data(show_spinner=False)
    def bootstrap(user_id: str, supabase_client):
        try:
            supabase_client.rpc("accept_pending_invite").execute()
        except Exception:
            pass # Ignora se não houver convites pendentes ou função não existir

        res = supabase_client.rpc("create_household_and_member", {"display_name": "Você"}).execute().data
        return {"household_id": res[0]["household_id"], "member_id": res[0]["member_id"]}

    ids = bootstrap(st.session_state.user.id, sb)
    st.session_state.HOUSEHOLD_ID = ids["household_id"]
    st.session_state.MY_MEMBER_ID = ids["member_id"]

# Verificação final antes de prosseguir para o conteúdo da página
if not (st.session_state.auth_ok and "HOUSEHOLD_ID" in st.session_state):
    st.warning("Por favor, faça login ou crie uma conta para continuar.")
    st.stop()

# Dispara lembretes (não bloqueia fluxo) - Acesso aos dados da sessão
notify_due_bills(sb, st.session_state.HOUSEHOLD_ID, st.session_state.user)


# ========================= # Conteúdo da Página Principal (Entrada) # =========================
# Este bloco se torna o conteúdo padrão da página principal do app
st.title("Family Finance")
st.header("🏠 Visão Geral")

first_day = date.today().replace(day=1)
txm = fetch_tx(sb, st.session_state.HOUSEHOLD_ID, first_day, date.today())
res = sum([(t.get("paid_amount") if t.get("is_paid") else t.get("planned_amount") or t.get("amount") or 0) * (1 if t.get("type")=="income" else -1) for t in txm]) if txm else 0

c1,c2,c3 = st.columns(3)
with c1:
    st.metric("Período", f"{first_day.strftime('%d/%m')}—{date.today().strftime('%d/%m')}")
with c2:
    st.metric("Lançamentos", len(txm))
with c3:
    st.metric("Resultado (previsto)", to_brl(res))

st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("Visão por membro (mês)")
mems = fetch_members(sb, st.session_state.HOUSEHOLD_ID)
mem_map = {m["id"]: m["display_name"] for m in mems}

if txm:
    df = pd.DataFrame(txm)
    df["valor_eff"] = df.apply(lambda r: (r.get("paid_amount") if r.get("is_paid") else r.get("planned_amount") or r.get("amount") or 0) * (1 if r.get("type")=="income" else -1), axis=1)
    df["Membro"] = df["member_id"].map(mem_map).fillna("—")
    st.bar_chart(df.groupby("Membro")["valor_eff"].sum().reset_index(), x="Membro", y="valor_eff")
else:
    st.info("Sem lançamentos no mês.")
st.markdown('</div>', unsafe_allow_html=True)
