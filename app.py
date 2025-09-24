# app.py — Family Finance v8.5.1 (fix bootstrap convite por link)
from __future__ import annotations
from datetime import date, datetime, timedelta
import uuid
import io
import os
from typing import List, Optional
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from dateutil.relativedelta import relativedelta

from supabase_client import get_supabase
from utils import to_brl, _to_date_safe, fetch_tx, fetch_members, notify_due_bills, fetch_categories

st.set_page_config(page_title="🏠 Home", layout="wide")

# =========================
# CSS (mantido)
# =========================
st.markdown("""<style>/* ... todo o CSS exatamente como você já tinha ... */</style>""", unsafe_allow_html=True)

# ========================= # Conexão Supabase # =========================
if "sb" not in st.session_state:
    st.session_state.sb = get_supabase()
sb = st.session_state.sb

# =========================
# 0) Capturar token de convite (?join=XXXX) ANTES de login
# =========================
try:
    qp = st.query_params  # Streamlit 1.32+
    join_token = qp.get("join")
except Exception:
    # compatibilidade com versões anteriores
    join_token = None
    try:
        join_token = st.experimental_get_query_params().get("join", [None])[0]
    except Exception:
        pass

if join_token:
    # guarda na sessão para sobreviver ao fluxo de signup/login
    st.session_state["pending_join_token"] = join_token

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
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.auth_ok = False
    st.rerun()

def _user():
    sess = sb.auth.get_session()
    return sess.user if sess and sess.user else None

# ========================= # Sidebar # =========================
with st.sidebar:
    st.markdown('<div class="ff-brand"><div class="ff-card">', unsafe_allow_html=True)
    st.image("assets/logo_family_finance.png", width=116)
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if not st.session_state.auth_ok:
        # dica visual se veio com convite
        if st.session_state.get("pending_join_token"):
            st.info("Convite detectado. Faça login/crie conta para entrar na família do convite.")

        st.markdown('<div class="sidebar-title">Acesso à Plataforma</div>', unsafe_allow_html=True)
        email = st.text_input("Email").strip()
        pwd = st.text_input("Senha", type="password")

        def _validate_inputs() -> bool:
            if not email:
                st.warning("Informe um e-mail."); return False
            if not pwd:
                st.warning("Informe uma senha."); return False
            if len(pwd) < 6:
                st.warning("A senha deve ter pelo menos 6 caracteres."); return False
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
                        st.success("Conta criada. Confirme o e-mail (se exigido) e depois faça login.")
                    except Exception as e:
                        st.error(f"Falha ao criar conta: {e}")
        st.stop()

    # autenticado
    user = _user()
    st.session_state.user = user
    st.markdown(f'<div class="user-email-display">Logado: {user.email if user else ""}</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)

    # Navegação nativa (estilizada via CSS)

    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)
    if st.button("Sair", key="sidebar_logout_button"):
        _signout()
    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)

    st.markdown('<div class="ff-powered"><div class="small">Powered by</div>', unsafe_allow_html=True)
    st.image("assets/logo_automaGO.png", width=96)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 1) Bootstrap household/member — corrige fluxo do convite
# =========================
if st.session_state.auth_ok and "HOUSEHOLD_ID" not in st.session_state:

    def _accept_by_token_if_any(client):
        token = st.session_state.pop("pending_join_token", None)
        if not token:
            return
        try:
            # RPC SECURITY DEFINER, criada no seu banco:
            client.rpc("accept_invite_by_token", {"p_token": token}).execute()
        except Exception:
            # silencioso: se token inválido/expirado segue o fluxo normal
            pass

    def _find_membership(client, user_id: str):
        try:
            data = client.table("members").select("id, household_id").eq("user_id", user_id).limit(1).execute().data
            if data:
                return {"household_id": data[0]["household_id"], "member_id": data[0]["id"]}
        except Exception:
            pass
        return None

    def bootstrap(user_id: str, client):
        # 1) Se veio por link, tenta aceitar pelo token
        _accept_by_token_if_any(client)

        # 2) Se já tem membership (token aceito ou já era membro), usa
        m = _find_membership(client, user_id)
        if m:
            return m

        # 3) Fallback: aceita convites pendentes por e-mail (fluxo antigo, se mantido)
        try:
            client.rpc("accept_pending_invite").execute()
        except Exception:
            pass
        m = _find_membership(client, user_id)
        if m:
            return m

        # 4) Último recurso: cria nova família
        try:
            res = client.rpc("create_household_and_member", {"display_name": "Você"}).execute().data
        except Exception as e:
            st.error(f"Falha ao inicializar o household: {e}.")
            st.stop()
        if not res or not res[0].get("household_id") or not res[0].get("member_id"):
            st.error("Resposta inválida do servidor ao inicializar o household.")
            st.stop()
        return {"household_id": res[0]["household_id"], "member_id": res[0]["member_id"]}

    ids = bootstrap(st.session_state.user.id, sb)
    st.session_state.HOUSEHOLD_ID = ids["household_id"]
    st.session_state.MY_MEMBER_ID = ids["member_id"]

# Pré-login (mantido)
if not (st.session_state.auth_ok and "HOUSEHOLD_ID" in st.session_state):
    st.markdown('<div class="welcome-container"><div class="welcome-overlay">', unsafe_allow_html=True)
    st.markdown('<h1>Bem-vindo ao Family Finance!</h1>', unsafe_allow_html=True)
    st.markdown('<p>Sua plataforma inteligente para gerenciar as finanças familiares de forma colaborativa.</p>', unsafe_allow_html=True)
    st.image("assets/logo_family_finance.png", width=250)
    if st.session_state.get("pending_join_token"):
        st.info("Convite detectado. Crie sua conta ou faça login na barra lateral para entrar na família.")
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop()

notify_due_bills(sb, st.session_state.HOUSEHOLD_ID, st.session_state.user)

# ========================= # Dados do Dashboard # =========================
def get_dashboard_data(supabase_client, household_id):
    today = date.today()
    first_day_current_month = today.replace(day=1)
    current_month_tx = fetch_tx(supabase_client, household_id, first_day_current_month, today)

    cats = fetch_categories(supabase_client, household_id)
    cat_name_by_id = {c["id"]: c.get("name", "Sem Categoria") for c in cats}

    total_income_current_month = sum(t.get("planned_amount", 0) for t in current_month_tx if t.get("type") == "income")
    total_expense_current_month = sum(t.get("planned_amount", 0) for t in current_month_tx if t.get("type") == "expense")
    current_balance = total_income_current_month - total_expense_current_month

    expense_txs = [t for t in current_month_tx if t.get("type") == "expense"]
    if expense_txs:
        df_exp = pd.DataFrame(expense_txs)
        df_exp["Categoria"] = df_exp.get("category_id").map(lambda cid: cat_name_by_id.get(cid, "Sem Categoria"))
        df_exp["Valor"] = pd.to_numeric(df_exp.get("planned_amount", 0), errors="coerce").fillna(0)
        expense_categories = df_exp.groupby("Categoria", dropna=False)["Valor"].sum().reset_index()
    else:
        expense_categories = pd.DataFrame(columns=["Categoria", "Valor"])

    monthly_data = []
    for i in range(6):
        month_date = today - relativedelta(months=i)
        month_start_calc = month_date.replace(day=1)
        if month_date.month == 12:
            month_end_calc = date(month_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end_calc = date(month_date.year, month_date.month + 1, 1) - timedelta(days=1)
        if month_end_calc > today:
            month_end_calc = today
        txs = fetch_tx(supabase_client, household_id, month_start_calc, month_end_calc)
        income = sum(t.get("planned_amount", 0) for t in txs if t.get("type") == "income")
        expense = sum(t.get("planned_amount", 0) for t in txs if t.get("type") == "expense")
        monthly_data.append({
            "Mês": month_start_calc.strftime("%Y-%m"),
            "Receitas": income,
            "Despesas": expense,
            "Saldo": income - expense
        })
    monthly_df = pd.DataFrame(monthly_data).sort_values("Mês", ascending=True)

    return {
        "current_month_income": total_income_current_month,
        "current_month_expense": total_expense_current_month,
        "current_month_balance": current_balance,
        "expense_categories_df": expense_categories,
        "monthly_evolution_df": monthly_df,
        "all_transactions_current_month": current_month_tx
    }

# ========================= # Renderização do Dashboard (Home) # =========================
def show_home_dashboard():
    st.markdown('<h1 class="dashboard-title">✨ Dashboard Financeiro Familiar</h1>', unsafe_allow_html=True)
    with st.spinner("Carregando dados do dashboard..."):
        dashboard_data = get_dashboard_data(sb, st.session_state.HOUSEHOLD_ID)

    st.markdown("<h2>Visão Geral do Mês Atual</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <h3>💰 Receitas <span style="color:#22c55e;">▲</span></h3>
            <div class="value">{to_brl(dashboard_data["current_month_income"])}</div>
            <div class="delta">Total de entradas no mês</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-box">
            <h3>💸 Despesas <span style="color:#ef4444;">▼</span></h3>
            <div class="value">{to_brl(dashboard_data["current_month_expense"])}</div>
            <div class="delta">Total de saídas no mês</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        saldo_color = "#22c55e" if dashboard_data["current_month_balance"] >= 0 else "#ef4444"
        st.markdown(f"""
        <div class="metric-box">
            <h3>📊 Saldo <span style="color:{saldo_color};"></span></h3>
            <div class="value" style="color:{saldo_color};">{to_brl(dashboard_data["current_month_balance"])}</div>
            <div class="delta">Resultado financeiro até hoje</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown('<div class="chart-container"><h2>Despesas por Categoria (Mês Atual)</h2>', unsafe_allow_html=True)
        if not dashboard_data["expense_categories_df"].empty:
            fig_pie = px.pie(
                dashboard_data["expense_categories_df"],
                values="Valor",
                names="Categoria",
                title="Distribuição das Despesas",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#0b2038', width=1)))
            fig_pie.update_layout(showlegend=True, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Nenhuma despesa registrada para o mês atual com categoria.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_chart2:
        st.markdown('<div class="chart-container"><h2>Evolução Financeira Mensal</h2>', unsafe_allow_html=True)
        if not dashboard_data["monthly_evolution_df"].empty:
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=dashboard_data["monthly_eolution_df"]["Mês"], y=dashboard_data["monthly_eolution_df"]["Receitas"], mode='lines+markers', name='Receitas', line=dict(color='#22c55e', width=3)))
            fig_line.add_trace(go.Scatter(x=dashboard_data["monthly_eolution_df"]["Mês"], y=dashboard_data["monthly_eolution_df"]["Despesas"], mode='lines+markers', name='Despesas', line=dict(color='#ef4444', width=3)))
            fig_line.add_trace(go.Scatter(x=dashboard_data["monthly_eolution_df"]["Mês"], y=dashboard_data["monthly_eolution_df"]["Saldo"], mode='lines+markers', name='Saldo', line=dict(color='#0ea5e9', width=4, dash='dot')))
            fig_line.update_layout(title='Receitas, Despesas e Saldo ao longo do Tempo', xaxis_title='Mês', yaxis_title='Valor', hovermode='x unified', legend_title_text='Legenda', height=400)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Dados insuficientes para evolução mensal. Registre mais transações.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    st.markdown('<div class="chart-container"><h2>Resultado por Membro (Mês Atual)</h2>', unsafe_allow_html=True)
    mems = fetch_members(sb, st.session_state.HOUSEHOLD_ID)
    mem_map = {m["id"]: m["display_name"] for m in mems}

    if dashboard_data["all_transactions_current_month"]:
        df = pd.DataFrame(dashboard_data["all_transactions_current_month"])
        df["valor_eff"] = df.apply(lambda r: (r.get("paid_amount") if r.get("is_paid") else r.get("planned_amount", 0)) * (1 if r.get("type")=="income" else -1), axis=1)
        df["Membro"] = df["member_id"].map(mem_map).fillna("Não Atribuído")
        member_summary = df.groupby("Membro")["valor_eff"].sum().reset_index()
        fig_bar = px.bar(member_summary, x="Membro", y="valor_eff", title="Resultado Líquido por Membro",
                         color="valor_eff", color_continuous_scale=px.colors.sequential.RdBu,
                         labels={"valor_eff": "Resultado (R$)"})
        fig_bar.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sem lançamentos no mês para análise por membro.")
    st.markdown('</div>', unsafe_allow_html=True)

# ========================= # Roteamento (Home) # =========================
if st.session_state.auth_ok and "HOUSEHOLD_ID" in st.session_state:
    show_home_dashboard()
