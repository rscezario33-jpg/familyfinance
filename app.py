# app.py — v7.2
from __future__ import annotations
from datetime import date, datetime, timedelta
import uuid
import pandas as pd
import streamlit as st
from supabase_client import get_supabase

st.set_page_config(page_title="Finanças Familiares — v7.2", layout="wide")

# ====== estilo ======
st.markdown("""
<style>
.main .block-container { max-width: 1200px; padding-top: .5rem; }
.card { background: linear-gradient(180deg,#fff 0%,#f8fafc 100%);
  border:1px solid #e2e8f0; border-radius:16px; padding:16px 18px;
  box-shadow:0 6px 20px rgba(0,0,0,.06); margin-bottom:12px; }
.stTextInput input, .stNumberInput input, .stDateInput input { border-radius:10px !important; }
.stSelectbox div[data-baseweb="select"] > div { border-radius:10px !important; }
.stButton>button { border-radius:10px; padding:.6rem 1rem; font-weight:600;
  border:1px solid #0ea5e9; transition:.15s; }
.stButton>button:hover { transform: translateY(-1px); }
.badge { display:inline-flex; align-items:center; gap:.5rem; background:#eef6ff; color:#0369a1;
  border:1px solid #bfdbfe; padding:.35rem .6rem; border-radius:999px; font-weight:600; margin:4px 6px 0 0; }
.badge.red{background:#fff1f2;color:#9f1239;border-color:#fecdd3;}
.badge.green{background:#ecfdf5;color:#065f46;border-color:#bbf7d0;}
</style>
""", unsafe_allow_html=True)

sb = get_supabase()

# ====== auth ======
def _user():
    sess = sb.auth.get_session()
    try:
        return sess.user if sess and sess.user else None
    except Exception:
        return None

def _signin(email: str, password: str):
    sb.auth.sign_in_with_password({"email": email, "password": password})

def _signup(email: str, password: str):
    sb.auth.sign_up({"email": email, "password": password})

def _signout():
    sb.auth.sign_out()

with st.sidebar:
    st.header("🔐 Login")
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
    if not st.session_state.auth_ok:
        email = st.text_input("Email")
        pwd   = st.text_input("Senha", type="password")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Entrar"):
                try:
                    _signin(email,pwd)
                    st.session_state.auth_ok = True
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with c2:
            if st.button("Criar conta"):
                try:
                    _signup(email,pwd)
                    st.success("Conta criada. Faça login.")
                except Exception as e:
                    st.error(str(e))
    else:
        u = _user()
        if u: st.caption(f"Logado: {u.email}")
        if st.button("Sair"):
            _signout(); st.session_state.auth_ok = False; st.rerun()

if not st.session_state.auth_ok:
    st.stop()

user = _user()
assert user, "Usuário não autenticado."

# ====== bootstrap (aceita convites + cria família/membro) ======
@st.cache_data(show_spinner=False)
def bootstrap(user_id: str):
    try:
        sb.rpc("accept_pending_invite").execute()
    except Exception:
        pass
    res = sb.rpc("create_household_and_member", {"display_name": "Você"}).execute().data
    item = res[0] if isinstance(res, list) and res else res
    return {"household_id": item["household_id"], "member_id": item["member_id"]}

ids = bootstrap(user.id)
HOUSEHOLD_ID = ids["household_id"]; MY_MEMBER_ID = ids["member_id"]

# ====== helpers ======
def to_brl(v: float | int | None) -> str:
    v = v or 0
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _safe_to_date(s) -> date | None:
    try:
        return pd.to_datetime(s).date() if s else None
    except Exception:
        return None

def fetch_members():
    q = sb.table("members").select("id,display_name,role").eq("household_id", HOUSEHOLD_ID)
    try:
        return q.order("display_name", desc=False).execute().data
    except Exception:
        return q.execute().data

def fetch_categories():
    q = sb.table("categories").select("id,name,kind").eq("household_id", HOUSEHOLD_ID)
    try:
        return q.order("name", desc=False).execute().data
    except Exception:
        return q.execute().data

def fetch_accounts(active_only=False):
    q = sb.table("accounts").select("id,name,is_active,type").eq("household_id", HOUSEHOLD_ID)
    if active_only:
        q = q.eq("is_active", True)
    try:
        return q.order("name", desc=False).execute().data
    except Exception:
        return q.execute().data

def fetch_cards(active_only=True):
    q = sb.table("credit_cards").select("id,name,limit_amount,closing_day,due_day,is_active").eq("household_id", HOUSEHOLD_ID)
    if active_only:
        q = q.eq("is_active", True)
    try:
        return q.order("name", desc=False).execute().data
    except Exception:
        return q.execute().data

def fetch_card_limits():
    try:
        return sb.table("v_card_limit").select("id,available_limit").eq("household_id", HOUSEHOLD_ID).execute().data
    except Exception:
        return []

# ====== TRANSACTIONS: robustez máxima contra RLS/ORDER ======
def _tx_select_base():
    # Colunas explicitamente listadas para evitar RLS que bloqueia colunas “sensíveis”
    return sb.table("transactions").select(
        "id,household_id,occurred_at,due_date,type,amount,planned_amount,paid_amount,"
        "is_paid,paid_at,description,category_id,account_id,member_id,payment_method,"
        "card_id,installment_group_id,installment_no,installment_total,attachment_url,created_by"
    ).eq("household_id", HOUSEHOLD_ID)

def fetch_tx(start: date, end: date):
    """
    Plano A: filtra por occurred_at no SQL e ordena por due_date.
    Plano B: filtra por occurred_at no SQL e ordena por occurred_at.
    Plano C: fetch simples (sem filtro) + filtro/ordem no Python (limit para segurança).
    """
    base = _tx_select_base().gte("occurred_at", start.isoformat()).lte("occurred_at", end.isoformat())
    # Plano A
    try:
        return base.order("due_date", desc=False).execute().data
    except Exception:
        pass
    # Plano B
    try:
        return base.order("occurred_at", desc=False).execute().data
    except Exception:
        pass
    # Plano C — último recurso: sem filtro de data no banco
    try:
        raw = _tx_select_base().limit(5000).execute().data  # limite de segurança
        if not raw:
            return []
        # filtra no Python
        out = []
        for r in raw:
            od = _safe_to_date(r.get("occurred_at"))
            if od and (start <= od <= end):
                out.append(r)
        # ordena por due_date (nulos por último) e depois occurred_at
        def _key(r):
            dd = _safe_to_date(r.get("due_date"))
            od = _safe_to_date(r.get("occurred_at"))
            return (dd is None, dd or date.min, od or date.min)
        out.sort(key=_key)
        return out
    except Exception as e:
        # Último fallback: retorna array vazio para não quebrar a página
        return []

def fetch_tx_due(start: date, end: date):
    """
    Fluxo previsto (due_date no range; se nulo, caiu pro occurred_at):
    A) Tenta uma única query com OR (PostgREST).
    B) Tenta duas queries separadas e concatena.
    C) Fetch simples sem filtro e filtra/ordena no Python.
    """
    # A) OR
    try:
        q = _tx_select_base()
        expr = (
            f"and(due_date.gte.{start.isoformat()},due_date.lte.{end.isoformat()}),"
            f"and(due_date.is.null,occurred_at.gte.{start.isoformat()},occurred_at.lte.{end.isoformat()})"
        )
        q = q.or_(expr).order("due_date", desc=False, nulls_first=True).order("occurred_at", desc=False)
        return q.execute().data
    except Exception:
        pass
    # B) Duas queries
    try:
        a = _tx_select_base().gte("due_date", start.isoformat()).lte("due_date", end.isoformat()).execute().data
    except Exception:
        a = []
    try:
        b = _tx_select_base().is_("due_date", "null").gte("occurred_at", start.isoformat()).lte("occurred_at", end.isoformat()).execute().data
    except Exception:
        b = []
    if a or b:
        out = (a or []) + (b or [])
        # ordena (nulos de due_date primeiro, depois occurred_at)
        def _key(r):
            dd = _safe_to_date(r.get("due_date"))
            od = _safe_to_date(r.get("occurred_at"))
            return (dd is not None, dd or date.min, od or date.min)
        out.sort(key=_key)
        return out
    # C) Sem filtro no banco
    try:
        raw = _tx_select_base().limit(5000).execute().data
        if not raw:
            return []
        out = []
        for r in raw:
            dd = _safe_to_date(r.get("due_date"))
            od = _safe_to_date(r.get("occurred_at"))
            eff = dd or od
            if eff and (start <= eff <= end):
                out.append(r)
        def _key2(r):
            dd = _safe_to_date(r.get("due_date"))
            od = _safe_to_date(r.get("occurred_at"))
            return (dd is not None, dd or date.min, od or date.min)
        out.sort(key=_key2)
        return out
    except Exception:
        return []

# ====== sidebar menu ======
with st.sidebar:
    st.header("📍 Navegação")
    section = st.radio("Área", ["🏠 Entrada","💼 Financeiro","🧰 Administração","📊 Dashboards"], index=0)
    st.markdown("---")
    if st.button("🔄 Recarregar dados"):
        st.cache_data.clear(); st.rerun()

st.title("Finanças Familiares — v7.2")

# ====== Entrada ======
if section == "🏠 Entrada":
    first_day = date.today().replace(day=1)
    txm = fetch_tx(first_day, date.today())
    res = sum([
        ((t.get("paid_amount") if t.get("is_paid") else (t.get("planned_amount") or t.get("amount") or 0.0)))
        * (1 if t["type"] == "income" else -1)
        for t in (txm or [])
    ])
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Período", f"{first_day.strftime('%d/%m')}—{date.today().strftime('%d/%m')}")
    with c2: st.metric("Lançamentos", len(txm or []))
    with c3: st.metric("Resultado (previsto)", to_brl(res))

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Visão por membro (mês)")
    mems = fetch_members(); mem_map = {m["id"]: m["display_name"] for m in (mems or [])}
    if txm:
        df = pd.DataFrame(txm)
        df["valor_eff"] = df.apply(
            lambda r: ((r.get("paid_amount") if r.get("is_paid") else (r.get("planned_amount") or r.get("amount") or 0.0)))
                      * (1 if r["type"]=="income" else -1),
            axis=1
        )
        df["Membro"] = df["member_id"].map(mem_map).fillna("—")
        s = df.groupby("Membro", as_index=False)["valor_eff"].sum()
        st.bar_chart(s, x="Membro", y="valor_eff")
    else:
        st.info("Sem lançamentos no mês.")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("⚡ Lançar agora"):
        st.session_state.section = "💼 Financeiro"
        st.session_state.sub = "Lançamentos"
        st.rerun()

# ====== Financeiro ======
if section == "💼 Financeiro":
    st.tabs(["Lançamentos","Movimentações","Receitas/Despesas fixas","Orçamentos","Fluxo de caixa"])

    # ————— Lançamentos —————
    with st.expander("➕ Lançar (rápido / parcelado / cartão)", True):
        cats = fetch_categories(); cat_map = {c["name"]: c for c in (cats or [])}
        accs = fetch_accounts(True); acc_map = {a["name"]: a for a in (accs or [])}
        cards = fetch_cards(True); card_map = {c["name"]: c for c in (cards or [])}

        with st.form("quick_tx"):
            col1,col2 = st.columns(2)
            with col1:
                tipo = st.selectbox("Tipo", ["income","expense"], index=1, format_func=lambda x: {"income":"Receita","expense":"Despesa"}[x])
                cat  = st.selectbox("Categoria", list(cat_map.keys()) or ["Mercado"])
                desc = st.text_input("Descrição")
                data = st.date_input("Data", value=date.today())
                due  = st.date_input("Vencimento (opcional)", value=date.today())
            with col2:
                val  = st.number_input("Valor", min_value=0.0, step=10.0)
                method = st.selectbox("Forma de pagamento", ["account","card"], index=0, format_func=lambda x: "Conta" if x=="account" else "Cartão")
                acc = st.selectbox("Conta", list(acc_map.keys()) or ["Conta Corrente"])
                card_name = st.selectbox("Cartão (se aplicável)", ["—"] + list(card_map.keys()))
                parcelado = st.checkbox("Parcelado?")
                n_parc = st.number_input("Nº parcelas", min_value=2, max_value=36, value=2, disabled=not parcelado)

            ok = st.form_submit_button("Lançar")
            if ok:
                try:
                    cat_id = (cat_map.get(cat) or {}).get("id")
                    acc_id = (acc_map.get(acc) or {}).get("id")
                    card_id = (card_map.get(card_name) or {}).get("id") if method=="card" and card_name!="—" else None

                    if tipo=="expense" and parcelado:
                        sb.rpc("create_installments", {
                            "p_household": HOUSEHOLD_ID,
                            "p_member": MY_MEMBER_ID,
                            "p_account": acc_id,
                            "p_category": cat_id,
                            "p_desc": desc,
                            "p_total": float(val),
                            "p_n": int(n_parc),
                            "p_first_due": due.isoformat(),
                            "p_payment_method": method,
                            "p_card_id": card_id
                        }).execute()
                    else:
                        planned = float(val)
                        sb.table("transactions").insert({
                            "household_id": HOUSEHOLD_ID, "member_id": MY_MEMBER_ID,
                            "account_id": acc_id, "category_id": cat_id,
                            "type": tipo,
                            "amount": float(val),
                            "planned_amount": planned,
                            "occurred_at": data.isoformat(),
                            "due_date": due.isoformat(),
                            "description": desc,
                            "payment_method": method,
                            "card_id": card_id,
                            "created_by": user.id
                        }).execute()
                    st.toast("✅ Lançamento registrado!", icon="✅"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Falha: {e}")

    # ————— Movimentações —————
    with st.expander("📋 Movimentações"):
        ini = st.date_input("Início", value=date.today().replace(day=1), key="mv_ini")
        fim = st.date_input("Fim", value=date.today(), key="mv_fim")
        tx = fetch_tx(ini, fim)
        if not tx:
            st.info("Sem lançamentos.")
        else:
            df = pd.DataFrame(tx)
            # datas seguras
            df["Data"] = df["occurred_at"].apply(lambda x: _safe_to_date(x).strftime("%d/%m/%Y") if _safe_to_date(x) else "")
            df["Venc"] = df["due_date"].apply(lambda x: _safe_to_date(x).strftime("%d/%m/%Y") if _safe_to_date(x) else "")
            df["Tipo"] = df["type"].map({"income":"Receita","expense":"Despesa"})
            df["Previsto"] = df["planned_amount"].fillna(df["amount"]).fillna(0.0)
            df["Pago?"] = df["is_paid"].fillna(False)
            df["Pago (R$)"] = df["paid_amount"].fillna("")
            df_show = df[["Data","Venc","Tipo","description","Previsto","Pago?","Pago (R$)","attachment_url","id"]]
            st.dataframe(df_show.rename(columns={"description":"Descrição","attachment_url":"Boleto"}), use_container_width=True, hide_index=True)

            # marcar pagamento
            st.markdown("### Marcar pagamento")
            tx_id = st.selectbox("Transação", df["id"])
            pago_val = st.number_input("Valor pago (R$)", min_value=0.0, step=10.0)
            pago_dt  = st.date_input("Data pagamento", value=date.today())
            if st.button("✅ Confirmar pagamento"):
                try:
                    sb.rpc("mark_transaction_paid", {"p_tx_id": tx_id, "p_amount": float(pago_val), "p_date": pago_dt.isoformat()}).execute()
                    st.toast("Pagamento registrado!", icon="✅"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Falha ao marcar pago: {e}")

            # anexo de boleto
            st.markdown("### Anexar boleto")
            tx_id2 = st.selectbox("Transação (anexo)", df["id"], key="att_tx")
            up = st.file_uploader("Arquivo (PDF/IMG)", type=["pdf","png","jpg","jpeg"], key="att_file")
            if up and st.button("📎 Enviar anexo"):
                try:
                    fname = f"{uuid.uuid4().hex}_{up.name}"
                    content = up.read()
                    # Produção: usar Supabase Storage; aqui deixamos um placeholder:
                    url = f"uploaded:{fname}"
                    sb.table("transactions").update({"attachment_url": url}).eq("id", tx_id2).execute()
                    st.toast("Anexo salvo!", icon="📎"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Falha no anexo: {e}")

    # ————— Fixas —————
    with st.expander("♻️ Receitas/Despesas fixas"):
        cats = fetch_categories(); cat_map = {c["name"]: c for c in (cats or [])}
        accs = fetch_accounts(True); acc_map = {a["name"]: a for a in (accs or [])}
        cards = fetch_cards(True); card_map = {c["name"]: c for c in (cards or [])}

        with st.form("fixas_form"):
            col1,col2 = st.columns(2)
            with col1:
                tipo = st.selectbox("Tipo", ["income","expense"], index=1, format_func=lambda x: {"income":"Receita","expense":"Despesa"}[x])
                cat  = st.selectbox("Categoria", list(cat_map.keys()) or ["Energia","Salário"])
                desc = st.text_input("Descrição (ex.: [FIXA] Energia)")
                start_due = st.date_input("Vencimento inicial", value=date.today())
            with col2:
                previsto = st.number_input("Valor previsto (R$)", min_value=0.0, step=10.0)
                method = st.selectbox("Forma pagamento", ["account","card"], index=0, format_func=lambda x: "Conta" if x=="account" else "Cartão")
                acc = st.selectbox("Conta", list(acc_map.keys()) or ["Conta Corrente"])
                card_name = st.selectbox("Cartão (se aplicável)", ["—"] + list(card_map.keys()))
                meses = st.number_input("Copiar para próximos (meses)", min_value=0, max_value=24, value=0)
            okf = st.form_submit_button("Criar fixa(s)")
            if okf:
                try:
                    cat_id = (cat_map.get(cat) or {}).get("id")
                    acc_id = (acc_map.get(acc) or {}).get("id")
                    card_id = (card_map.get(card_name) or {}).get("id") if method=="card" and card_name!="—" else None

                    # cria do mês inicial
                    sb.table("transactions").insert({
                        "household_id": HOUSEHOLD_ID, "member_id": MY_MEMBER_ID,
                        "account_id": acc_id, "category_id": cat_id,
                        "type": tipo,
                        "amount": float(previsto),
                        "planned_amount": float(previsto),
                        "occurred_at": start_due.isoformat(),
                        "due_date": start_due.isoformat(),
                        "description": desc,
                        "payment_method": method,
                        "card_id": card_id,
                        "created_by": user.id
                    }).execute()

                    # copia para próximos meses
                    d = start_due
                    for _ in range(int(meses)):
                        d = (d + timedelta(days=32)).replace(day=min(start_due.day, 28))
                        sb.table("transactions").insert({
                            "household_id": HOUSEHOLD_ID, "member_id": MY_MEMBER_ID,
                            "account_id": acc_id, "category_id": cat_id,
                            "type": tipo,
                            "amount": float(previsto),
                            "planned_amount": float(previsto),
                            "occurred_at": d.isoformat(),
                            "due_date": d.isoformat(),
                            "description": desc,
                            "payment_method": method,
                            "card_id": card_id,
                            "created_by": user.id
                        }).execute()
                    st.toast("✅ Fixas criadas!", icon="✅"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Falha: {e}")

        st.caption("Ao marcar pagamento em Movimentações: se não informar 'Valor pago', usamos o previsto; a 'Data de pagamento' padrão é hoje.")

    # ————— Orçamentos —————
    with st.expander("💡 Orçamentos"):
        month_str = st.text_input("Mês (YYYY-MM)", value=date.today().strftime("%Y-%m"))
        cats = fetch_categories(); cat_by_name = {c["name"]: c for c in (cats or [])}
        colb1,colb2 = st.columns([2,1])
        with colb1: cat_name = st.selectbox("Categoria", list(cat_by_name.keys()) or ["Mercado"])
        with colb2: val_orc = st.number_input("Orçado (R$)", min_value=0.0, step=50.0)
        if st.button("Salvar orçamento"):
            try:
                cid = (cat_by_name.get(cat_name) or {}).get("id")
                sb.rpc("upsert_budget", {"p_household": HOUSEHOLD_ID, "p_month": month_str, "p_category": cid, "p_amount": float(val_orc)}).execute()
                st.toast("✅ Salvo!", icon="✅")
            except Exception as e:
                st.error(f"Falha: {e}")
        st.markdown("### Comparativo do mês")
        try:
            res = sb.rpc("budget_vs_actual", {"p_household": HOUSEHOLD_ID, "p_month": month_str}).execute().data
        except Exception as e:
            res = []; st.error(f"Falha: {e}")
        dfba = pd.DataFrame(res) if res else pd.DataFrame()
        if dfba.empty:
            st.info("Sem dados.")
        else:
            dfba["Tipo"] = dfba["kind"].map({"income":"Receita","expense":"Despesa"})
            dfba["Categoria"] = dfba["category_name"]
            dfba["Orçado"] = dfba["budget"].fillna(0)
            dfba["Realizado"] = dfba["actual"].fillna(0)
            st.dataframe(dfba[["Categoria","Tipo","Orçado","Realizado"]], use_container_width=True, hide_index=True)

    # ————— Fluxo de caixa (previsto) —————
    with st.expander("📈 Fluxo de caixa (previsto)"):
        f1,f2 = st.columns(2)
        with f1: ini = st.date_input("Início", value=date.today().replace(day=1), key="fx_ini")
        with f2: fim = st.date_input("Fim", value=date.today()+timedelta(days=60), key="fx_fim")
        txx = fetch_tx_due(ini, fim)
        if not txx:
            st.info("Sem previstos no período.")
        else:
            df = pd.DataFrame(txx)
            def eff(r):
                v = r.get("paid_amount") if r.get("is_paid") else (r.get("planned_amount") or r.get("amount") or 0)
                return v if r["type"]=="income" else -v
            df["eff"] = df.apply(eff, axis=1)
            df["Quando"] = df.apply(lambda r: (_safe_to_date(r.get("due_date")) or _safe_to_date(r.get("occurred_at"))), axis=1)
            df = df[df["Quando"].notna()]
            tot = df.groupby("Quando", as_index=False)["eff"].sum()
            st.line_chart(tot, x="Quando", y="eff")
            cta = df[df["type"]=="income"]["eff"].sum()
            ctd = -df[df["type"]=="expense"]["eff"].sum()
            st.metric("Receitas previstas", to_brl(cta))
            st.metric("Despesas previstas", to_brl(ctd))

# ====== Administração ======
if section == "🧰 Administração":
    tabs = st.tabs(["Membros","Contas","Categorias","Cartões"])

    # Membros
    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Membros")
        nm = st.text_input("Seu nome de exibição", value="Você")
        if st.button("Salvar"):
            try:
                sb.table("members").upsert({
                    "household_id": HOUSEHOLD_ID,"user_id": user.id,"display_name": nm.strip(),"role":"owner"
                }, on_conflict="household_id,user_id").execute()
                st.toast("✅ Salvo!", icon="✅"); st.cache_data.clear(); st.rerun()
            except Exception as e:
                st.error(str(e))
        mems = fetch_members()
        if mems:
            chips = " ".join([f'<span class="badge">👤 {m["display_name"]}{" · owner" if m["role"]=="owner" else ""}</span>' for m in mems])
            st.markdown(chips, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Contas
    with tabs[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Contas")
        an = st.text_input("Nome")
        at = st.selectbox("Tipo", ["checking","savings","wallet","credit"])
        ob = st.number_input("Saldo inicial", min_value=0.0, step=50.0)
        if st.button("Salvar conta"):
            try:
                sb.table("accounts").insert({
                    "household_id": HOUSEHOLD_ID,"name": an.strip(),"type":at,"opening_balance":float(ob),"currency":"BRL","is_active":True
                }).execute()
                st.toast("✅ Conta salva!", icon="✅"); st.cache_data.clear(); st.rerun()
            except Exception as e:
                st.error(str(e))
        accs = fetch_accounts(False)
        for a in (accs or []):
            st.write(("✅ " if a["is_active"] else "❌ ") + a["name"])
        st.markdown('</div>', unsafe_allow_html=True)

    # Categorias
    with tabs[2]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Categorias")
        cn = st.text_input("Nome da categoria")
        ck = st.selectbox("Tipo", ["income","expense"], format_func=lambda k: {"income":"Receita","expense":"Despesa"}[k])
        if st.button("Salvar categoria"):
            try:
                sb.table("categories").insert({
                    "household_id": HOUSEHOLD_ID,"name": cn.strip(),"kind": ck
                }).execute()
                st.toast("✅ Categoria salva!", icon="✅"); st.cache_data.clear(); st.rerun()
            except Exception as e:
                st.error(str(e))
        cats = fetch_categories()
        if cats:
            chips_inc = " ".join([f'<span class="badge green">#{c["name"]}</span>' for c in cats if c["kind"]=="income"])
            chips_exp = " ".join([f'<span class="badge red">#{c["name"]}</span>' for c in cats if c["kind"]=="expense"])
            st.markdown("**Receitas**"); st.markdown(chips_inc or "_(vazio)_", unsafe_allow_html=True)
            st.markdown("**Despesas**"); st.markdown(chips_exp or "_(vazio)_", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Cartões (somente aqui)
    with tabs[3]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Cartões")
        with st.form("novo_cartao_admin"):
            c1,c2,c3,c4 = st.columns(4)
            with c1: nm = st.text_input("Nome do cartão")
            with c2: lim = st.number_input("Limite (R$)", min_value=0.0, step=100.0)
            with c3: closing = st.number_input("Fechamento (1-28)", min_value=1, max_value=28, value=5)
            with c4: due = st.number_input("Vencimento (1-28)", min_value=1, max_value=28, value=15)
            okc = st.form_submit_button("Salvar cartão")
            if okc and nm.strip():
                try:
                    sb.table("credit_cards").insert({
                        "household_id": HOUSEHOLD_ID, "name": nm.strip(),
                        "limit_amount": float(lim), "closing_day": int(closing), "due_day": int(due),
                        "is_active": True, "created_by": user.id
                    }).execute()
                    st.toast("✅ Cartão salvo!", icon="✅"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Falha: {e}")

        cards = fetch_cards(False)
        limits = fetch_card_limits(); limap = {x.get("id"): x for x in (limits or [])}
        if not cards:
            st.info("Nenhum cartão cadastrado.")
        else:
            for c in cards:
                colA,colB,colC,colD = st.columns([4,2,2,2])
                with colA: st.write(f"💳 **{c.get('name','(sem nome)')}** · Fechamento {c.get('closing_day')}/ Venc {c.get('due_day')}")
                with colB: st.write(f"Limite: {to_brl(c.get('limit_amount'))}")
                with colC: st.write("Disponível: " + to_brl(limap.get(c["id"],{}).get("available_limit", c.get("limit_amount",0))))
                with colD:
                    if c.get("is_active"):
                        if st.button("Desativar", key=f"card_d_{c['id']}"):
                            sb.table("credit_cards").update({"is_active": False}).eq("id", c["id"]).execute()
                            st.cache_data.clear(); st.rerun()
                    else:
                        if st.button("Ativar", key=f"card_a_{c['id']}"):
                            sb.table("credit_cards").update({"is_active": True}).eq("id", c["id"]).execute()
                            st.cache_data.clear(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ====== Dashboards ======
if section == "📊 Dashboards":
    tabs = st.tabs(["Relatórios","Fluxo de caixa"])
    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Relatórios")
        ini = st.date_input("Início", value=date.today().replace(day=1))
        fim = st.date_input("Fim", value=date.today())
        tx = fetch_tx(ini, fim)
        mems = fetch_members(); cats = fetch_categories()
        if not tx:
            st.info("Sem lançamentos.")
        else:
            df = pd.DataFrame(tx)
            mem_map = {m["id"]: m["display_name"] for m in (mems or [])}
            cat_map = {c["id"]: c["name"] for c in (cats or [])}
            df["valor_eff"] = df.apply(
                lambda r: ((r.get("paid_amount") if r.get("is_paid") else (r.get("planned_amount") or r.get("amount") or 0.0)))
                          * (1 if r["type"]=="income" else -1),
                axis=1
            )
            df["Membro"] = df["member_id"].map(mem_map).fillna("—")
            df["Categoria"] = df["category_id"].map(cat_map).fillna("—")
            st.markdown("#### Por membro")
            st.bar_chart(df.groupby("Membro", as_index=False)["valor_eff"].sum(), x="Membro", y="valor_eff")
            st.markdown("#### Por categoria")
            st.bar_chart(df.groupby("Categoria", as_index=False)["valor_eff"].sum(), x="Categoria", y="valor_eff")
        st.markdown('</div>', unsafe_allow_html=True)
    with tabs[1]:
        st.info("Use também o Financeiro › Fluxo de caixa (previsto) para ver o futuro por data de vencimento.")
