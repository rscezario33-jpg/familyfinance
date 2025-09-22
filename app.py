# app.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import streamlit as st
from datetime import date
from supabase_client import get_supabase

st.set_page_config(page_title="Finanças Familiares — Matriz & Filiais", layout="wide")
st.title("🏦 Finanças Familiares — Matriz & Filiais")

sb = get_supabase()

# ================= Auth =================
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
        tab1, tab2 = st.tabs(["Entrar", "Criar conta"])
        with tab1:
            le = st.text_input("Email")
            lp = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                try:
                    _signin(le, lp)
                    st.session_state.auth_ok = True
                    st.rerun()
                except Exception as e:
                    msg = str(e)
                    if "Email not confirmed" in msg or "email_not_confirmed" in msg:
                        st.error("Seu e-mail ainda não foi confirmado. Verifique sua caixa de entrada ou reenvie a confirmação.")
                    else:
                        st.error(f"Falha no login: {msg}")
        with tab2:
            ne = st.text_input("Email (novo)")
            np = st.text_input("Senha (nova)", type="password")
            if st.button("Criar conta"):
                try:
                    _signup(ne, np)
                    st.success("Conta criada. Depois faça login (ou confirme o e-mail, se estiver habilitado).")
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

# ============ Bootstrap família/membro ============
# IMPORTANTE: não passe objetos não-hashable (ex.: Client) como parâmetro de função cacheada
@st.cache_data(show_spinner=False)
def ensure_household_and_member(user_id: str) -> dict:
    sb_local = get_supabase()  # pega o client por dentro (não vira parâmetro do cache)

    # já é membro de alguma família?
    m = sb_local.table("members").select("*").eq("user_id", user_id).execute().data
    if m:
        return {"household_id": m[0]["household_id"], "member_id": m[0]["id"]}

    # cria família padrão
    hh = sb_local.table("households").insert({
        "name": "Minha Família",
        "currency": "BRL",
        "created_by": user_id
    }).execute().data[0]

    # cria membro dono
    mem = sb_local.table("members").insert({
        "household_id": hh["id"],
        "user_id": user_id,
        "display_name": "Você",
        "role": "owner"
    }).execute().data[0]

    # categorias básicas
    base_cats = [
        ("Salário","income"), ("Extras","income"),
        ("Mercado","expense"), ("Moradia","expense"),
        ("Transporte","expense"), ("Saúde","expense"),
        ("Lazer","expense"), ("Educação","expense")
    ]
    for n,k in base_cats:
        sb_local.table("categories").insert({
            "household_id": hh["id"], "name": n, "kind": k
        }).execute()

    # conta padrão
    sb_local.table("accounts").insert({
        "household_id": hh["id"],
        "name": "Conta Corrente",
        "type": "checking",
        "opening_balance": 0,
        "currency": "BRL"
    }).execute()

    return {"household_id": hh["id"], "member_id": mem["id"]}

ids = ensure_household_and_member(user.id)
HOUSEHOLD_ID = ids["household_id"]
MY_MEMBER_ID = ids["member_id"]

with st.sidebar:
    if st.button("🔄 Recarregar dados"):
        st.cache_data.clear()
        st.rerun()

# ============ Filiais (membros) ============
st.subheader("👪 Filiais (membros)")
with st.form("novo_membro"):
    nm = st.text_input("Nome do membro (filial)")
    ok = st.form_submit_button("Adicionar")
    if ok and nm.strip():
        sb.table("members").insert({
            "household_id": HOUSEHOLD_ID,
            "user_id": user.id,
            "display_name": nm.strip(),
            "role": "member"
        }).execute()
        st.success("Membro adicionado.")
        st.cache_data.clear()
        st.rerun()

mems = sb.table("members").select("id,display_name,role") \
        .eq("household_id", HOUSEHOLD_ID).execute().data
st.dataframe(pd.DataFrame(mems), use_container_width=True)

st.markdown("---")

# ============ Lançamento rápido ============
st.subheader("💸 Lançamento rápido (teste de persistência)")
cats = sb.table("categories").select("id,name,kind").eq("household_id", HOUSEHOLD_ID).execute().data
accts = sb.table("accounts").select("id,name").eq("household_id", HOUSEHOLD_ID).eq("is_active", True).execute().data
cat_map = {c["name"]: c for c in cats} or {}
acc_map = {a["name"]: a for a in accts} or {}

with st.form("form_tx"):
    tipo = st.selectbox("Tipo", ["income","expense"], format_func=lambda k: {"income":"Receita","expense":"Despesa"}[k])
    cat = st.selectbox("Categoria", list(cat_map.keys()) or ["Salário","Mercado"])
    acc = st.selectbox("Conta", list(acc_map.keys()) or ["Conta Corrente"])
    val = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
    dt = st.date_input("Data", value=date.today())
    desc = st.text_input("Descrição")
    ok2 = st.form_submit_button("Lançar")
    if ok2:
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
        st.success("Lançamento registrado.")
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# ============ Listagem por período ============
st.subheader("📋 Movimentações do mês")
first_day = date.today().replace(day=1)
start = st.date_input("Início", value=first_day, key="dt_ini")
end = st.date_input("Fim", value=date.today(), key="dt_fim")

tx = sb.table("transactions").select(
        "id,occurred_at,type,amount,description"
    ).eq("household_id", HOUSEHOLD_ID) \
     .gte("occurred_at", start.isoformat()) \
     .lte("occurred_at", end.isoformat()) \
     .order("occurred_at", desc=False).execute().data

df = pd.DataFrame(tx)
if df.empty:
    st.info("Sem lançamentos no período.")
else:
    df["occurred_at"] = pd.to_datetime(df["occurred_at"]).dt.date
    st.dataframe(df, use_container_width=True)
    saldo = df.apply(lambda r: r["amount"] if r["type"]=="income" else -r["amount"], axis=1).sum()
    c1, c2 = st.columns(2)
    c1.metric("Lançamentos", len(df))
    c2.metric("Resultado do período", f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
