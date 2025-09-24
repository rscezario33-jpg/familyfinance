# pages/1_Entrada.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
from ff_shared import require_session_ids

st.set_page_config(page_title="Family Finance — Entrada", layout="wide", page_icon="🏠")

# Sidebar visível nas páginas internas
st.sidebar.image("assets/logo_family_finance.png", use_column_width=True)
st.sidebar.markdown("### Navegação")
st.sidebar.write("- Entrada")
st.sidebar.write("- Financeiro")
st.sidebar.write("- Administração")
st.sidebar.write("- Dashboards")

household_id, member_id = require_session_ids()

st.title("🏠 Entrada")
st.success("Login OK. Sessão carregada.")
st.write(f"**Household:** {household_id}")
st.write(f"**Member:** {member_id}")

st.markdown("---")
st.subheader("Próximos passos")
st.write(
    "- Criar contas padrão (carteira, conta corrente, cartão) no onboarding.\n"
    "- Lançar primeira entrada/saída.\n"
    "- Ajustar metas mensais por categoria."
)
