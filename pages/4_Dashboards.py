# pages/4_Dashboards.py — Family Finance (Página: Dashboards)
from __future__ import annotations
from datetime import date, timedelta
import pandas as pd
import streamlit as st

from ff_shared import (
    inject_css, sidebar_shell, user, bootstrap,
    fetch_tx, fetch_tx_due, fetch_members, fetch_categories, to_brl
)

st.set_page_config(page_title="Family Finance — Dashboards", layout="wide")
inject_css()

# ====== Auth / contexto do lar ======
u = user()
if not u:
    st.error("Faça login para acessar os Dashboards.")
    st.stop()

ids = bootstrap(u.id)
HOUSEHOLD_ID = ids["household_id"]

# ====== Sidebar padrão ======
with st.sidebar:
    sidebar_shell(show_logout=True)

# ====== UI ======
st.title("Dashboards")
tabs = st.tabs(["Relatórios", "Fluxo de caixa"])

# -------------------------------------------------------------------
# 1) Relatórios (por membro e por categoria)
# -------------------------------------------------------------------
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Relatórios")

    c1, c2 = st.columns(2)
    with c1:
        ini = st.date_input("Início", value=date.today().replace(day=1), key="r_ini")
    with c2:
        fim = st.date_input("Fim", value=date.today(), key="r_fim")

    tx = fetch_tx(HOUSEHOLD_ID, ini, fim)
    mems = fetch_members(HOUSEHOLD_ID)
    cats = fetch_categories(HOUSEHOLD_ID)

    if not tx:
        st.info("Sem lançamentos no período.")
    else:
        df = pd.DataFrame(tx)
        mem_map = {m["id"]: m["display_name"] for m in mems}
        cat_map = {c["id"]: c["name"] for c in cats}

        def valor_eff(r):
            v = r.get("paid_amount") if r.get("is_paid") else (r.get("planned_amount") or r.get("amount") or 0)
            return v if r.get("type") == "income" else -v

        df["Valor"] = df.apply(valor_eff, axis=1)
        df["Membro"] = df["member_id"].map(mem_map).fillna("—")
        df["Categoria"] = df["category_id"].map(cat_map).fillna("—")

        # ---- Por membro
        st.markdown("#### Por membro")
        by_mem = df.groupby("Membro", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
        st.bar_chart(by_mem, x="Membro", y="Valor")

        # ---- Por categoria
        st.markdown("#### Por categoria")
        by_cat = df.groupby("Categoria", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
        st.bar_chart(by_cat, x="Categoria", y="Valor")

        # ---- Tabela detalhada + export
        st.markdown("#### Detalhes")
        show_cols = ["description", "type", "occurred_at", "due_date", "Membro", "Categoria", "Valor"]
        st.dataframe(df[show_cols].rename(columns={
            "description": "Descrição", "type": "Tipo",
            "occurred_at": "Data", "due_date": "Vencimento"
        }), use_container_width=True, hide_index=True)

        csv = df[show_cols].to_csv(index=False).encode("utf-8")
        st.download_button("Baixar CSV do período", data=csv, file_name="relatorio_periodo.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------------------------
# 2) Fluxo de caixa (previsto)
# -------------------------------------------------------------------
with tabs[1]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📈 Fluxo de caixa (previsto)")

    f1, f2 = st.columns(2)
    with f1:
        ini = st.date_input("Início", value=date.today().replace(day=1), key="fxd_ini")
    with f2:
        fim = st.date_input("Fim", value=date.today() + timedelta(days=60), key="fxd_fim")

    txx = fetch_tx_due(HOUSEHOLD_ID, ini, fim)
    if not txx:
        st.info("Sem previstos para o período.")
    else:
        df = pd.DataFrame(txx)

        def eff(r):
            v = r.get("paid_amount") if r.get("is_paid") else (r.get("planned_amount") or r.get("amount") or 0)
            return v if r.get("type") == "income" else -v

        df["Quando"] = pd.to_datetime(df.get("due_date").fillna(df.get("occurred_at")), errors="coerce").dt.date
        df["Saldo"] = df.apply(eff, axis=1)

        diario = df.groupby("Quando", as_index=False)["Saldo"].sum().sort_values("Quando")
        diario["Acumulado"] = diario["Saldo"].cumsum()

        st.line_chart(diario[["Quando", "Saldo"]], x="Quando", y="Saldo")
        st.markdown("**Acumulado do período:** " + to_brl(diario["Saldo"].sum()))

        st.markdown("#### Tabela do fluxo")
        st.dataframe(diario, use_container_width=True, hide_index=True)

        csv = diario.to_csv(index=False).encode("utf-8")
        st.download_button("Baixar CSV do fluxo", data=csv, file_name="fluxo_previsto.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)

