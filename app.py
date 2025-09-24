# app.py — Family Finance v8.6.0 # (Sidebar com navegação nativa totalmente estilizada e com CSS Vars)
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

# Importações de módulos locais
from supabase_client import get_supabase
from utils import to_brl, _to_date_safe, fetch_tx, fetch_members, notify_due_bills

# Configurações da página principal (Dashboard)
st.set_page_config(page_title="🏠 Home", layout="wide")

# =========================
# CSS (visual + contraste sidebar + dashboard)
# =========================
st.markdown("""
<style>
/* =========================
   Vars (ajuste rápido de tema)
========================= */
:root{
  --sb-bg: #0b2038;        /* Sidebar Fundo */
  --sb-fg: #eaf2ff;        /* Sidebar Texto */
  --line: rgba(255,255,255,.12); /* Divisor da Sidebar */
  --card: rgba(255,255,255,.06); /* Fundo dos Cards de navegação */
  --card-hov: rgba(255,255,255,.10); /* Fundo dos Cards de navegação (hover) */
  --brand: #0ea5e9;       /* Cor primária (azul) */
  --brand-700:#0284c7;    /* Cor primária (azul escuro) */
  --danger:#ef4444;       /* Cor de perigo (vermelho) */
  --danger-700:#dc2626;   /* Cor de perigo (vermelho escuro) */
  --radius: 14px;         /* Raio da borda */

  /* Cores para o Dashboard */
  --dash-bg-card: linear-gradient(145deg, #ffffff, #f0f2f5);
  --dash-border-card: #e0e0e0;
  --dash-shadow-card: 0 4px 15px rgba(0,0,0,0.08);
  --dash-text-dark: #0b2038;
  --dash-text-medium: #334155;
  --dash-text-light: #64748b;
  --dash-success: #22c55e;
  --dash-error: #ef4444;
}

/* Streamlit padrão */
.st-emotion-cache-zt5igj { visibility: hidden; }  /* "Made with Streamlit" */
div.stSpinner > div { text-align: center; color: var(--sb-fg); }
div.stSpinner > div > span { color: var(--sb-fg); }

/* =====================
   Sidebar Base Styling
   ===================== */
section[data-testid="stSidebar"] > div {
  background: var(--sb-bg) !important;
  color: var(--sb-fg) !important;
  box-shadow: 2px 0 5px rgba(0,0,0,0.1);
  position: relative; /* permite a logo absoluta */
  padding-top: 0; /* Remove padding top para a logo ser absoluta */
}

/* Layout coluna full-height e reordenação com flexbox */
section[data-testid="stSidebar"] > div > div.stVerticalBlock:first-of-type {
  display:flex; flex-direction:column; min-height:100vh;
}

/* Logo Family Finance (topo, fixa e centralizada) */
section[data-testid="stSidebar"] img[src*="logo_family_finance"] {
  position:absolute;
  top:14px; left:50%; transform:translateX(-50%);
  max-width:78%; /* Ajusta o tamanho da logo */
  margin:0;
  display:block;
  filter: drop-shadow(0 2px 6px rgba(0,0,0,.25));
  z-index:5; /* Garante que fique acima de outros elementos */
  order: 1; /* Força a ordem visual */
}

/* Divisores na sidebar */
.sidebar-group {
  border-top:1px solid var(--line);
  margin:12px 12px 6px 12px;
  padding-top:8px;
}
/* Reordenação dos divisores */
section[data-testid="stSidebar"] .sidebar-group:nth-of-type(1) { order: 2; margin-top: 100px; } /* Ajusta para começar após a logo */
section[data-testid="stSidebar"] .sidebar-group:nth-of-type(2) { order: 4; }
section[data-testid="stSidebar"] .sidebar-group:nth-of-type(3) { order: 6; }
section[data-testid="stSidebar"] .sidebar-group:nth-of-type(4) { order: 8; }


/* Bloco "Logado:" (email do usuário) */
.user-email-display {
  order: 3; /* Após o primeiro divisor */
  margin:8px 16px 10px 16px;
  padding:8px 4px 0 4px;
  font-size:.92rem; opacity:.95;
  color: var(--sb-fg);
  text-align: center;
}

/* ==============================
   Navegação Nativa Centralizada
   ============================== */
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {
  order: 5; /* Após o email do usuário e seu divisor */
  flex:1 1 auto; /* Ocupa o espaço restante verticalmente */
  display:flex; flex-direction:column; justify-content:center; /* Centraliza verticalmente o menu */
  padding:6px 10px;
}
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul{ list-style:none; margin:0; padding:0; }
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li{ margin:6px 0; } /* Margem entre os itens do menu */

section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li a{
  display:flex; align-items:center; gap:10px;
  padding:14px 16px; margin:0 2px;
  color:var(--sb-fg) !important; text-decoration:none;
  background:var(--card);
  border:1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.04), 0 1px 4px rgba(0,0,0,.15);
  transition: all .18s ease-in-out;
  font-weight:600;
}
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li a:hover{
  background:var(--card-hov);
  border-color: rgba(255,255,255,.18);
  transform: translateY(-1px);
}
/* Link ativo robusto (aria-current="page") */
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li a[aria-current="page"]{
  background:linear-gradient(180deg, var(--brand) 0%, #11b7ff 100%);
  color:#001523 !important; /* Cor de texto para links ativos, forte contraste */
  border-color: transparent;
  box-shadow: 0 6px 14px rgba(0,165,233,.35);
}

/* Esconde o cabeçalho do expander se as páginas estiverem agrupadas (opcional) */
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] .stExpander > div > div:first-child { display: none; }
/* Remove padding extra de expander */
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] .stExpander div[data-testid="stVerticalBlock"] { padding: 0; }

/* =====================
   Botão SAIR (footer)
   ===================== */
section[data-testid="stSidebar"] .stButton:last-of-type button{
  order: 7; /* Força a ordem visual */
  display:block !important;
  width: calc(100% - 32px) !important;
  margin: 8px 16px 2px 16px !important;
  border-radius:var(--radius) !important;
  background:var(--danger) !important;
  border:1px solid var(--danger) !important;
  color:#fff !important;
  font-weight:700 !important;
  padding:10px 0 !important;
  box-shadow: 0 4px 10px rgba(0,0,0,.2) !important;
}
section[data-testid="stSidebar"] .stButton:last-of-type button:hover{
  background:var(--danger-700) !important; border-color:var(--danger-700) !important; transform:translateY(-1px);
}

/* =====================
   Rodapé "Powered by"
   ===================== */
section[data-testid="stSidebar"] .small{ 
  order: 9; /* Força a ordem visual */
  text-align:center; opacity:.9; margin: 6px 0 2px 0;
  color: var(--sb-fg);
}
section[data-testid="stSidebar"] img[src*="logo_automaGO"]{
  order: 10; /* Força a ordem visual */
  display:block; margin:6px auto 14px auto;
  max-width:46%; /* Tamanho menor para a logo de rodapé */
  filter: drop-shadow(0 1px 3px rgba(0,0,0,.25));
}

/* Esconde nav se não autenticado */
body:not(:has(.user-email-display)) div[data-testid="stSidebarNav"]{ display:none !important; }

/* =====================
   Inputs/botões gerais (fora da sidebar)
   ===================== */
.stButton>button, .stDownloadButton>button{
  border-radius:10px; padding:.55rem .9rem; font-weight:600;
  border:1px solid var(--brand); background:var(--brand); color:white;
  transition:all .2s ease-in-out;
}
.stButton>button:hover, .stDownloadButton>button:hover{
  transform: translateY(-1px);
  background:var(--brand-700); border-color:var(--brand-700);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}
.stSelectbox div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input, .stDateInput input{
  border-radius:10px !important; border:1px solid #e2e8f0;
}

/* =====================
   Cards, Welcome e Dashboard (atualizado com CSS Vars)
   ===================== */
.card{
  background:var(--dash-bg-card); border:1px solid var(--dash-border-card);
  border-radius:var(--radius); padding:16px 18px;
  box-shadow:0 6px 20px rgba(0,0,0,.06); margin-bottom:12px;
}
.badge{
  display:inline-flex; align-items:center; gap:.5rem;
  background:#eef6ff; color:#0369a1; border:1px solid #bfdbfe;
  padding:.35rem .6rem; border-radius:999px; font-weight:600; margin:4px 6px 0 0;
}
.badge.red{background:#fff1f2;color:#9f1239;border-color:#fecdd3;}
.badge.green{background:#ecfdf5;color:#065f46;border-color:#bbf7d0;}
.small { font-size:.85rem; opacity:.75; }

.welcome-container{
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  min-height:100vh; text-align:center; padding:20px;
  background:url("https://images.unsplash.com/photo-1543286386-77942a635930?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1974&q=80") no-repeat center center fixed;
  background-size:cover; color:white; text-shadow:1px 1px 3px rgba(0,0,0,0.5);
}
.welcome-overlay{ background:rgba(0,0,0,0.5); padding:40px; border-radius:15px; max-width:800px; }
.welcome-container h1{ font-size:3.5rem; color:white; margin-bottom:20px; font-weight:700; }
.welcome-container p{ font-size:1.5rem; color:#f0f6ff; margin-bottom:30px; line-height:1.6; }
.welcome-container img{ max-width:300px; height:auto; margin-top:20px; filter:drop-shadow(0 0 5px rgba(0,0,0,0.5)); }
.welcome-container .stButton > button{ background:var(--brand); border:none; color:white; padding:10px 25px; font-size:1.2rem; border-radius:8px; transition:all .3s ease; }
.welcome-container .stButton > button:hover{ background:var(--brand-700); transform:translateY(-2px); }

.dashboard-title{ font-size:2.2rem; font-weight:700; color:var(--dash-text-dark); margin-bottom:25px; }
.metric-box{
  background:var(--dash-bg-card); border:1px solid var(--dash-border-card);
  border-radius:var(--radius); padding:20px;
  box-shadow:var(--dash-shadow-card); display:flex; flex-direction:column;
  justify-content:space-between; min-height:120px; margin-bottom:15px;
  transition:all .2s ease-in-out;
}
.metric-box:hover{ transform:translateY(-3px); box-shadow:0 6px 20px rgba(0,0,0,0.12); }
.metric-box h3{ font-size:1.1rem; color:var(--dash-text-medium); margin-bottom:10px; display:flex; align-items:center; gap:8px; }
.metric-box .value{ font-size:2.2rem; font-weight:700; color:var(--dash-text-dark); }
.metric-box .delta{ font-size:.9rem; color:var(--dash-text-light); }
.chart-container{
  background:var(--dash-bg-card); border:1px solid var(--dash-border-card);
  border-radius:var(--radius); padding:20px;
  box-shadow:var(--dash-shadow-card); margin-bottom:25px;
}
.chart-container h2{ font-size:1.5rem; color:var(--dash-text-dark); margin-bottom:15px; }

</style>
""", unsafe_allow_html=True)

# ========================= # Conexão Supabase # =========================
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
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.auth_ok = False
    st.rerun()

def _user():
    sess = sb.auth.get_session()
    return sess.user if sess and sess.user else None

# ========================= # Sidebar # =========================
with st.sidebar:
    # A logo Family Finance já está sendo posicionada de forma absoluta via CSS
    st.image("assets/logo_family_finance.png", width=110, use_column_width=False, output_format="PNG") # Necessário para o seletor CSS `img[src*="logo_family_finance"]`
    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True) # Divisor 1

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if not st.session_state.auth_ok:
        st.markdown('<div class="sidebar-title">Acesso à Plataforma</div>', unsafe_allow_html=True)
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

    # Se autenticado:
    user = _user()
    st.session_state.user = user
    st.markdown(f'<div class="user-email-display">Logado: {user.email if user else ""}</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True) # Divisor 2

    # A navegação de páginas nativa do Streamlit (st.PageLink) será renderizada aqui
    # pelo próprio Streamlit, e o CSS irá reposicioná-la e estilizá-la.
    # Não há necessidade de adicionar elementos Streamlit aqui para a navegação.
    
    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True) # Divisor 3

    if st.button("Sair", key="sidebar_logout_button"):
        _signout()

    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True) # Divisor 4

    st.markdown('<div class="small">Powered by</div>', unsafe_allow_html=True)
    st.image("assets/logo_automaGO.png", width=80, use_column_width=False, output_format="PNG")


# ========================= # Bootstrap household/member # =========================
if st.session_state.auth_ok and "HOUSEHOLD_ID" not in st.session_state:
    def bootstrap(user_id: str, supabase_client):
        try:
            supabase_client.rpc("accept_pending_invite").execute()
        except Exception:
            pass

        try:
            res = supabase_client.rpc("create_household_and_member", {"display_name": "Você"}).execute().data
        except Exception as e:
            st.error(f"Falha ao inicializar o household: {e}. Por favor, tente novamente ou contate o suporte.")
            st.stop()

        if not res or not res[0].get("household_id") or not res[0].get("member_id"):
            st.error("Resposta inválida do servidor ao inicializar o household. Por favor, tente novamente ou contate o suporte.")
            st.stop()

        return {"household_id": res[0]["household_id"], "member_id": res[0]["member_id"]}

    ids = bootstrap(st.session_state.user.id, sb)
    st.session_state.HOUSEHOLD_ID = ids["household_id"]
    st.session_state.MY_MEMBER_ID = ids["member_id"]

# Verificação final antes de prosseguir para o conteúdo da página (pré-login)
if not (st.session_state.auth_ok and "HOUSEHOLD_ID" in st.session_state):
    st.markdown('<div class="welcome-container">', unsafe_allow_html=True)
    st.markdown('<div class="welcome-overlay">', unsafe_allow_html=True)
    st.markdown('<h1>Bem-vindo ao Family Finance!</h1>', unsafe_allow_html=True)
    st.markdown('<p>Sua plataforma inteligente para gerenciar as finanças familiares de forma colaborativa, transparente e eficiente. Juntos, construa o futuro financeiro que você sempre sonhou.</p>', unsafe_allow_html=True)
    st.image("assets/logo_family_finance.png", width=250)
    st.markdown('<p>Acesse sua conta ou crie uma nova na barra lateral para começar a transformar suas finanças!</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

notify_due_bills(sb, st.session_state.HOUSEHOLD_ID, st.session_state.user)


# ========================= # Funções para Buscar Dados do Dashboard # =========================
def get_dashboard_data(supabase_client, household_id):
    today = date.today()
    
    first_day_current_month = today.replace(day=1)
    current_month_tx = fetch_tx(supabase_client, household_id, first_day_current_month, today)
    
    total_income_current_month = sum(t.get("planned_amount", 0) for t in current_month_tx if t.get("type") == "income")
    total_expense_current_month = sum(t.get("planned_amount", 0) for t in current_month_tx if t.get("type") == "expense")
    current_balance = total_income_current_month - total_expense_current_month

    expense_transactions_with_category = [
        t for t in current_month_tx if t.get("type") == "expense" and t.get("category") is not None
    ]
    if expense_transactions_with_category:
        expense_categories_df = pd.DataFrame(expense_transactions_with_category)
        expense_categories_df['planned_amount'] = pd.to_numeric(expense_categories_df['planned_amount'], errors='coerce').fillna(0)
        expense_categories = expense_categories_df.groupby("category")["planned_amount"].sum().reset_index()
        expense_categories.columns = ["Categoria", "Valor"]
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

# ========================= # Função para renderizar o Dashboard (Home) # =========================
def show_home_dashboard():
    st.markdown('<h1 class="dashboard-title">✨ Dashboard Financeiro Familiar</h1>', unsafe_allow_html=True)

    with st.spinner("Carregando dados do dashboard..."):
        dashboard_data = get_dashboard_data(sb, st.session_state.HOUSEHOLD_ID)

    st.markdown("<h2>Visão Geral do Mês Atual</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <h3>💰 Receitas <span style="color:var(--dash-success);">▲</span></h3>
            <div class="value">{to_brl(dashboard_data["current_month_income"])}</div>
            <div class="delta">Total de entradas no mês</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-box">
            <h3>💸 Despesas <span style="color:var(--dash-error);">▼</span></h3>
            <div class="value">{to_brl(dashboard_data["current_month_expense"])}</div>
            <div class="delta">Total de saídas no mês</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        saldo_color = "var(--dash-success)" if dashboard_data["current_month_balance"] >= 0 else "var(--dash-error)"
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
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h2>Despesas por Categoria (Mês Atual)</h2>', unsafe_allow_html=True)
        if not dashboard_data["expense_categories_df"].empty:
            fig_pie = px.pie(
                dashboard_data["expense_categories_df"],
                values="Valor",
                names="Categoria",
                title="Distribuição das Despesas",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color=var(--dash-text-dark), width=1)))
            fig_pie.update_layout(showlegend=True, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Nenhuma despesa registrada para o mês atual com categoria.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_chart2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h2>Evolução Financeira Mensal</h2>', unsafe_allow_html=True)
        if not dashboard_data["monthly_evolution_df"].empty:
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=dashboard_data["monthly_evolution_df"]["Mês"], y=dashboard_data["monthly_evolution_df"]["Receitas"], mode='lines+markers', name='Receitas', line=dict(color=var(--dash-success), width=3)))
            fig_line.add_trace(go.Scatter(x=dashboard_data["monthly_evolution_df"]["Mês"], y=dashboard_data["monthly_evolution_df"]["Despesas"], mode='lines+markers', name='Despesas', line=dict(color=var(--dash-error), width=3)))
            fig_line.add_trace(go.Scatter(x=dashboard_data["monthly_evolution_df"]["Mês"], y=dashboard_data["monthly_evolution_df"]["Saldo"], mode='lines+markers', name='Saldo', line=dict(color=var(--brand), width=4, dash='dot')))

            fig_line.update_layout(
                title='Receitas, Despesas e Saldo ao longo do Tempo',
                xaxis_title='Mês',
                yaxis_title='Valor',
                hovermode='x unified',
                legend_title_text='Legenda',
                height=400
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Dados insuficientes para evolução mensal. Registre mais transações.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<h2>Resultado por Membro (Mês Atual)</h2>', unsafe_allow_html=True)

    mems = fetch_members(sb, st.session_state.HOUSEHOLD_ID)
    mem_map = {m["id"]: m["display_name"] for m in mems}

    if dashboard_data["all_transactions_current_month"]:
        df = pd.DataFrame(dashboard_data["all_transactions_current_month"])
        df["valor_eff"] = df.apply(lambda r: (r.get("paid_amount") if r.get("is_paid") else r.get("planned_amount", 0)) * (1 if r.get("type")=="income" else -1), axis=1)
        df["Membro"] = df["member_id"].map(mem_map).fillna("Não Atribuído")

        member_summary = df.groupby("Membro")["valor_eff"].sum().reset_index()
        
        fig_bar = px.bar(
            member_summary,
            x="Membro",
            y="valor_eff",
            title="Resultado Líquido por Membro",
            color="valor_eff",
            color_continuous_scale=px.colors.sequential.RdBu,
            labels={"valor_eff": "Resultado (R\$)"}
        )
        fig_bar.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.info("Sem lançamentos no mês para análise por membro.")
    st.markdown('</div>', unsafe_allow_html=True)


# ========================= # Roteamento de Páginas (Após Login) # =========================
if st.session_state.auth_ok and "HOUSEHOLD_ID" in st.session_state:
    # O Streamlit renderiza a página atual automaticamente.
    # Como app.py é a "Home", ele sempre exibirá show_home_dashboard() se não houver pages/
    # Se houver pages/, o Streamlit alterna para elas.
    # Então, este bloco apenas garante que o dashboard seja mostrado na página principal.
    show_home_dashboard() 
