# app.py — v5.0
# -*- coding: utf-8 -*-
from __future__ import annotations
import io
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
from supabase_client import get_supabase

# ---------------------------------------------------------
# Config & Estilo
# ---------------------------------------------------------
st.set_page_config(page_title="Finanças Familiares — Matriz & Filiais", layout="wide")

st.markdown("""
<style>
/* container confortável */
.main .block-container { max-width: 1200px; padding-top: .75rem; }

/* cards padrão */
.card {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 6px 20px rgba(0,0,0,.06);
  margin-bottom: 12px;
}

/* inputs arredondados */
.stTextInput input, .stNumberInput input, .stDateInput input { border-radius: 10px !important; }
.stSelectbox div[data-baseweb="select"] > div { border-radius: 10px !important; }

/* botões */
.stButton>button {
  border-radius: 10px; padding: .6rem 1rem; font-weight: 600;
  border: 1px solid #0ea5e9; transition: all .15s ease;
}
.stButton>button:hover { transform: translateY(-1px); }

/* chips/badges */
.badge {
  display: inline-flex; align-items: center; gap: .5rem;
  background: #eef6ff; color: #0369a1; border: 1px solid #bfdbfe;
  padding: .35rem .6rem; border-radius: 999px; font-weight: 600; margin: 4px 6px 0 0;
}
.badge.red  { background:#fff1f2; color:#9f1239; border-color:#fecdd3; }
.badge.green{ background:#ecfdf5; color:#065f46; border-color:#bbf7d0; }

h1,h2,h3 { letter-spacing: .2px; }
</style>
""", unsafe_allow_html=True)

st.title("🏦 Finanças Familiares — Matriz & Filiais")

sb = get_supabase()

# ---------------------------------------------------------
# Auth
# ---------------------------------------------------------
def _signin(email: str, password: str):
    return sb.auth.sign_in_with_password({"email": email, "password": password})

def _signup(email: str, password: str):
    return sb.auth.sign_up({"email": email, "password": password})

def _signout():
    sb.auth.sign_out()

def _user():
    sess = sb.auth.get_session()
    return sess.user if sess and sess.user else None

with st.sidebar:
    st.header("🔐 Acesso")
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if not st.session_state.auth_ok:
        tab_login, tab_signup = st.tabs(["Entrar", "Criar conta"])
        with tab_login:
            le = st.text_input("Email")
            lp = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                try:
                    _signin(le, lp)
                    st.session_state.auth_ok = True
                    st.rerun()
                except Exception as e:
                    msg = str(e)
                    if "email_not_confirmed" in msg or "Email not confirmed" in msg:
                        st.error("Seu e-mail ainda não foi confirmado. Verifique a caixa de entrada.")
                    else:
                        st.error(f"Falha no login: {msg}")
        with tab_signup:
            ne = st.text_input("Email (novo)")
            np = st.text_input("Senha (nova)", type="password")
            if st.button("Criar conta"):
                try:
                    _signup(ne, np)
                    st.success("Conta criada. Depois faça login (ou confirme o e-mail, se exigido).")
                except Exception as e:
                    st.error(f"Falha no cadastro: {e}")
    else:
        u = _user()
        if u:
            st.success(f"Logado: {u.email}")
            if st.button("Sair"):
                _signout()
                st.session_state.auth_ok = False
                st.rerun()
        else:
            st.session_state.auth_ok = False
            st.rerun()

if not st.session_state.auth_ok:
    st.info("Faça login para continuar.")
    st.stop()

user = _user()
assert user, "Sessão inválida"

# ---------------------------------------------------------
# Bootstrap via RPC (Security Definer) — sem fallback
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def ensure_household_and_member(user_id: str) -> dict:
    sb_local = get_supabase()
    res = sb_local.rpc("create_household_and_member", {"display_name": "Você"}).execute().data
    if not res:
        raise RuntimeError("RPC create_household_and_member retornou vazio.")
    return {"household_id": res[0]["household_id"], "member_id": res[0]["member_id"]}

ids = ensure_household_and_member(user.id)
HOUSEHOLD_ID = ids["household_id"]
MY_MEMBER_ID = ids["member_id"]

with st.sidebar:
    if st.button("🔄 Recarregar dados"):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def fetch_members():
    return sb.table("members").select("id,display_name,role") \
             .eq("household_id", HOUSEHOLD_ID).order("display_name").execute().data

def fetch_categories():
    return sb.table("categories").select("id,name,kind") \
             .eq("household_id", HOUSEHOLD_ID).order("name").execute().data

def fetch_accounts():
    return sb.table("accounts").select("id,name,is_active,type") \
             .eq("household_id", HOUSEHOLD_ID).order("name").execute().data

def fetch_active_accounts():
    return sb.table("accounts").select("id,name,is_active,type") \
             .eq("household_id", HOUSEHOLD_ID).eq("is_active", True).order("name").execute().data

def fetch_transactions(start: date, end: date):
    return sb.table("transactions").select(
        "id,occurred_at,type,amount,description,category_id,account_id"
    ).eq("household_id", HOUSEHOLD_ID) \
     .gte("occurred_at", start.isoformat()) \
     .lte("occurred_at", end.isoformat()) \
     .order("occurred_at", desc=False).execute().data

# ---------------------------------------------------------
# Header: métricas rápidas do mês
# ---------------------------------------------------------
first_day = date.today().replace(day=1)
tx_this_month = fetch_transactions(first_day, date.today())
sum_month = sum([t["amount"] if t["type"] == "income" else -t["amount"] for t in tx_this_month]) if tx_this_month else 0.0
n_mems = len(fetch_members())

c1, c2, c3 = st.columns(3)
with c1: st.metric("👪 Membros", n_mems)
with c2: st.metric("📅 Período atual", f"{first_day.strftime('%d/%m')} — {date.today().strftime('%d/%m')}")
with c3: st.metric("💼 Resultado do mês", f"R$ {sum_month:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.markdown("")

# ---------------------------------------------------------
# Abas
# ---------------------------------------------------------
tab_resumo, tab_lancar, tab_movs, tab_membros, tab_contas, tab_categorias, tab_fixas = st.tabs(
    ["📊 Resumo", "➕ Lançar", "📋 Movimentações", "👤 Membros", "🏦 Contas", "🏷️ Categorias", "♻️ Fixas / Cartão"]
)

# ---------------- Resumo ----------------
with tab_resumo:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Visão geral")
    if not tx_this_month:
        st.info("Sem lançamentos neste mês ainda.")
    else:
        dfm = pd.DataFrame(tx_this_month)
        dfm["occurred_at"] = pd.to_datetime(dfm["occurred_at"]).dt.date
        receitas = dfm.loc[dfm["type"]=="income","amount"].sum() if not dfm.empty else 0
        despesas = dfm.loc[dfm["type"]=="expense","amount"].sum() if not dfm.empty else 0
        cA, cB, cC = st.columns(3)
        cA.metric("Receitas", f"R$ {receitas:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
        cB.metric("Despesas", f"R$ {despesas:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
        cC.metric("Resultado", f"R$ {(receitas - despesas):,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Lançar ----------------
with tab_lancar:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Lançamento rápido")
    try:
        cats = fetch_categories()
        accts = fetch_active_accounts()
    except Exception as e:
        cats, accts = [], []
        st.error(f"Falha ao carregar categorias/contas: {e}")

    cat_map = {c["name"]: c for c in cats} or {}
    acc_map = {a["name"]: a for a in accts} or {}

    with st.form("form_tx"):
        tipo = st.selectbox("Tipo", ["income","expense"], index=1,
                            format_func=lambda k: {"income":"Receita","expense":"Despesa"}[k])
        cat = st.selectbox("Categoria", list(cat_map.keys()) or ["Salário","Mercado"])
        acc = st.selectbox("Conta", list(acc_map.keys()) or ["Conta Corrente"])
        val = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
        dt  = st.date_input("Data", value=date.today())
        desc = st.text_input("Descrição")
        ok_tx = st.form_submit_button("Lançar")
        if ok_tx:
            try:
                cat_id = (cat_map.get(cat) or {}).get("id")
                acc_id = (acc_map.get(acc) or {}).get("id")
                sb.table("transactions").insert({
                    "household_id": HOUSEHOLD_ID,
                    "member_id": MY_MEMBER_ID,
                    "account_id": acc_id,
                    "type": tipo,
                    "amount": val,
                    "occurred_at": dt.isoformat(),
                    "description": desc,
                    "category_id": cat_id,
                    "created_by": user.id
                }).execute()
                st.toast("✅ Lançamento registrado!", icon="✅")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Falha ao lançar transação: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Movimentações ----------------
with tab_movs:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Movimentações do período")
    colf1, colf2, colf3 = st.columns([1,1,1])
    with colf1:
        start = st.date_input("Início", value=first_day, key="mov_ini")
    with colf2:
        end = st.date_input("Fim", value=date.today(), key="mov_fim")
    with colf3:
        if st.button("🔍 Buscar", use_container_width=True):
            st.session_state["__trigger_fetch__"] = True

    if st.session_state.get("__trigger_fetch__", True):
        try:
            tx = fetch_transactions(start, end)
        except Exception as e:
            tx = []
            st.error(f"Falha ao carregar movimentações: {e}")
        df = pd.DataFrame(tx)
        if df.empty:
            st.info("Sem lançamentos no período.")
        else:
            df["Data"] = pd.to_datetime(df["occurred_at"]).dt.strftime("%d/%m/%Y")
            df["Tipo"] = df["type"].map({"income":"Receita","expense":"Despesa"})
            df["Valor (R$)"] = df.apply(lambda r: r["amount"] if r["type"]=="income" else -r["amount"], axis=1)
            df["Descrição"] = df["description"].fillna("")
            df_view = df[["Data","Tipo","Valor (R$)","Descrição"]].copy()
            st.dataframe(df_view, use_container_width=True, hide_index=True)

            saldo = df["Valor (R$)"].sum()
            c1, c2 = st.columns(2)
            c1.metric("Lançamentos", len(df))
            c2.metric("Resultado do período", f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

            csv = df_view.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Baixar CSV", data=csv, file_name="movimentacoes.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Membros ----------------
with tab_membros:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Filiais (membros)")

    # === Importante: devido a RLS, só posso alterar MEU próprio member ===
    with st.form("renomear_membro"):
        nm = st.text_input("Seu nome de exibição", value="Você")
        ok_add = st.form_submit_button("Salvar")
        if ok_add and nm.strip():
            try:
                # UPSERT evita o erro 23505 de unique (household_id,user_id)
                sb.table("members").upsert({
                    "household_id": HOUSEHOLD_ID,
                    "user_id": user.id,
                    "display_name": nm.strip(),
                    "role": "owner"
                }, on_conflict="household_id,user_id").execute()
                st.toast("✅ Nome salvo!", icon="✅")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Falha ao salvar seu membro: {e}")

    try:
        mems = fetch_members()
    except Exception as e:
        mems = []
        st.error(f"Falha ao carregar membros: {e}")

    if not mems:
        st.info("Sem membros além de você.")
    else:
        st.markdown("#### Membros da família")
        chips = " ".join([
            f'<span class="badge">👤 {m["display_name"]}{" · owner" if m["role"]=="owner" else ""}</span>'
            for m in mems
        ])
        st.markdown(chips, unsafe_allow_html=True)
        st.caption("Para adicionar outras pessoas, elas precisam criar login e você pode convidá-las depois. (Mantivemos as políticas RLS seguras.)")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Contas ----------------
with tab_contas:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Contas / Carteiras")
    with st.form("nova_conta"):
        col1, col2 = st.columns([2,1])
        with col1:
            an = st.text_input("Nome da conta (ex.: Conta Corrente, Cartão Nubank, Carteira)")
        with col2:
            atype = st.selectbox("Tipo", ["checking","savings","wallet","credit"])
        ob = st.number_input("Saldo inicial", min_value=0.0, step=50.0)
        ok_acc = st.form_submit_button("Salvar conta")
        if ok_acc and an.strip():
            try:
                sb.table("accounts").insert({
                    "household_id": HOUSEHOLD_ID, "name": an.strip(),
                    "type": atype, "opening_balance": ob, "currency": "BRL",
                    "is_active": True
                }).execute()
                st.toast("✅ Conta salva!", icon="✅")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Falha ao salvar conta: {e}")

    try:
        accounts = fetch_accounts()
    except Exception as e:
        accounts = []
        st.error(f"Falha ao carregar contas: {e}")

    if not accounts:
        st.info("Nenhuma conta cadastrada ainda.")
    else:
        st.markdown("#### Suas contas")
        # grid simples
        for acc in accounts:
            colA, colB, colC, colD = st.columns([4,2,2,2])
            with colA: st.write(f"🧾 **{acc['name']}**")
            with colB: st.write(f"Tipo: `{acc.get('type','')}`")
            with colC: st.write("Ativa: ✅" if acc.get("is_active") else "Ativa: ❌")
            with colD:
                if acc.get("is_active"):
                    if st.button("Desativar", key=f"d_{acc['id']}"):
                        sb.table("accounts").update({"is_active": False}).eq("id", acc["id"]).execute()
                        st.cache_data.clear(); st.rerun()
                else:
                    if st.button("Ativar", key=f"a_{acc['id']}"):
                        sb.table("accounts").update({"is_active": True}).eq("id", acc["id"]).execute()
                        st.cache_data.clear(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Categorias ----------------
with tab_categorias:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Categorias (tags visuais)")
    with st.form("nova_cat"):
        cn = st.text_input("Nome da categoria")
        ck = st.selectbox("Tipo", ["income","expense"], format_func=lambda k: {"income":"Receita","expense":"Despesa"}[k])
        ok_cat = st.form_submit_button("Salvar categoria")
        if ok_cat and cn.strip():
            try:
                sb.table("categories").insert({
                    "household_id": HOUSEHOLD_ID, "name": cn.strip(), "kind": ck
                }).execute()
                st.toast("✅ Categoria salva!", icon="✅")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Falha ao salvar categoria: {e}")

    try:
        cats = fetch_categories()
    except Exception as e:
        cats = []
        st.error(f"Falha ao carregar categorias: {e}")

    if not cats:
        st.info("Nenhuma categoria cadastrada.")
    else:
        st.markdown("#### Suas categorias")
        chips_inc = " ".join([f'<span class="badge green">#{c["name"]}</span>' for c in cats if c["kind"]=="income"])
        chips_exp = " ".join([f'<span class="badge red">#{c["name"]}</span>'   for c in cats if c["kind"]=="expense"])
        st.markdown("**Receitas**"); st.markdown(chips_inc or "_(vazio)_", unsafe_allow_html=True)
        st.markdown("**Despesas**"); st.markdown(chips_exp or "_(vazio)_", unsafe_allow_html=True)
        st.caption("As tags são apenas visuais (não criamos coluna extra).")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Fixas / Cartão ----------------
with tab_fixas:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Fixas / Cartão — atalho prático")
    st.write("👉 Marque suas transações fixas com **[FIXA]** na descrição (ex.: `[FIXA] Aluguel`). Use os botões abaixo para facilitar o mês a mês.")

    cfx1, cfx2 = st.columns(2)
    with cfx1:
        # Duplicar FIXAS do mês anterior para o atual
        if st.button("📆 Duplicar [FIXA] do mês anterior"):
            today = date.today()
            first_cur = today.replace(day=1)
            last_prev = first_cur - timedelta(days=1)
            first_prev = last_prev.replace(day=1)

            prev = fetch_transactions(first_prev, last_prev)
            to_copy = [t for t in prev if t.get("description","").upper().find("[FIXA]") >= 0]
            if not to_copy:
                st.warning("Nenhuma [FIXA] encontrada no mês anterior.")
            else:
                for t in to_copy:
                    sb.table("transactions").insert({
                        "household_id": HOUSEHOLD_ID,
                        "member_id": MY_MEMBER_ID,
                        "account_id": t["account_id"],
                        "type": t["type"],
                        "amount": t["amount"],
                        "occurred_at": first_cur.isoformat(),  # dia 1 — ajuste depois se quiser
                        "description": t["description"],
                        "category_id": t["category_id"],
                        "created_by": user.id
                    }).execute()
                st.toast(f"✅ {len(to_copy)} lançamentos [FIXA] criados para este mês.", icon="✅")
                st.cache_data.clear(); st.rerun()

    with cfx2:
        # Atalho: lançar fechamento de cartão (despesa) com [FIXA]
        try:
            accts = [a for a in fetch_active_accounts() if a.get("type") in ("credit","checking","wallet","savings")]
        except Exception:
            accts = []
        acc_map = {a["name"]: a for a in accts}
        with st.form("fechamento_cc"):
            acc = st.selectbox("Conta (Cartão ou onde pagar)", list(acc_map.keys()) or ["Cartão"], key="cc_acc")
            valor = st.number_input("Valor total (R$)", min_value=0.0, step=50.0, key="cc_val")
            dataf = st.date_input("Data", value=date.today(), key="cc_dt")
            ok_cc = st.form_submit_button("Lançar [FIXA] fechamento")
            if ok_cc:
                try:
                    acc_id = (acc_map.get(acc) or {}).get("id")
                    sb.table("transactions").insert({
                        "household_id": HOUSEHOLD_ID,
                        "member_id": MY_MEMBER_ID,
                        "account_id": acc_id,
                        "type": "expense",
                        "amount": valor,
                        "occurred_at": dataf.isoformat(),
                        "description": "[FIXA] Fechamento Cartão",
                        "category_id": None,
                        "created_by": user.id
                    }).execute()
                    st.toast("✅ Fechamento lançado!", icon="✅")
                    st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Falha ao lançar fechamento: {e}")

    st.markdown('</div>', unsafe_allow_html=True)
