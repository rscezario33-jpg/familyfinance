# app.py — v9.3 (alinhado ao seu schema atual)
from __future__ import annotations
from datetime import date, timedelta
import uuid
import pandas as pd
import streamlit as st
from supabase_client import get_supabase

st.set_page_config(page_title="Finanças da Família — v9.3", layout="wide")

# ====== Estilo ======
st.markdown("""
<style>
.main .block-container { max-width: 1180px; padding-top: .5rem; }
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
.small {font-size: 12px; color:#475569}
</style>
""", unsafe_allow_html=True)

sb = get_supabase()

# ====== Helpers ======
PT_TYPES = {
    "checking":"Conta corrente","savings":"Poupança","wallet":"Carteira",
    "credit":"Cartão de crédito","investment":"Investimento","other":"Outra"
}
EN_TYPES = {v:k for k,v in PT_TYPES.items()}

def to_brl(v) -> str:
    v = 0.0 if v is None else float(v)
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def month_bounds(y: int, m: int) -> tuple[date, date]:
    ini = date(y, m, 1)
    fim = (ini + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return ini, fim

def select_competence(key_prefix: str, default: date | None = None) -> tuple[int,int,date,date]:
    today = date.today()
    base = default or date(today.year, today.month, 1)
    cols = st.columns([1,1,1])
    with cols[0]:
        y = st.number_input("Ano", min_value=2000, max_value=today.year+5,
                            value=base.year, key=f"{key_prefix}_y")
    with cols[1]:
        m = st.number_input("Mês", min_value=1, max_value=12,
                            value=base.month, key=f"{key_prefix}_m")
    ini, fim = month_bounds(int(y), int(m))
    with cols[2]:
        st.caption(f"Período: {ini.strftime('%d/%m')}—{fim.strftime('%d/%m')}")
    return int(y), int(m), ini, fim

def _to_date(s):
    try: return pd.to_datetime(s).date() if s else None
    except Exception: return None

# ====== Auth ======
def _user():
    sess = sb.auth.get_session()
    try:
        return sess.user if sess and sess.user else None
    except Exception:
        return None

def _signin(email: str, password: str): sb.auth.sign_in_with_password({"email": email, "password": password})
def _signup(email: str, password: str): sb.auth.sign_up({"email": email, "password": password})
def _signout(): sb.auth.sign_out()

with st.sidebar:
    st.header("🔐 Acesso")
    if "auth_ok" not in st.session_state: st.session_state.auth_ok = False
    if not st.session_state.auth_ok:
        email = st.text_input("Email")
        pwd   = st.text_input("Senha", type="password")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Entrar"):
                try: _signin(email,pwd); st.session_state.auth_ok = True; st.rerun()
                except Exception as e: st.error(str(e))
        with c2:
            if st.button("Criar conta"):
                try: _signup(email,pwd); st.success("Conta criada. Faça login.")
                except Exception as e: st.error(str(e))
    else:
        u = _user()
        if u: st.caption(f"Logado: {u.email}")
        if st.button("Sair"):
            _signout(); st.session_state.auth_ok = False; st.rerun()

if not st.session_state.get("auth_ok"): st.stop()
user = _user(); assert user

# ====== Bootstrap ======
@st.cache_data(show_spinner=False)
def bootstrap(user_id: str):
    try: sb.rpc("accept_pending_invite").execute()
    except Exception: pass
    res = sb.rpc("create_household_and_member", {"display_name":"Você"}).execute().data
    row = res[0] if isinstance(res, list) and res else res
    return row["household_id"], row["member_id"]

if "household_id" not in st.session_state:
    hid, mid = bootstrap(user.id)
    st.session_state["household_id"] = hid
    st.session_state["member_id"] = mid

HID = st.session_state["household_id"]
MID = st.session_state["member_id"]

# ====== Fetches ======
def fetch_members():
    try: return sb.table("members").select("id,display_name,role").eq("household_id", HID).order("display_name").execute().data
    except Exception: return []

def fetch_categories():
    try: return sb.table("categories").select("id,name,kind").eq("household_id", HID).order("name").execute().data
    except Exception: return []

def fetch_accounts(active_only=False):
    q = sb.table("accounts").select("id,name,is_active,type,opening_balance").eq("household_id", HID)
    if active_only: q = q.eq("is_active", True)
    try: return q.order("name").execute().data
    except Exception: return []

def fetch_tx(start: date, end: date):
    try:
        return sb.table("transactions").select(
            "id,household_id,member_id,account_id,type,amount,occurred_at,description,category_id,counterparty,transfer_group,created_by,created_at"
        ).eq("household_id", HID).gte("occurred_at", start.isoformat()).lte("occurred_at", end.isoformat()) \
         .order("occurred_at", desc=False).execute().data
    except Exception: return []

# ====== Insert seguro (somente colunas do seu schema) ======
def insert_tx(payload: dict) -> tuple[bool, str | None]:
    allowed = {"household_id","member_id","account_id","type","amount","occurred_at",
               "description","category_id","counterparty","transfer_group","created_by"}
    data = {k:v for k,v in payload.items() if k in allowed and v is not None}
    try:
        sb.table("transactions").insert(data).execute()
        return True, None
    except Exception as e:
        return False, str(e)

# ====== Sidebar / Navegação ======
with st.sidebar:
    st.header("📍 Navegação")
    section = st.radio("Área", ["🏠 Entrada","💼 Financeiro","🧰 Administração","📊 Dashboards"], index=0)
    st.markdown("---")
    if st.button("🔄 Recarregar dados"): st.cache_data.clear(); st.rerun()

st.title("Finanças da Família — v9.3")

# ===================== ENTRADA =====================
if section == "🏠 Entrada":
    y,m,ini,fim = select_competence("home_comp")
    txm = fetch_tx(ini, fim)

    mems = fetch_members(); mem_map = {m["id"]: m["display_name"] for m in mems}
    cats = fetch_categories(); cats_map = {c["id"]: c for c in cats}

    # Resultado consolidado (ignora categorias 'transfer')
    res = 0.0
    for t in (txm or []):
        kind = cats_map.get(t.get("category_id"),{}).get("kind")
        if kind == "transfer":  # não entra no DRE
            continue
        res += t["amount"] if t["type"]=="income" else -t["amount"]

    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Competência", f"{m:02d}/{y}")
    with c2: st.metric("Lançamentos", len(txm or []))
    with c3: st.metric("Resultado (previsto)", to_brl(res))

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Visão por membro")
    if txm:
        df = pd.DataFrame(txm)
        df["kind"] = df["category_id"].map(lambda cid: cats_map.get(cid,{}).get("kind"))
        df = df[df["kind"]!="transfer"]
        df["signed"] = df.apply(lambda r: r["amount"] if r["type"]=="income" else -r["amount"], axis=1)
        df["Membro"] = df["member_id"].map(mem_map).fillna("—")
        grp = df.groupby("Membro", as_index=False)["signed"].sum()
        st.bar_chart(grp, x="Membro", y="signed")
    else:
        st.info("Sem lançamentos na competência.")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("⚡ Lançar agora"):
        st.session_state.section = "💼 Financeiro"
        st.session_state.fin_tab = "Lançamentos"
        st.rerun()

# ===================== FINANCEIRO =====================
if section == "💼 Financeiro":
    tabs = st.tabs(["Lançamentos","Movimentações","Fixas","Transferência","Orçamento","Fluxo"])
    # -------- Lançamentos --------
    with tabs[0]:
        st.subheader("➕ Lançar receita/despesa")
        cats = [c for c in fetch_categories() if c["kind"] in ("income","expense")]
        accs = fetch_accounts(True)
        cat_by_name = {c["name"]: c for c in cats}
        acc_by_name = {a["name"]: a for a in accs}
        y,m,ini,fim = select_competence("lan_comp")
        with st.form("quick_tx"):
            col1,col2 = st.columns(2)
            with col1:
                tipo = st.selectbox("Tipo", ["expense","income"], index=0,
                                    format_func=lambda x: {"income":"Receita","expense":"Despesa"}[x])
                cat  = st.selectbox("Categoria", list(cat_by_name.keys()) or ["Mercado"])
                desc = st.text_input("Descrição")
                dt   = st.date_input("Data", value=ini)
            with col2:
                val  = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
                acc  = st.selectbox("Conta", list(acc_by_name.keys()) or ["Conta Corrente"])
                contrap = st.text_input("Contraparte (opcional)")
            ok = st.form_submit_button("Lançar")
            if ok:
                try:
                    ok2, err = insert_tx({
                        "household_id": HID, "member_id": MID,
                        "account_id": (acc_by_name.get(acc) or {}).get("id"),
                        "type": tipo, "amount": float(val),
                        "occurred_at": dt.isoformat(),
                        "description": desc,
                        "category_id": (cat_by_name.get(cat) or {}).get("id"),
                        "counterparty": (contrap or None),
                        "created_by": user.id
                    })
                    if not ok2: raise RuntimeError(err or "Falha ao salvar")
                    st.success("✅ Lançamento registrado!"); st.cache_data.clear()
                except Exception as e:
                    st.error(f"Falha: {e}")

    # -------- Movimentações --------
    with tabs[1]:
        st.subheader("📋 Movimentações")
        y,m,ini,fim = select_competence("mov_comp")
        tx = fetch_tx(ini, fim)
        if not tx:
            st.info("Sem lançamentos.")
        else:
            mems = fetch_members(); mem_map = {m["id"]: m["display_name"] for m in mems}
            cats = fetch_categories(); cat_map = {c["id"]: c["name"] for c in cats}
            df = pd.DataFrame(tx)
            df["Data"] = pd.to_datetime(df["occurred_at"]).dt.strftime("%d/%m/%Y")
            df["Tipo"] = df["type"].map({"income":"Receita","expense":"Despesa","transfer":"Transferência"})
            df["Membro"] = df["member_id"].map(mem_map).fillna("—")
            df["Categoria"] = df["category_id"].map(cat_map).fillna("—")
            show = df[["Data","Tipo","Categoria","description","amount","Membro","counterparty","id"]] \
                    .rename(columns={"description":"Descrição","amount":"Valor (R$)"})
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.download_button("⬇️ Baixar CSV", data=show.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"mov_{y}-{m:02d}.csv", mime="text/csv")

    # -------- Fixas (cópia p/ próximos meses) --------
    with tabs[2]:
        st.subheader("♻️ Receitas/Despesas fixas")
        cats = [c for c in fetch_categories() if c["kind"] in ("income","expense")]
        accs = fetch_accounts(True)
        cat_by_name = {c["name"]: c for c in cats}
        acc_by_name = {a["name"]: a for a in accs}
        with st.form("fixas"):
            col1,col2 = st.columns(2)
            with col1:
                tipo = st.selectbox("Tipo", ["expense","income"], index=0,
                                    format_func=lambda x: {"income":"Receita","expense":"Despesa"}[x])
                cat  = st.selectbox("Categoria", list(cat_by_name.keys()) or ["Energia","Aluguel","Salário"])
                desc = st.text_input("Descrição (ex.: [FIXA] Energia)")
                dt   = st.date_input("Data inicial", value=date.today())
            with col2:
                val  = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
                acc  = st.selectbox("Conta", list(acc_by_name.keys()) or ["Conta Corrente"])
                meses = st.number_input("Copiar para próximos (meses)", min_value=0, max_value=24, value=0)
            okf = st.form_submit_button("Criar fixa(s)")
            if okf:
                try:
                    base = {
                        "household_id": HID, "member_id": MID,
                        "account_id": (acc_by_name.get(acc) or {}).get("id"),
                        "type": tipo, "amount": float(val),
                        "description": desc,
                        "category_id": (cat_by_name.get(cat) or {}).get("id"),
                        "created_by": user.id
                    }
                    ok1, e1 = insert_tx({**base, "occurred_at": dt.isoformat()})
                    if not ok1: raise RuntimeError(e1 or "Falha")
                    d = dt
                    for _ in range(int(meses)):
                        d = (d + timedelta(days=32)).replace(day=min(dt.day, 28))
                        ok2, e2 = insert_tx({**base, "occurred_at": d.isoformat()})
                        if not ok2: raise RuntimeError(e2 or "Falha")
                    st.success("✅ Fixas criadas!"); st.cache_data.clear()
                except Exception as e:
                    st.error(f"Falha: {e}")

    # -------- Transferência (dupla partida) --------
    with tabs[3]:
        st.subheader("🔁 Transferência entre contas")
        accs = fetch_accounts(True); acc_by_name = {a["name"]: a for a in accs}
        # categoria de transfer
        cats = fetch_categories(); transfer_cats = [c for c in cats if c["kind"]=="transfer"]
        if not transfer_cats:
            st.warning("Crie uma categoria com tipo **transfer** (ex.: 'Transferência') para usar esta função.")
        else:
            cat_transfer_id = transfer_cats[0]["id"]
            c1,c2,c3,c4 = st.columns(4)
            with c1: origem = st.selectbox("Origem", list(acc_by_name.keys()) or ["—"])
            with c2: destino = st.selectbox("Destino", list(acc_by_name.keys()) or ["—"])
            with c3: valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
            with c4: data_t = st.date_input("Data", value=date.today())
            desc = st.text_input("Descrição", value="[TRANSF] Entre contas")
            if st.button("➡️ Transferir"):
                try:
                    o_id = (acc_by_name.get(origem) or {}).get("id")
                    d_id = (acc_by_name.get(destino) or {}).get("id")
                    if not o_id or not d_id or o_id == d_id:
                        raise RuntimeError("Selecione contas válidas e diferentes.")
                    group = uuid.uuid4().hex
                    # 1) saída origem (expense, kind=transfer)
                    okA, eA = insert_tx({
                        "household_id": HID, "member_id": MID, "account_id": o_id,
                        "type": "expense", "amount": float(valor), "occurred_at": data_t.isoformat(),
                        "description": f"{desc} [{group}]", "category_id": cat_transfer_id,
                        "transfer_group": group, "created_by": user.id
                    })
                    # 2) entrada destino (income, kind=transfer)
                    okB, eB = insert_tx({
                        "household_id": HID, "member_id": MID, "account_id": d_id,
                        "type": "income", "amount": float(valor), "occurred_at": data_t.isoformat(),
                        "description": f"{desc} [{group}]", "category_id": cat_transfer_id,
                        "transfer_group": group, "created_by": user.id
                    })
                    if not (okA and okB): raise RuntimeError(eA or eB or "Falha na transferência")
                    st.success("✅ Transferência registrada!"); st.cache_data.clear()
                except Exception as e:
                    st.error(f"Falha: {e}")

    # -------- Orçamento --------
    with tabs[4]:
        st.subheader("💡 Orçamento da competência")
        cats = [c for c in fetch_categories() if c["kind"] in ("income","expense")]
        cat_by_name = {c["name"]: c for c in cats}
        y,m,ini,fim = select_competence("orc_comp")
        colb1,colb2 = st.columns([2,1])
        with colb1: cat_name = st.selectbox("Categoria", list(cat_by_name.keys()) or ["Mercado"])
        with colb2: val_orc = st.number_input("Orçado (R$)", min_value=0.0, step=50.0)
        if st.button("Salvar orçamento"):
            try:
                cid = (cat_by_name.get(cat_name) or {}).get("id")
                # budgets: household_id, category_id, month, year, amount
                sb.table("budgets").upsert({
                    "household_id": HID, "category_id": cid,
                    "month": int(m), "year": int(y), "amount": float(val_orc),
                    "month_date": date(int(y), int(m), 1).isoformat()
                }, on_conflict="household_id,category_id,month,year").execute()
                st.toast("✅ Salvo!", icon="✅")
            except Exception as e:
                st.error(f"Falha: {e}")

        st.markdown("### Comparativo do mês")
        # tenta RPC; senão calcula local
        try:
            out = sb.rpc("budget_vs_actual", {"p_household": HID, "p_year": int(y), "p_month": int(m)}).execute().data
            dfba = pd.DataFrame(out or [])
            if not dfba.empty:
                dfba["% usado"] = dfba.apply(lambda r: (r["actual"]/r["budget"]*100 if r["budget"] else 0), axis=1)
                dfba.rename(columns={"category_name":"Categoria","kind":"Tipo","budget":"Orçado","actual":"Realizado"}, inplace=True)
                st.dataframe(dfba[["Categoria","Tipo","Orçado","Realizado","% usado"]], use_container_width=True, hide_index=True)
            else:
                st.info("Sem dados.")
        except Exception:
            tx = fetch_tx(ini, fim)
            if not tx: st.info("Sem dados.")
            else:
                cats_map = {c["id"]: (c["name"], c["kind"]) for c in cats}
                df = pd.DataFrame(tx)
                df["kind"] = df["category_id"].map(lambda cid: cats_map.get(cid,("—",None))[1])
                df = df[df["kind"]!="transfer"]
                df["Categoria"] = df["category_id"].map(lambda cid: cats_map.get(cid,("—",None))[0])
                df["Realizado"] = df.apply(lambda r: r["amount"] if r["type"]=="income" else -r["amount"], axis=1)
                real = df.groupby(["category_id","Categoria","kind"], as_index=False)["Realizado"].sum()
                bud = pd.DataFrame(sb.table("budgets").select("*").eq("household_id", HID).eq("year", int(y)).eq("month", int(m)).execute().data)
                if bud.empty:
                    real.rename(columns={"kind":"Tipo"}, inplace=True)
                    real["Orçado"] = 0; real["% usado"] = 0
                    st.dataframe(real[["Categoria","Tipo","Orçado","Realizado","% usado"]], use_container_width=True, hide_index=True)
                else:
                    merged = real.merge(bud[["category_id","amount"]], on="category_id", how="left")
                    merged["Orçado"] = merged["amount"].fillna(0); merged.drop(columns=["amount"], inplace=True)
                    merged["% usado"] = merged.apply(lambda r: (r["Realizado"]/r["Orçado"]*100 if r["Orçado"] else 0), axis=1)
                    merged.rename(columns={"kind":"Tipo"}, inplace=True)
                    st.dataframe(merged[["Categoria","Tipo","Orçado","Realizado","% usado"]], use_container_width=True, hide_index=True)

    # -------- Fluxo (por ocorrência) --------
    with tabs[5]:
        st.subheader("📈 Fluxo de caixa (por data de ocorrência)")
        f1,f2 = st.columns(2)
        with f1: ini = st.date_input("Início", value=date.today().replace(day=1))
        with f2: fim = st.date_input("Fim", value=date.today()+timedelta(days=60))
        txx = fetch_tx(ini, fim)
        if not txx:
            st.info("Sem lançamentos no período.")
        else:
            df = pd.DataFrame(txx)
            df["signed"] = df.apply(lambda r: (r["amount"] if r["type"]=="income" else -r["amount"]), axis=1)
            df["Quando"] = pd.to_datetime(df["occurred_at"]).dt.date
            tot = df.groupby("Quando", as_index=False)["signed"].sum()
            st.line_chart(tot, x="Quando", y="signed")
            c1,c2 = st.columns(2)
            with c1: st.metric("Receitas", to_brl(df[df["type"]=="income"]["amount"].sum()))
            with c2: st.metric("Despesas", to_brl(df[df["type"]=="expense"]["amount"].sum()))

# ===================== ADMINISTRAÇÃO =====================
if section == "🧰 Administração":
    tabs = st.tabs(["Membros","Contas","Categorias"])
    # Membros
    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Membros")
        mems = fetch_members()
        if mems:
            chips = " ".join([f'<span class="badge">👤 {m["display_name"]}{" · owner" if m["role"]=="owner" else ""}</span>' for m in mems])
            st.markdown(chips, unsafe_allow_html=True)
        st.markdown("### Convidar por e-mail")
        inv_email = st.text_input("E-mail do convidado")
        inv_role = st.selectbox("Papel", ["viewer","member"], index=1)
        if st.button("Enviar convite"):
            try:
                try:
                    sb.rpc("invite_member", {"p_household": HID, "p_email": inv_email, "p_role": inv_role}).execute()
                except Exception:
                    # fallback se RPC não existir
                    sb.table("invites").insert({"household_id": HID, "email": inv_email, "role": inv_role, "created_by": user.id}).execute()
                st.success("Convite enviado/registrado.")
            except Exception as e:
                st.error(f"Falha no convite: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Contas
    with tabs[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Contas")
        accs_all = fetch_accounts(False) or []
        if st.checkbox("Editar conta existente", key="acc_edit") and accs_all:
            acc_names = [a["name"] for a in accs_all]
            sel = st.selectbox("Conta", acc_names)
            sel_acc = next((a for a in accs_all if a["name"]==sel), None) or {}
            new_name = st.text_input("Nome", value=sel_acc.get("name",""))
            tipo_pt = PT_TYPES.get(sel_acc.get("type","checking"), "Conta corrente")
            new_type_pt = st.selectbox("Tipo", list(PT_TYPES.values()), index=list(PT_TYPES.values()).index(tipo_pt))
            new_active = st.checkbox("Ativa?", value=bool(sel_acc.get("is_active", True)))
            if st.button("💾 Salvar alterações"):
                try:
                    sb.table("accounts").update({
                        "name": new_name.strip(),
                        "type": EN_TYPES[new_type_pt],
                        "is_active": new_active
                    }).eq("id", sel_acc["id"]).execute()
                    st.toast("✅ Alterada!", icon="✅"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Falha: {e}")
            if st.button("🗑️ Excluir conta"):
                try:
                    sb.table("accounts").delete().eq("id", sel_acc["id"]).execute()
                    st.toast("✅ Excluída!", icon="✅"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Falha ao excluir: {e}")
        else:
            name = st.text_input("Nome")
            tipo_pt = st.selectbox("Tipo", list(PT_TYPES.values()))
            opening = st.number_input("Saldo inicial", min_value=0.0, step=50.0)
            if st.button("Salvar conta"):
                try:
                    sb.table("accounts").insert({
                        "household_id": HID, "name": name.strip(),
                        "type": {v:k for k,v in PT_TYPES.items()}[tipo_pt],
                        "opening_balance": float(opening), "currency": "BRL", "is_active": True
                    }).execute()
                    st.toast("✅ Conta salva!", icon="✅"); st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(str(e))

        st.markdown("### Transferir entre contas")
        accs_active = fetch_accounts(True) or []
        acc_by_name = {a["name"]: a for a in accs_active}
        cta = st.columns(3)
        with cta[0]: origem = st.selectbox("Origem", list(acc_by_name.keys()) or ["—"])
        with cta[1]: destino = st.selectbox("Destino", list(acc_by_name.keys()) or ["—"])
        with cta[2]: valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
        desc_t = st.text_input("Descrição", value="[TRANSF] Transferência entre contas")
        data_t = st.date_input("Data", value=date.today())
        # pega categoria transfer
        cats = fetch_categories(); transfer_cats = [c for c in cats if c["kind"]=="transfer"]
        if not transfer_cats:
            st.info("Crie uma categoria com tipo **transfer** para transferências.")
        else:
            cat_transfer_id = transfer_cats[0]["id"]
            if st.button("➡️ Transferir"):
                try:
                    a_or = acc_by_name.get(origem,{}).get("id")
                    a_de = acc_by_name.get(destino,{}).get("id")
                    if not a_or or not a_de or a_or==a_de:
                        raise RuntimeError("Selecione contas válidas e diferentes.")
                    group = uuid.uuid4().hex
                    okA, eA = insert_tx({
                        "household_id": HID,"member_id": MID,
                        "account_id": a_or, "category_id": cat_transfer_id, "type":"expense",
                        "amount": float(valor), "occurred_at": data_t.isoformat(),
                        "description": f"{desc_t} [{group}]","transfer_group": group, "created_by": user.id
                    })
                    okB, eB = insert_tx({
                        "household_id": HID,"member_id": MID,
                        "account_id": a_de, "category_id": cat_transfer_id, "type":"income",
                        "amount": float(valor), "occurred_at": data_t.isoformat(),
                        "description": f"{desc_t} [{group}]","transfer_group": group, "created_by": user.id
                    })
                    if not (okA and okB): raise RuntimeError(eA or eB or "Falha na transferência")
                    st.success("Transferência registrada."); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Falha: {e}")

        # Lista
        accs = fetch_accounts(False)
        if accs:
            df = pd.DataFrame(accs)
            df["Tipo"] = df["type"].map(PT_TYPES).fillna(df["type"])
            df["Ativa?"] = df["is_active"].map({True:"Sim", False:"Não"})
            st.dataframe(df[["name","Tipo","opening_balance","Ativa?"]].rename(columns={"name":"Conta","opening_balance":"Saldo inicial"}),
                         use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Categorias
    with tabs[2]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Categorias")
        cn = st.text_input("Nome da categoria")
        ck = st.selectbox("Tipo", ["income","expense","transfer"],
                          format_func=lambda k: {"income":"Receita","expense":"Despesa","transfer":"Transferência"}[k])
        if st.button("Salvar categoria"):
            try:
                sb.table("categories").insert({"household_id": HID,"name": cn.strip(),"kind": ck}).execute()
                st.toast("✅ Categoria salva!", icon="✅"); st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(str(e))
        cats = fetch_categories()
        if cats:
            chips_inc = " ".join([f'<span class="badge green">#{c["name"]}</span>' for c in cats if c["kind"]=="income"])
            chips_exp = " ".join([f'<span class="badge red">#{c["name"]}</span>' for c in cats if c["kind"]=="expense"])
            chips_trn = " ".join([f'<span class="badge">🔁 {c["name"]}</span>' for c in cats if c["kind"]=="transfer"])
            st.markdown("**Receitas**"); st.markdown(chips_inc or "_(vazio)_", unsafe_allow_html=True)
            st.markdown("**Despesas**"); st.markdown(chips_exp or "_(vazio)_", unsafe_allow_html=True)
            st.markdown("**Transferências**"); st.markdown(chips_trn or "_(vazio)_", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ===================== DASHBOARDS =====================
if section == "📊 Dashboards":
    tabs = st.tabs(["Relatórios","Visão rápida"])
    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Relatórios por competência")
        y,m,ini,fim = select_competence("dash_comp")
        tx = fetch_tx(ini, fim)
        mems = fetch_members(); cats = fetch_categories()
        if not tx: st.info("Sem lançamentos.")
        else:
            df = pd.DataFrame(tx)
            mem_map = {m["id"]: m["display_name"] for m in (mems or [])}
            cat_map = {c["id"]: (c["name"], c["kind"]) for c in (cats or [])}
            df["Categoria"] = df["category_id"].map(lambda cid: cat_map.get(cid,("—",None))[0]).fillna("—")
            df["kind"] = df["category_id"].map(lambda cid: cat_map.get(cid,("—",None))[1])
            df = df[df["kind"]!="transfer"]
            df["valor_eff"] = df.apply(lambda r: r["amount"] if r["type"]=="income" else -r["amount"], axis=1)
            df["Membro"] = df["member_id"].map(mem_map).fillna("—")
            st.markdown("#### Por membro")
            st.bar_chart(df.groupby("Membro", as_index=False)["valor_eff"].sum(), x="Membro", y="valor_eff")
            st.markdown("#### Por categoria")
            st.bar_chart(df.groupby("Categoria", as_index=False)["valor_eff"].sum(), x="Categoria", y="valor_eff")
        st.markdown('</div>', unsafe_allow_html=True)
    with tabs[1]:
        st.info("Dica: crie uma view `v_account_balance` somando opening_balance + (entradas - saídas) por conta para saldos instantâneos.")
