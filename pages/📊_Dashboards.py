# pages/📊_Dashboards.py
from __future__ import annotations
from datetime import date, datetime, timedelta
import streamlit as st
import pandas as pd
from utils import to_brl, _to_date_safe, fetch_tx, fetch_tx_due, fetch_members, fetch_categories

# Acessa o cliente Supabase e IDs do household/membro da sessão
if "sb" not in st.session_state or "HOUSEHOLD_ID" not in st.session_state:
    st.warning("Por favor, faça login na página principal.")
    st.stop()

sb = st.session_state.sb
HOUSEHOLD_ID = st.session_state.HOUSEHOLD_ID

st.title("📊 Dashboards")
tabs = st.tabs(["Relatórios","Fluxo de caixa"])

with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Relatórios")
    ini = st.date_input("Início", value=date.today().replace(day=1))
    fim = st.date_input("Fim", value=date.today())
    tx = fetch_tx(sb, HOUSEHOLD_ID, ini, fim)

    mems = fetch_members(sb, HOUSEHOLD_ID)
    cats = fetch_categories(sb, HOUSEHOLD_ID)

    if not tx:
        st.info("Sem lançamentos.")
    else:
        df = pd.DataFrame(tx)
        mem_map = {m["id"]: m["display_name"] for m in mems}
        cat_map = {c["id"]: c["name"] for c in cats}

        df["valor_eff"] = df.apply(lambda r: (r.get("paid_amount") if r.get("is_paid") else r.get("planned_amount") or r.get("amount") or 0) * (1 if r.get("type")=="income" else -1), axis=1)
        df["Membro"] = df["member_id"].map(mem_map).fillna("—")
        df["Categoria"] = df["category_id"].map(cat_map).fillna("—")

        st.markdown("#### Por membro")
        st.bar_chart(df.groupby("Membro")["valor_eff"].sum().reset_index(), x="Membro", y="valor_eff")

        st.markdown("#### Por categoria")
        st.bar_chart(df.groupby("Categoria")["valor_eff"].sum().reset_index(), x="Categoria", y="valor_eff")
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[1]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Fluxo de caixa (previsto)")
    ini = st.date_input("Início", value=date.today().replace(day=1), key="fx_ini_dash")
    fim = st.date_input("Fim", value=date.today()+timedelta(days=60), key="fx_fim_dash")
    txx = fetch_tx_due(sb, HOUSEHOLD_ID, ini, fim)

    if not txx:
        st.info("Sem previstos.")
    else:
        df = pd.DataFrame(txx)
        def eff(r):
            v = r.get("paid_amount") if r.get("is_paid") else (r.get("planned_amount") or r.get("amount") or 0)
            return v if r.get("type")=="income" else -v
        df["Quando"] = pd.to_datetime(df.get("due_date").fillna(df.get("occurred_at")), errors="coerce").dt.date
        df["Saldo"] = df.apply(eff, axis=1)
        st.line_chart(df.groupby("Quando")["Saldo"].sum().reset_index(), x="Quando", y="Saldo")
    st.markdown('</div>', unsafe_allow_html=True)
