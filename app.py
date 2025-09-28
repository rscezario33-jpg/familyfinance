# app.py — Family Finance v8.6.0
# Login full-screen (sem sidebar) + Home pós-login com menu superior de navegação

from __future__ import annotations
from datetime import date, timedelta
import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from dateutil.relativedelta import relativedelta

from supabase_client import get_supabase
from utils import to_brl, fetch_tx, fetch_members, notify_due_bills, fetch_categories

# ============== Config da página ==============
st.set_page_config(page_title="🏠 Home", layout="wide")

# ============== CSS global (seu visual atual preservado) ==============
st.markdown("""
<style>
:root{
  --sb-bg:#0b2038; --sb-fg:#eaf2ff; --line:rgba(255,255,255,.12);
  --glass:rgba(255,255,255,.06); --glass-hov:rgba(255,255,255,.10);
  --brand:#0ea5e9; --brand-700:#0284c7; --danger:#ef4444; --danger-700:#dc2626;
  --radius:14px;
}
.st-emotion-cache-zt5igj{ visibility:hidden; }

/* ===== Sidebar (pós-login) ===== */
section[data-testid="stSidebar"]>div{
  background:var(--sb-bg)!important; color:var(--sb-fg)!important;
  position:relative;
  background-image:
    linear-gradient(180deg, rgba(6,18,32,.85) 0%, rgba(14,33,56,.85) 40%, rgba(14,33,56,.92) 100%),
    url("assets/Backgroud_FF.png");
  background-size:cover; background-position:center; box-shadow:2px 0 5px rgba(0,0,0,.12);
}
section[data-testid="stSidebar"] > div > div.stVerticalBlock:first-of-type{
  display:flex; flex-direction:column; min-height:100vh;
}
.ff-brand{ order:1; position:sticky; top:12px; z-index:5; padding:12px 10px 0; }
.ff-brand .ff-card{
  background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.18);
  border-radius:16px; padding:12px 10px; backdrop-filter:blur(6px);
  box-shadow:0 6px 18px rgba(0,0,0,.15), inset 0 1px 0 rgba(255,255,255,.12);
  display:flex; align-items:center; justify-content:center;
}
.ff-brand img{ display:block; max-width:78%; height:auto; filter:drop-shadow(0 2px 6px rgba(0,0,0,.25)); }
.sidebar-group{ border-top:1px solid var(--line); margin:12px 12px 6px; padding-top:8px; order:2; }
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"]{
  order:3; flex:1 1 auto; display:flex; flex-direction:column; justify-content:center;
  padding:6px 10px; margin-top:8px;
}
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul{ list-style:none; margin:0; padding:0; }
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li{ margin:10px 0; }
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li a{
  display:flex; align-items:center; gap:10px; padding:14px 16px; margin:0 2px;
  color:var(--sb-fg)!important; text-decoration:none; background:var(--glass);
  border:1px solid var(--line); border-radius:var(--radius);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.08), 0 6px 14px rgba(0,0,0,.18);
  transition:transform .16s ease, background .16s ease, border-color .16s ease; font-weight:600;
}
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li a:hover{
  background:var(--glass-hov); border-color:rgba(255,255,255,.22); transform:translateY(-1px);
}
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li a[aria-current="page"]{
  background:linear-gradient(180deg,#16b3ff 0%, var(--brand) 100%);
  color:#041421!important; border-color:transparent; box-shadow:0 10px 22px rgba(0,165,233,.35);
}
.user-email-display{ order:4; margin:8px 16px 10px; padding:8px 4px 0; font-size:.93rem; opacity:.96; border-top:1px solid var(--line); }
.ff-powered{ order:90; margin-top:auto; text-align:center; padding:8px 0 12px; }
.ff-powered .small{ opacity:.9; margin:6px 0 4px; }
.ff-powered img{ display:block; margin:6px auto 14px; max-width:56%; filter:drop-shadow(0 1px 3px rgba(0,0,0,.25)); }
.ff-logout button{
  display:block!important; width:calc(100% - 32px)!important; margin:10px 16px 4px!important;
  border-radius:14px!important; background:var(--danger)!important; border:1px solid var(--danger)!important;
  color:#fff!important; font-weight:700!important; padding:10px 0!important; box-shadow:0 8px 18px rgba(0,0,0,.22)!important;
}
.ff-logout button:hover{ background:var(--danger-700)!important; border-color:var(--danger-700)!important; transform:translateY(-1px); }

/* ===== Cards & gráficos (pós-login) ===== */
.card{ background:linear-gradient(180deg,#fff 0%,#f8fafc 100%); border:1px solid #e2e8f0; border-radius:16px; padding:16px 18px; box-shadow:0 6px 20px rgba(0,0,0,.06); margin-bottom:12px; }
.badge{ display:inline-flex; align-items:center; gap:.5rem; background:#eef6ff; color:#0369a1; border:1px solid #bfdbfe; padding:.35rem .6rem; border-radius:999px; font-weight:600; margin:4px 6px 0 0; }
.badge.red{background:#fff1f2;color:#9f1239;border-color:#fecdd3;} .badge.green{background:#ecfdf5;color:#065f46;border-color:#bbf7d0;}
.small{ font-size:.85rem; opacity:.75; }
.dashboard-title{ font-size:2.2rem; font-weight:700; color:#0b2038; margin-bottom:14px; }
.metric-box{ background:linear-gradient(145deg,#ffffff,#f0f2f5); border-radius:12px; padding:20px; box-shadow:0 4px 15px rgba(0,0,0,0.08); min-height:120px; margin-bottom:15px; border:1px solid #e0e0e0; }
.metric-box h3{ font-size:1.1rem; color:#334155; margin-bottom:10px; display:flex; align-items:center; gap:8px; }
.metric-box .value{ font-size:2.2rem; font-weight:700; color:#0b2038; }
.chart-container{ background:linear-gradient(145deg,#ffffff,#f0f2f5); border-radius:12px; padding:20px; box-shadow:0 4px 15px rgba(0,0,0,0.08); margin-bottom:25px; border:1px solid #e0e0e0; }
.chart-container h2{ font-size:1.5rem; color:#0b2038; margin-bottom:15px; }

/* ===== Barra de menu superior (pós-login) ===== */
.top-menu{
  display:flex; gap:10px; align-items:center; margin: 4px 0 16px 0;
}
.top-menu .pill > button{
  border-radius:999px !important; padding:.6rem 1.0rem !important; font-weight:700 !important;
  background:#0ea5e9 !important; border:1px solid #0ea5e9 !important; color:#fff !important;
}
.top-menu .pill > button:hover{ background:#0284c7 !important; border-color:#0284c7 !important; transform:translateY(-1px); }

/* ===== Login full-screen (sem sidebar) ===== */
.ff-login-hide header[data-testid="stHeader"]{ display:none; }
.ff-login-hide section[data-testid="stSidebar"]{ display:none; }
.ff-login-hide footer{ visibility:hidden; }
.ff-login-hide [data-testid="stAppViewContainer"] > .main{ padding:0 !important; }
.ff-login-hide .main .block-container{ padding-top:0 !important; padding-bottom:0 !important; }

.ff-login-bg [data-testid="stAppViewContainer"]{
  background-image:url('assets/Backgroud_FF.png'); background-size:cover; background-position:center; background-repeat:no-repeat;
}
.ff-login-shell{
  min-height:100vh; display:grid; grid-template-columns:1.25fr 1fr; align-items:center; gap:56px; padding:48px 6vw; box-sizing:border-box;
}
.ff-brand-login{
  display:flex; align-items:center; gap:24px; background:rgba(0,18,35,.38); border:1px solid rgba(255,255,255,.18);
  border-radius:18px; padding:28px 30px; color:#eaf3ff; backdrop-filter:blur(6px); box-shadow:0 24px 60px rgba(0,0,0,.45);
}
.ff-brand-login img{ width:140px; height:auto; }
.ff-title{ font-size:48px; font-weight:900; line-height:1.05; margin:0; }
.ff-sub{ opacity:.9; margin-top:8px; font-size:14px; }
.ff-form{
  width:460px; max-width:92%; background:rgba(0,18,35,.62); border:1px solid rgba(255,255,255,.12);
  border-radius:18px; padding:24px 22px 18px; color:#eaf3ff; backdrop-filter:blur(8px);
  box-shadow:0 24px 60px rgba(0,0,0,.45);
}
.ff-form .stTextInput>div>div, .ff-form .stPassword>div>div{
  background:rgba(255,255,255,.06)!important; border:1px solid rgba(255,255,255,.16)!important; border-radius:12px!important;
}
.ff-form input{ color:#eaf3ff!important; }
.ff-form .stButton>button{
  width:100%; border-radius:12px; padding:.85rem; font-weight:800; border:1px solid rgba(255,255,255,.25);
}
.ff-form .primary>button{ background:#0ea5e9; color:#fff; border-color:#0ea5e9; }
.ff-form .primary>button:hover{ transform:translateY(-1px); background:#0284c7; border-color:#0284c7; }
.ff-form .ghost>button{ background:transparent; color:#eaf3ff; }
.ff-form .ghost>button:hover{ background:rgba(255,255,255,.08); }
.ff-powered-login{
  position:fixed; left:14px; bottom:10px; display:flex; align-items:center; gap:8px; font-size:11.5px; opacity:.9; color:#eaf3ff; text-shadow:0 1px 8px rgba(0,0,0,.5);
}
.ff-powered-login img{ height:16px; width:auto; opacity:.95; }

/* Responsividade do login */
@media (max-width:1200px){
  .ff-login-shell{ gap:40px; grid-template-columns:1.1fr 1fr; padding:32px 4vw; }
  .ff-brand-login img{ width:120px; }
  .ff-title{ font-size:42px; }
}
@media (max-width:900px){
  .ff-login-shell{ grid-template-columns:1fr; gap:24px; justify-items:start; }
  .ff-form{ width:520px; max-width:96%; }
}
@media (max-width:600px){
  .ff-brand-login{ gap:16px; padding:18px; }
  .ff-brand-login img{ width:90px; }
  .ff-title{ font-size:34px; }
  .ff-form{ width:100%; max-width:calc(100vw - 32px); padding:18px 16px; }
  .ff-login-shell{ padding:18px; gap:18px; }
}
</style>
""", unsafe_allow_html=True)

# ============== Conexão Supabase ==============
if "sb" not in st.session_state:
    st.session_state.sb = get_supabase()
sb = st.session_state.sb

# ============== Auth helpers ==============
def _signin(email: str, password: str):
    sb.auth.sign_in_with_password({"email": email, "password": password})

def _signup(email: str, password: str):
    sb.auth.sign_up({"email": email, "password": password})

def _user():
    sess = sb.auth.get_session()
    return sess.user if sess and sess.user else None

def _signout():
    sb.auth.sign_out()
    st.session_state.clear()
    st.rerun()

# ============== Login Full-screen (sem sidebar) ==============
def render_login_fullscreen():
    # classes para esconder header/rodapé/sidebar e aplicar bg
    st.markdown('<div class="ff-login-hide ff-login-bg">', unsafe_allow_html=True)

    st.markdown('<div class="ff-login-shell">', unsafe_allow_html=True)
    # Coluna esquerda (marca)
    st.markdown("""
    <div class="ff-brand-login">
      <img src="assets/logo_family_finance.png" />
      <div>
        <h1 class="ff-title">Family<br/>Finance</h1>
        <div class="ff-sub">Gestão financeira familiar — moderna, segura e precisa.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Coluna direita (form)
    st.markdown('<div class="ff-form">', unsafe_allow_html=True)
    st.markdown("<h4>Acessar sua conta</h4>", unsafe_allow_html=True)
    email = st.text_input("E-mail", key="ff_login_email", placeholder="voce@email.com")
    pwd   = st.text_input("Senha", key="ff_login_pwd", type="password", placeholder="••••••••")
    c1, c2 = st.columns(2)
    with c1:
        do_login = st.button("Entrar", key="ff_btn_login", use_container_width=True, type="primary")
    with c2:
        do_signup = st.button("Criar conta", key="ff_btn_signup", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)  # fecha ff-form
    st.markdown("</div>", unsafe_allow_html=True)  # fecha shell

    st.markdown('<div class="ff-powered-login">powered by <img src="assets/logo_automaGO.png"/></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # fecha wrappers

    def _valid():
        if not email.strip():
            st.warning("Informe seu e-mail."); return False
        if not pwd:
            st.warning("Informe sua senha."); return False
        if len(pwd) < 6:
            st.warning("A senha deve ter pelo menos 6 caracteres."); return False
        return True

    if do_login and _valid():
        try:
            _signin(email.strip(), pwd)
            if _user():
                st.session_state.auth_ok = True
                st.rerun()
            else:
                st.error("Não foi possível autenticar. Verifique e-mail e senha.")
        except Exception as e:
            st.error(f"Falha no login: {e}")

    if do_signup and _valid():
        try:
            _signup(email.strip(), pwd)
            st.success("Conta criada. Se a confirmação por e-mail estiver ativada, confirme para poder entrar.")
        except Exception as e:
            st.error(f"Falha ao criar conta: {e}")

# ============== Estado de autenticação ==============
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = _user() is not None

if not st.session_state.auth_ok:
    render_login_fullscreen()
    st.stop()

# ============== Sidebar (só após login) ==============
with st.sidebar:
    st.markdown('<div class="ff-brand"><div class="ff-card">', unsafe_allow_html=True)
    st.image("assets/logo_family_finance.png", width=116)
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)

    usr = _user()
    st.markdown(f'<div class="user-email-display">Logado: {usr.email if usr else ""}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)
    st.markdown('<div class="ff-logout">', unsafe_allow_html=True)
    if st.button("Sair", key="sidebar_logout_button"):
        _signout()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)
    st.markdown('<div class="ff-powered"><div class="small">Powered by</div>', unsafe_allow_html=True)
    st.image("assets/logo_automaGO.png", width=96)
    st.markdown('</div>', unsafe_allow_html=True)

# ============== Bootstrap household/member ==============
if "HOUSEHOLD_ID" not in st.session_state:
    def _find_membership(client, user_id: str):
        try:
            data = client.table("members").select("id, household_id").eq("user_id", user_id).limit(1).execute().data
            if data:
                return {"household_id": data[0]["household_id"], "member_id": data[0]["id"]}
        except Exception:
            pass
        return None

    def bootstrap_user(client):
        me = _user()
        if not me:
            st.error("Sessão perdida. Faça login novamente."); st.stop()
        # já membro?
        m = _find_membership(client, me.id)
        if m:
            return m
        # tenta aceitar convites pendentes
        try: client.rpc("accept_pending_invite").execute()
        except Exception: pass
        m = _find_membership(client, me.id)
        if m:
            return m
        # cria família
        res = client.rpc("create_household_and_member", {"display_name": "Você"}).execute().data
        return {"household_id": res[0]["household_id"], "member_id": res[0]["member_id"]}

    ids = bootstrap_user(sb)
    st.session_state.HOUSEHOLD_ID = ids["household_id"]
    st.session_state.MY_MEMBER_ID = ids["member_id"]

# ============== Notificações de contas a vencer ==============
notify_due_bills(sb, st.session_state.HOUSEHOLD_ID, _user())

# ============== Dados do Dashboard (Home) ==============
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
        from dateutil.relativedelta import relativedelta
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
        monthly_data.append({"Mês": month_start_calc.strftime("%Y-%m"), "Receitas": income, "Despesas": expense, "Saldo": income - expense})
    monthly_df = pd.DataFrame(monthly_data).sort_values("Mês", ascending=True)

    return {
        "current_month_income": total_income_current_month,
        "current_month_expense": total_expense_current_month,
        "current_month_balance": current_balance,
        "expense_categories_df": expense_categories,
        "monthly_evolution_df": monthly_df,
        "all_transactions_current_month": current_month_tx
    }

# ============== Navegação topo (botões) ==============
def top_menu():
    st.markdown('<div class="top-menu">', unsafe_allow_html=True)

    # Preferir page_link (Streamlit >= 1.32). Se não existir, usar fallback com switch_page.
    has_page_link = hasattr(st, "page_link")

    if has_page_link:
        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            st.page_link("pages/2_Financeiro.py", label="💼 Financeiro", use_container_width=True)
        with c2:
            st.page_link("pages/4_Dashboards.py", label="📊 Dashboards", use_container_width=True)
        with c3:
            st.page_link("pages/3_Administração.py", label="🧰 Administração", use_container_width=True)
    else:
        # Fallback com botões
        def _go(targets):
            for t in targets:
                try:
                    st.switch_page(t); return
                except Exception:
                    pass
        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            if st.button("💼 Financeiro", key="m_fin", use_container_width=True): 
                _go(["pages/2_Financeiro.py", "2_Financeiro", "Financeiro"])
        with c2:
            if st.button("📊 Dashboards", key="m_dash", use_container_width=True): 
                _go(["pages/4_Dashboards.py", "4_Dashboards", "Dashboards"])
        with c3:
            if st.button("🧰 Administração", key="m_admin", use_container_width=True): 
                _go(["pages/3_Administração.py", "3_Administração", "Administracao", "Administração"])

    st.markdown('</div>', unsafe_allow_html=True)

# ============== Render Home (Dashboard) ==============
def show_home_dashboard():
    st.markdown('<h1 class="dashboard-title">✨ Dashboard Financeiro Familiar</h1>', unsafe_allow_html=True)

    # Menu superior
    top_menu()

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
            <h3>📊 Saldo</h3>
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
                values="Valor", names="Categoria",
                title="Distribuição das Despesas", hole=0.4,
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
            fig_line.add_trace(go.Scatter(x=dashboard_data["monthly_evolution_df"]["Mês"], y=dashboard_data["monthly_evolution_df"]["Receitas"], mode='lines+markers', name='Receitas', line=dict(color='#22c55e', width=3)))
            fig_line.add_trace(go.Scatter(x=dashboard_data["monthly_evolution_df"]["Mês"], y=dashboard_data["monthly_evolution_df"]["Despesas"], mode='lines+markers', name='Despesas', line=dict(color='#ef4444', width=3)))
            fig_line.add_trace(go.Scatter(x=dashboard_data["monthly_evolution_df"]["Mês"], y=dashboard_data["monthly_evolution_df"]["Saldo"], mode='lines+markers', name='Saldo', line=dict(color='#0ea5e9', width=4, dash='dot')))
            fig_line.update_layout(title='Receitas, Despesas e Saldo', xaxis_title='Mês', yaxis_title='Valor',
                                   hovermode='x unified', legend_title_text='Legenda', height=400)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Dados insuficientes para evolução mensal.")
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

# ============== Renomeia o item 'app' no nav nativo para '🏠 Home' ==============
st.markdown("""
<script>
const fixNav = () => {
  const nav = document.querySelector('div[data-testid="stSidebarNav"]');
  if(!nav) return;
  const links = nav.querySelectorAll('a');
  links.forEach(a => { if(a.textContent.trim().toLowerCase() === 'app'){ a.textContent = '🏠 Home'; }});
};
setTimeout(fixNav, 80);
</script>
""", unsafe_allow_html=True)

# ============== Mostra Home ==============
show_home_dashboard()
