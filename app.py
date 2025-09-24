# app.py — Family Finance (Home) • Sidebar reorganizada + correções de categorias e métricas
from __future__ import annotations

from datetime import date, datetime
from collections import defaultdict
from uuid import uuid4

import pandas as pd
import streamlit as st

from supabase_client import get_supabase
from utils import (
    to_brl,
    fetch_members, fetch_categories, fetch_accounts, fetch_cards,
    fetch_tx, fetch_tx_due,
)

# ------------------------------------------------------------
# Config inicial
# ------------------------------------------------------------
st.set_page_config(page_title="Home • Family Finance", layout="wide", initial_sidebar_state="expanded")

# ------------------------------------------------------------
# CSS — visual geral + NOVA sidebar (ordem: logo → navegação → usuário → rodapé)
# ------------------------------------------------------------
st.markdown("""
<style>
/* ========== Sidebar ========== */
section[data-testid="stSidebar"] > div {
  background: #0b2038 !important;
  color: #f0f6ff !important;
  padding-top: 8px; padding-bottom: 8px;
}

/* Container raiz da sidebar vira um flex vertical com espaçamento controlado */
section[data-testid="stSidebar"] > div > div {
  display: flex; flex-direction: column; height: 100%;
}

/* 1) Logo no topo (gruda) */
.ff-sidebar-logo {
  position: sticky; top: 0; z-index: 2;
  padding: 10px 8px 6px 8px; margin-bottom: 6px;
  background: linear-gradient(180deg, rgba(11,32,56,1) 60%, rgba(11,32,56,0) 100%);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

/* 2) Navegação logo abaixo */
.ff-sidebar-nav {
  display: flex; flex-direction: column; gap: 8px;
  padding: 6px 6px 10px 6px; margin-bottom: 8px;
}

/* 3) Bloco do usuário */
.ff-sidebar-user {
  margin-top: 4px;
  padding: 10px 10px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  font-size: 0.9rem;
}

/* Botão sair */
.ff-logout button {
  width: 100%;
  border-radius: 12px;
  background: #e74c3c !important;
  color: #fff !important;
  border: none;
}

/* Separador */
.ff-sep { height: 10px; }

/* 4) Rodapé (Powered by) grudado no fim */
.ff-sidebar-footer {
  margin-top: auto; /* empurra para o fim */
  padding: 8px 8px 6px 8px;
  border-top: 1px solid rgba(255,255,255,0.06);
  text-align: left;
  opacity: .95;
}
.ff-powered { font-size: 11px; color: #b9c9ff; margin: 4px 0 6px 2px; letter-spacing: .3px; }
.ff-brand { display:flex; align-items:center; gap:10px; }
.ff-brand img { max-height: 28px; }

/* Títulos no conteúdo */
h1, h2, h3 { color: #0b2038; }

/* Esconde footer default do Streamlit sem depender de classe frágil */
footer:has(~ div div svg[aria-label="Made with Streamlit"]) { visibility: hidden; height: 0; }

/* Cart vibes */
.ff-card {
  background: #ffffff;
  border: 1px solid rgba(15,23,42,0.06);
  box-shadow: 0 4px 18px rgba(2,6,23,0.06);
  border-radius: 16px; padding: 18px;
}
.ff-kpi { display:flex; flex-direction:column; gap:6px; }
.ff-kpi .label { font-weight: 700; color: #5a6a85; }
.ff-kpi .value { font-size: 28px; font-weight: 900; }
.ff-kpi .hint { font-size: 12px; color: #8aa0c8; }
.red { color: #d63031; } .green { color: #2ecc71; } .blue { color: #1e90ff; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# Helpers de sessão
# ------------------------------------------------------------
sb = get_supabase()

# Você provavelmente já guarda isso ao autenticar; mantenho as chaves abaixo
HOUSEHOLD_ID = st.session_state.get("HOUSEHOLD_ID")
MEMBER_ID    = st.session_state.get("MEMBER_ID")
USER         = st.session_state.get("USER")  # objeto de auth (email, etc.)

# ------------------------------------------------------------
# Sidebar — ordem solicitada
# ------------------------------------------------------------
with st.sidebar:
    # 1) LOGO (no topo)
    st.markdown('<div class="ff-sidebar-logo">', unsafe_allow_html=True)
    st.image("assets/logo_family_finance.png", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 2) NAVEGAÇÃO
    st.markdown('<div class="ff-sidebar-nav">', unsafe_allow_html=True)
    page = st.radio(" ", options=["app", "💼 Financeiro", "📊 Dashboards", "🧰 Administração"],
                    label_visibility="collapsed", index=0)
    st.markdown('</div>', unsafe_allow_html=True)

    # 3) BLOCO DO USUÁRIO
    st.markdown('<div class="ff-sidebar-user">', unsafe_allow_html=True)
    st.write("**Logado:**")
    st.write(USER.email if USER and getattr(USER, "email", None) else "—")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="ff-sep"></div>', unsafe_allow_html=True)

    # Botão sair (sem mexer na sua lógica; apenas visual)
    st.markdown('<div class="ff-logout">', unsafe_allow_html=True)
    if st.button("Sair"):
        # sua lógica de logout fora (limpar sessão) — mantive contratual
        st.session_state.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 4) RODAPÉ (Powered by)
    st.markdown('<div class="ff-sidebar-footer">', unsafe_allow_html=True)
    st.markdown('<div class="ff-powered">Powered by</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns([1,1])
    with col_a:
        st.image("assets/logo_AutomaGO.png", caption=None, use_container_width=False)
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------
# Conteúdo principal
# ------------------------------------------------------------
st.title("✨ Dashboard Financeiro Familiar")

# Toggle “Planejado vs Realizado”
view_kind = st.segmented_control(
    "Métrica",
    options=["Realizado", "Planejado"],
    default="Realizado",
    help="Escolha se os números exibidos devem considerar valores pagos (Realizado) ou valores previstos (Planejado)."
)

# Período do mês atual
today = date.today()
start_month = today.replace(day=1)
end_month = today

# Carregar base mínima
cats = fetch_categories(sb, HOUSEHOLD_ID) if HOUSEHOLD_ID else []
cat_name_by_id = {c["id"]: c.get("name", "Sem Categoria") for c in cats}

txs = fetch_tx(sb, HOUSEHOLD_ID, start_month, end_month) if HOUSEHOLD_ID else []
txs_df = pd.DataFrame(txs) if txs else pd.DataFrame(columns=[
    "id","household_id","member_id","account_id","card_id","category_id","type",
    "amount","planned_amount","paid_amount","occurred_at","due_date",
    "description","payment_method","is_paid"
])

# Função de valor conforme métrica selecionada
def metric_amount(row) -> float:
    if view_kind == "Realizado":
        # realizado só conta o que está pago; se vazio, 0
        return float(row.get("paid_amount") or 0.0) if row.get("is_paid") else 0.0
    # Planejado: se houver planned, usa; senão amount
    return float(row.get("planned_amount") if row.get("planned_amount") is not None else row.get("amount") or 0.0)

# KPIs do mês
def sum_by_type(df: pd.DataFrame, t: str) -> float:
    if df.empty:
        return 0.0
    sub = df[df["type"] == t]
    return float(sub.apply(metric_amount, axis=1).sum())

receitas = sum_by_type(txs_df, "income")
despesas = sum_by_type(txs_df, "expense")
saldo = receitas - despesas

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="ff-card ff-kpi">', unsafe_allow_html=True)
    st.markdown('<div class="label">🍊 Receitas</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="value green">{to_brl(receitas)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">Total de entradas no mês</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="ff-card ff-kpi">', unsafe_allow_html=True)
    st.markdown('<div class="label">🪙 Despesas</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="value blue">{to_brl(despesas)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">Total de saídas no mês</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="ff-card ff-kpi">', unsafe_allow_html=True)
    color = "green" if saldo >= 0 else "red"
    st.markdown('<div class="label">🧮 Saldo</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="value {color}">{to_brl(saldo)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hint">Resultado financeiro até hoje ({view_kind.lower()})</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("—")

# ------------------------------------------------------------
# Despesas por Categoria (Mês Atual) — corrigido p/ usar category_id → nome
# ------------------------------------------------------------
st.subheader("Despesas por Categoria (Mês Atual)")
if txs_df.empty:
    st.info("Nenhuma transação no mês atual.")
else:
    df_exp = txs_df[txs_df["type"] == "expense"].copy()
    if df_exp.empty:
        st.info("Nenhuma despesa registrada no mês atual.")
    else:
        # mapear nomes; manter “Sem Categoria” quando missing
        df_exp["category_name"] = df_exp.get("category_id").map(lambda cid: cat_name_by_id.get(cid, "Sem Categoria"))
        df_exp["valor"] = df_exp.apply(metric_amount, axis=1)
        g = df_exp.groupby("category_name", dropna=False)["valor"].sum().reset_index().sort_values("valor", ascending=False)
        if g["valor"].sum() == 0:
            st.info("Nenhuma despesa válida para a métrica selecionada.")
        else:
            st.bar_chart(g.set_index("category_name"))

# ------------------------------------------------------------
# Evolução Financeira Mensal (últimos 6 meses)
# ------------------------------------------------------------
st.subheader("Evolução Financeira Mensal")
months = pd.date_range(end=end_month, periods=6, freq="MS").date
evo = []
for m in months:
    m_start = m
    m_end = (pd.Timestamp(m) + pd.offsets.MonthEnd(1)).date()
    dfm = pd.DataFrame(fetch_tx(sb, HOUSEHOLD_ID, m_start, m_end)) if HOUSEHOLD_ID else pd.DataFrame()
    if dfm.empty:
        evo.append({"mês": m_start.strftime("%b/%Y"), "Receitas": 0.0, "Despesas": 0.0, "Saldo": 0.0})
    else:
        inc = float(dfm[dfm["type"]=="income"].apply(lambda r: metric_amount(r), axis=1).sum())
        exp = float(dfm[dfm["type"]=="expense"].apply(lambda r: metric_amount(r), axis=1).sum())
        evo.append({"mês": m_start.strftime("%b/%Y"), "Receitas": inc, "Despesas": exp, "Saldo": inc-exp})

evo_df = pd.DataFrame(evo)
st.line_chart(evo_df.set_index("mês"))

# ------------------------------------------------------------
# Navegação (só atalho visual; a troca real é feita pelos arquivos nas pages/)
# ------------------------------------------------------------
if page == "💼 Financeiro":
    st.info("Abra a página **Financeiro** no menu lateral para lançar e gerenciar suas transações.")
elif page == "📊 Dashboards":
    st.info("Abra **Dashboards** para relatórios detalhados.")
elif page == "🧰 Administração":
    st.info("Abra **Administração** para gerenciar membros, contas, categorias e cartões.")
