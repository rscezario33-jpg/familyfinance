# app.py — Family Finance v8.2.0
# (sidebar topo/rodapé; contraste; categorias em AgGrid com ícone/editar/excluir;
#  membros em AgGrid com editar/excluir/convite; árvore familiar; anexos; lembretes por e-mail)
from __future__ import annotations
from datetime import date, datetime, timedelta
import uuid
import io
import os
import smtplib
from email.message import EmailMessage
from typing import List, Optional, Dict

import pandas as pd
import streamlit as st
from supabase_client import get_supabase

# AgGrid (grid profissional)
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
except Exception:
    AgGrid = None  # se faltar a dependência, o app segue sem travar

st.set_page_config(page_title="Family Finance", layout="wide", initial_sidebar_state="expanded")

# =========================
# CSS (visual + contraste + layout topo/rodapé)
# =========================
st.markdown("""
<style>
/* Sidebar base */
section[data-testid="stSidebar"] > div {
  background: #0b2038 !important;
  color: #f0f6ff !important;
  padding-top: 0;
  height: 100%;
}
/* Container flex para topo/miolo/rodapé */
div.sidebar-flex {
  display: flex; flex-direction: column; height: 100%;
}
div.sidebar-top, div.sidebar-bottom { display:flex; flex-direction:column; align-items:center; }
div.sidebar-top { padding: 12px 12px 8px 12px; }
div.sidebar-bottom { padding: 8px 12px 14px 12px; }

/* Contraste textos na sidebar */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > div,
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {
  color:#f0f6ff !important;
}

/* Títulos e divisores */
.sidebar-title {
  color:#e6f0ff; font-weight:700; letter-spacing:.6px; text-transform:uppercase;
  font-size:.80rem; margin: 6px 0 6px 6px;
}
.sidebar-group { border-top:1px solid rgba(255,255,255,.08); margin:10px 0 8px 0; padding-top:8px; }

/* Botões/inputs */
.stButton>button, .stDownloadButton>button {
  border-radius:10px; padding:.55rem .9rem; font-weight:600; border:1px solid #0ea5e9; background:#0ea5e9; color:white;
}
.stButton>button:hover { transform: translateY(-1px); background:#0284c7; border-color:#0284c7; }
.stSelectbox div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input, .stDateInput input {
  border-radius:10px !important;
}

/* Cards e badges */
.card { background: linear-gradient(180deg,#fff 0%,#f8fafc 100%);
  border:1px solid #e2e8f0; border-radius:16px; padding:16px 18px;
  box-shadow:0 6px 20px rgba(0,0,0,.06); margin-bottom:12px; }
.badge { display:inline-flex; align-items:center; gap:.5rem; background:#eef6ff; color:#0369a1;
  border:1px solid #bfdbfe; padding:.35rem .6rem; border-radius:999px; font-weight:600; margin:4px 6px 0 0; }
.badge.red{background:#fff1f2;color:#9f1239;border-color:#fecdd3;}
.badge.green{background:#ecfdf5;color:#065f46;border-color:#bbf7d0;}
.small { font-size:.85rem; opacity:.75; }

/* Centralização das logos */
.sidebar-logo-top img, .sidebar-logo-bottom img { display:block; margin:0 auto; }
</style>
""", unsafe_allow_html=True)

# =========================
# Conexão Supabase
# =========================
sb = get_supabase()

# =========================
# Helpers utilitários
# =========================
def to_brl(v: float) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def _to_date_safe(s):
    if not s: return None
    try:
        return datetime.fromisoformat(str(s)).date()
    except Exception:
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try: return datetime.strptime(str(s)[:len(fmt)], fmt).date()
            except Exception: pass
    return None

def _safe_table(name: str):
    try:
        return sb.table(name).select("*").eq("household_id", HOUSEHOLD_ID).execute().data or []
    except Exception:
        return []

# =========================
# Auth wrappers
# =========================
def _signin(email, password):
    sb.auth.sign_in_with_password({"email": email, "password": password})

def _signup(email, password):
    try:
        sb.auth.sign_up({"email": email, "password": password})
    except OSError as e:
        if getattr(e, "errno", None) == -2:
            raise RuntimeError("Falha de rede/DNS ao contatar o Supabase.")
        raise

def _signout(): sb.auth.sign_out()

def _user():
    sess = sb.auth.get_session()
    return sess.user if sess and sess.user else None

# =========================
# Sidebar (logo topo, menu, logo rodapé)
# =========================
with st.sidebar:
    # Estrutura flex vertical
    st.markdown('<div class="sidebar-flex">', unsafe_allow_html=True)

    # Topo (logo FF centralizada)
    st.markdown('<div class="sidebar-top sidebar-logo-top">', unsafe_allow_html=True)
    st.image("assets/logo_family_finance.png", width=110)
    st.markdown('</div>', unsafe_allow_html=True)

    # Miolo (acesso + menu)
    st.markdown('<div class="sidebar-mid">', unsafe_allow_html=True)

    if "auth_ok" not in st.session_state: st.session_state.auth_ok = False
    if not st.session_state.auth_ok:
        st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">Acesso</div>', unsafe_allow_html=True)
        email = st.text_input("Email").strip()
        pwd   = st.text_input("Senha", type="password")

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
        st.markdown('</div>', unsafe_allow_html=True)   # fecha mid
        st.markdown('<div class="sidebar-bottom">', unsafe_allow_html=True)
        st.markdown('<div class="small" style="text-align:center;opacity:.9;">Powered by</div>', unsafe_allow_html=True)
        st.image("assets/logo_automaGO.png", width=80)
        st.markdown('</div></div>', unsafe_allow_html=True)  # fecha bottom e flex
        st.stop()
    else:
        u = _user()
        st.caption(f"Logado: {u.email if u else ''}")

    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">Menu</div>', unsafe_allow_html=True)

    section = st.radio(
        "", ["🏠 Entrada","💼 Financeiro","🧰 Administração","📊 Dashboards"],
        label_visibility="collapsed",
        index=0
    )

    st.markdown('<div class="sidebar-group"></div>', unsafe_allow_html=True)
    if st.button("Sair"):
        _signout(); st.session_state.auth_ok = False; st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)  # fecha mid

    # Rodapé (AutomaGO centralizada)
    st.markdown('<div class="sidebar-bottom sidebar-logo-bottom">', unsafe_allow_html=True)
    st.markdown('<div class="small" style="text-align:center;opacity:.9;">Powered by</div>', unsafe_allow_html=True)
    st.image("assets/logo_automaGO.png", width=80)
    st.markdown('</div></div>', unsafe_allow_html=True)  # fecha bottom e flex

user = _user(); assert user  # precisa estar logado daqui pra frente

# =========================
# Bootstrap household/member
# =========================
@st.cache_data(show_spinner=False)
def bootstrap(user_id: str):
    try: sb.rpc("accept_pending_invite").execute()
    except Exception: pass
    res = sb.rpc("create_household_and_member", {"display_name": "Você"}).execute().data
    return {"household_id": res[0]["household_id"], "member_id": res[0]["member_id"]}

ids = bootstrap(user.id)
HOUSEHOLD_ID = ids["household_id"]; MY_MEMBER_ID = ids["member_id"]

# =========================
# Data fetchers
# =========================
def fetch_members():
    try:
        return sb.table("members").select("id,display_name,role,user_id,parent_id") \
            .eq("household_id", HOUSEHOLD_ID).order("display_name").execute().data
    except Exception:
        return []

def fetch_categories():
    # tenta incluir coluna icon; se não existir, ignora
    try:
        return sb.table("categories").select("id,name,kind,icon") \
            .eq("household_id", HOUSEHOLD_ID).order("name").execute().data
    except Exception:
        try:
            return sb.table("categories").select("id,name,kind") \
                .eq("household_id", HOUSEHOLD_ID).order("name").execute().data
        except Exception:
            return []

def fetch_accounts(active_only=False):
    q = sb.table("accounts").select("id,name,is_active,type").eq("household_id", HOUSEHOLD_ID)
    if active_only: q = q.eq("is_active", True)
    try:
        data = q.execute().data or []
    except Exception:
        data = _safe_table("accounts")
    data.sort(key=lambda a:(a.get("name") or "").lower())
    return data

def fetch_cards(active_only=True):
    q = sb.table("credit_cards").select("id,household_id,name,limit_amount,closing_day,due_day,is_active,created_by") \
        .eq("household_id", HOUSEHOLD_ID)
    if active_only: q = q.eq("is_active", True)
    try:
        data = q.execute().data or []
    except Exception:
        data = _safe_table("credit_cards")
    data.sort(key=lambda c:(c.get("name") or "").lower())
    return data

def fetch_card_limits():
    try:
        data = sb.table("v_card_limit").select("*").eq("household_id", HOUSEHOLD_ID).execute().data or []
    except Exception:
        data = []
    data.sort(key=lambda c:(c.get("name") or "").lower())
    return data

def fetch_tx(start: date, end: date):
    rows = _safe_table("transactions")
    out=[]
    for t in rows:
        d = _to_date_safe(t.get("occurred_at"))
        if d and start <= d <= end:
            out.append(t)
    out.sort(key=lambda t: (_to_date_safe(t.get("due_date")) or _to_date_safe(t.get("occurred_at")) or date.min))
    return out

def fetch_tx_due(start: date, end: date):
    rows = _safe_table("transactions")
    out=[]
    for t in rows:
        dd = _to_date_safe(t.get("due_date"))
        od = _to_date_safe(t.get("occurred_at"))
        key = dd or od
        if key and start <= key <= end:
            out.append(t)
    out.sort(key=lambda t: (_to_date_safe(t.get("due_date")) or _to_date_safe(t.get("occurred_at")) or date.min))
    return out

# =========================
# SMTP (opcional) — envio de lembretes
# =========================
def _smtp_cfg():
    cfg = getattr(st.secrets, "smtp", None) if hasattr(st, "secrets") else None
    if not cfg: return None
    return {
        "host": cfg.get("host"),
        "port": int(cfg.get("port", 587)),
        "user": cfg.get("user"),
        "password": cfg.get("password"),
        "from_email": cfg.get("from_email", cfg.get("user")),
        "use_tls": bool(cfg.get("use_tls", True)),
    }

def send_email(to_emails: List[str], subject: str, body: str, attach_name: Optional[str]=None, attach_bytes: Optional[bytes]=None):
    smtp = _smtp_cfg()
    if not smtp:
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp["from_email"]
        msg["To"] = ", ".join(to_emails)
        msg.set_content(body)

        if attach_bytes and attach_name:
            msg.add_attachment(attach_bytes, maintype="application", subtype="octet-stream", filename=attach_name)

        with smtplib.SMTP(smtp["host"], smtp["port"]) as s:
            if smtp["use_tls"]:
                s.starttls()
            if smtp["user"]:
                s.login(smtp["user"], smtp["password"])
            s.send_message(msg)
        return True
    except Exception:
        return False

@st.cache_data(show_spinner=False)
def _today_str():
    return date.today().isoformat()

def notify_due_bills():
    key = f"__notified__{_today_str()}"
    if st.session_state.get(key): 
        return
    try:
        start = date.today()
        end = date.today() + timedelta(days=3)
        txs = fetch_tx_due(start, end)
        if not txs: 
            st.session_state[key] = True
            return
        pend = [t for t in txs if (t.get("type")=="expense" and not t.get("is_paid"))]
        if not pend:
            st.session_state[key] = True
            return
        to = [user.email] if user and user.email else []
        if not to:
            st.session_state[key] = True
            return
        lines=[]
        for t in pend:
            due = _to_date_safe(t.get("due_date")) or _to_date_safe(t.get("occurred_at"))
            val = t.get("planned_amount") or t.get("amount") or 0.0
            lines.append(f"- {t.get('description','(sem descrição)')} — vence em {due.strftime('%d/%m/%Y')} — {to_brl(val)}")
        if lines:
            subject = "Lembrete: contas a vencer (3 dias / hoje)"
            body = "Olá!\n\nAs seguintes contas vencem em até 3 dias (ou hoje):\n\n" + "\n".join(lines) + "\n\n— Family Finance"
            send_email(to, subject, body)
    finally:
        st.session_state[key] = True

# dispara lembretes
notify_due_bills()

# =========================
# UI
# =========================
st.title("Family Finance")

# =========================
# ENTRADA
# =========================
if section == "🏠 Entrada":
    first_day = date.today().replace(day=1)
    txm = fetch_tx(first_day, date.today())
    res = sum([(t.get("paid_amount") if t.get("is_paid") else t.get("planned_amount") or t.get("amount") or 0)
               * (1 if t.get("type")=="income" else -1) for t in txm]) if txm else 0
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Período", f"{first_day.strftime('%d/%m')}—{date.today().strftime('%d/%m')}")
    with c2: st.metric("Lançamentos", len(txm))
    with c3: st.metric("Resultado (previsto)", to_brl(res))

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Visão por membro (mês)")
    mems = fetch_members(); mem_map = {m["id"]: m["display_name"] for m in mems}
    if txm:
        df = pd.DataFrame(txm)
        df["valor_eff"] = df.apply(lambda r: (r.get("paid_amount") if r.get("is_paid") else r.get("planned_amount") or r.get("amount") or 0)
                                             * (1 if r.get("type")=="income" else -1), axis=1)
        df["Membro"] = df["member_id"].map(mem_map).fillna("—")
        st.bar_chart(df.groupby("Membro")["valor_eff"].sum().reset_index(), x="Membro", y="valor_eff")
    else:
        st.info("Sem lançamentos no mês.")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# FINANCEIRO
# =========================
if section == "💼 Financeiro":
    tabs = st.tabs(["Lançamentos","Movimentações","Receitas/Despesas fixas","Orçamentos","Fluxo de caixa"])

    # Lançamentos
    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("➕ Lançar")
        cats = fetch_categories(); cat_map = {c["name"]: c for c in cats}
        accs = fetch_accounts(True); acc_map = {a["name"]: a for a in accs}
        cards = fetch_cards(True); card_map = {c["name"]: c for c in cards}

        with st.form("quick_tx"):
            col1,col2 = st.columns(2)
            with col1:
                tipo = st.selectbox("Tipo", ["income","expense"], index=1, format_func=lambda x: {"income":"Receita","expense":"Despesa"}[x])
                cat  = st.selectbox("Categoria", list(cat_map.keys()) or ["Mercado"])
                desc = st.text_input("Descrição")
                data = st.date_input("Data", value=date.today())
                due  = st.date_input("Vencimento", value=date.today())
            with col2:
                val  = st.number_input("Valor", min_value=0.0, step=10.0)
                method = st.selectbox("Forma de pagamento", ["account","card"], index=0, format_func=lambda x: "Conta" if x=="account" else "Cartão")
                acc = st.selectbox("Conta", list(acc_map.keys()) or ["Conta Corrente"])
                card_name = st.selectbox("Cartão (se aplicável)", ["—"] + list(card_map.keys()))
                parcelado = st.checkbox("Parcelado? (somente despesa)")
                n_parc = st.number_input("Nº parcelas", min_value=2, max_value=36, value=2, disabled=not (parcelado and tipo=="expense"))
            boleto = st.file_uploader("Anexar boleto (PDF/JPG/PNG) — opcional", type=["pdf","jpg","jpeg","png"])
            ok = st.form_submit_button("Lançar")

            if ok:
                try:
                    cat_id = (cat_map.get(cat) or {}).get("id")
                    acc_id = (acc_map.get(acc) or {}).get("id")
                    card_id = (card_map.get(card_name) or {}).get("id") if method=="card" and card_name!="—" else None
                    attachment_url = None

                    if boleto is not None:
                        ext = os.path.splitext(boleto.name)[1].lower()
                        key = f"{HOUSEHOLD_ID}/{uuid.uuid4().hex}{ext}"
                        data_bytes = boleto.read()
                        sb.storage.from_("boletos").upload(key, data_bytes)
                        attachment_url = sb.storage.from_("boletos").get_public_url(key)

                    if tipo=="expense" and parcelado:
                        sb.rpc("create_installments", {
                            "p_household": HOUSEHOLD_ID,
                            "p_member": MY_MEMBER_ID,
                            "p_account": acc_id,
                            "p_category": cat_id,
                            "p_desc": desc,
                            "p_total": val,
                            "p_n": int(n_parc),
                            "p_first_due": due.isoformat(),
                            "p_payment_method": method,
                            "p_card_id": card_id
                        }).execute()
                    else:
                        planned = val
                        sb.table("transactions").insert({
                            "household_id": HOUSEHOLD_ID, "member_id": MY_MEMBER_ID,
                            "account_id": acc_id, "category_id": cat_id,
                            "type": tipo,
                            "amount": val,
                            "planned_amount": planned,
                            "occurred_at": data.isoformat(),
                            "due_date": due.isoformat(),
                            "description": desc,
                            "payment_method": method,
                            "card_id": card_id,
                            "attachment_url": attachment_url,
                            "created_by": user.id
                        }).execute()
                    st.toast("✅ Lançamento registrado!", icon="✅"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Falha: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Movimentações (pagamento + anexo)
    with tabs[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📋 Movimentações")
        ini = st.date_input("Início", value=date.today().replace(day=1), key="mv_ini")
        fim = st.date_input("Fim", value=date.today(), key="mv_fim")
        tx = fetch_tx(ini, fim)
        if not tx: 
            st.info("Sem lançamentos.")
        else:
            df = pd.DataFrame(tx)
            df["Data"] = pd.to_datetime(df.get("occurred_at"), errors="coerce").dt.strftime("%d/%m/%Y")
            df["Venc"] = pd.to_datetime(df.get("due_date"), errors="coerce").dt.strftime("%d/%m/%Y")
            df["Tipo"] = df.get("type").map({"income":"Receita","expense":"Despesa"})
            df["Previsto (R$)"] = (df.get("planned_amount").fillna(df.get("amount")).fillna(0.0)).astype(float)
            df["Pago?"] = df.get("is_paid").fillna(False)
            df["Pago (R$)"] = df.get("paid_amount").fillna("")
            st.dataframe(
                df[["Data","Venc","Tipo","description","Previsto (R$)","Pago?","Pago (R$)","attachment_url","id"]]
                .rename(columns={"description":"Descrição","attachment_url":"Boleto"}),
                use_container_width=True, hide_index=True
            )

            st.markdown("### Marcar pagamento / Anexar boleto")
            tx_id  = st.selectbox("Transação", df["id"])
            pago_v = st.number_input("Valor pago (R$) — deixe 0 para usar o previsto", min_value=0.0, step=10.0)
            pago_d = st.date_input("Data pagamento", value=date.today())
            novo_boleto = st.file_uploader("Anexar/atualizar boleto", type=["pdf","jpg","jpeg","png"], key="mv_bol")

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Confirmar pagamento"):
                    try:
                        row = df[df["id"]==tx_id].iloc[0]
                        previsto = float(row["Previsto (R$)"]) if row is not None else 0.0
                        valor_final = pago_v if pago_v > 0 else previsto
                        sb.rpc("mark_transaction_paid", {"p_tx_id": tx_id, "p_amount": valor_final, "p_date": pago_d.isoformat()}).execute()
                        st.toast("Pagamento registrado!", icon="✅"); st.cache_data.clear(); st.rerun()
                    except Exception as e:
                        st.error(f"Falha ao marcar pago: {e}")
            with col_b:
                if st.button("📎 Salvar anexo"):
                    try:
                        if novo_boleto is None:
                            st.warning("Selecione um arquivo para anexar.")
                        else:
                            ext = os.path.splitext(novo_boleto.name)[1].lower()
                            key = f"{HOUSEHOLD_ID}/{tx_id}{ext}"
                            data_bytes = novo_boleto.read()
                            sb.storage.from_("boletos").upload(key, data_bytes, {"upsert": True})
                            url = sb.storage.from_("boletos").get_public_url(key)
                            sb.table("transactions").update({"attachment_url": url}).eq("id", tx_id).execute()
                            st.toast("Anexo salvo!", icon="📎"); st.cache_data.clear(); st.rerun()
                    except Exception as e:
                        st.error(f"Falha ao anexar: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Fixas (cria lançamentos previstos; pagamento em Movimentações)
    with tabs[2]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("♻️ Receitas/Despesas fixas")
        cats = fetch_categories(); cat_map = {c["name"]: c for c in cats}
        accs = fetch_accounts(True); acc_map = {a["name"]: a for a in accs}
        cards = fetch_cards(True); card_map = {c["name"]: c for c in cards}

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

                    sb.table("transactions").insert({
                        "household_id": HOUSEHOLD_ID, "member_id": MY_MEMBER_ID,
                        "account_id": acc_id, "category_id": cat_id,
                        "type": tipo,
                        "amount": previsto,
                        "planned_amount": previsto,
                        "occurred_at": start_due.isoformat(),
                        "due_date": start_due.isoformat(),
                        "description": desc,
                        "payment_method": method,
                        "card_id": card_id,
                        "created_by": user.id
                    }).execute()

                    d = start_due
                    for _ in range(int(meses)):
                        first_next = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
                        try:
                            d = first_next.replace(day=start_due.day)
                        except ValueError:
                            last = (first_next + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                            d = last
                        sb.table("transactions").insert({
                            "household_id": HOUSEHOLD_ID, "member_id": MY_MEMBER_ID,
                            "account_id": acc_id, "category_id": cat_id,
                            "type": tipo,
                            "amount": previsto,
                            "planned_amount": previsto,
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
        st.caption("💡 O pagamento/valor pago é marcado na aba **Movimentações**. Se não informar o valor, o resultado usa o **previsto**; a **data de pagamento** padrão é o dia marcado.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Orçamentos
    with tabs[3]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("💡 Orçamentos")
        month_str = st.text_input("Mês (YYYY-MM)", value=date.today().strftime("%Y-%m"))
        cats = fetch_categories(); cat_by_name = {c["name"]: c for c in cats}
        colb1,colb2 = st.columns([2,1])
        with colb1: cat_name = st.selectbox("Categoria", list(cat_by_name.keys()) or ["Mercado"])
        with colb2: val_orc = st.number_input("Orçado (R$)", min_value=0.0, step=50.0)
        if st.button("Salvar orçamento"):
            try:
                cid = (cat_by_name.get(cat_name) or {}).get("id")
                sb.rpc("upsert_budget", {"p_household": HOUSEHOLD_ID, "p_month": month_str, "p_category": cid, "p_amount": val_orc}).execute()
                st.toast("✅ Salvo!", icon="✅")
            except Exception as e:
                st.error(f"Falha: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Fluxo previsto
    with tabs[4]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📈 Fluxo de caixa (previsto)")
        f1,f2 = st.columns(2)
        with f1: ini = st.date_input("Início", value=date.today().replace(day=1), key="fx_ini")
        with f2: fim = st.date_input("Fim", value=date.today()+timedelta(days=60), key="fx_fim")
        txx = fetch_tx_due(ini, fim)
        if not txx: st.info("Sem previstos no período.")
        else:
            df = pd.DataFrame(txx)
            def eff(r):
                v = r.get("paid_amount") if r.get("is_paid") else (r.get("planned_amount") or r.get("amount") or 0)
                return v if r.get("type")=="income" else -v
            df["Quando"] = pd.to_datetime(df.get("due_date").fillna(df.get("occurred_at")), errors="coerce").dt.date
            df["Saldo"] = df.apply(eff, axis=1)
            st.line_chart(df.groupby("Quando")["Saldo"].sum().reset_index(), x="Quando", y="Saldo")
        st.markdown('</div>', unsafe_allow_html=True)

# =========================
# ADMINISTRAÇÃO (Membros, Contas, Categorias, Cartões)
# =========================
if section == "🧰 Administração":
    tabs = st.tabs(["Membros","Contas","Categorias","Cartões"])

    # ---------- Membros (AgGrid + excluir + convite + árvore) ----------
    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Membros da família")

        # Form de cadastro/edição simples
        colm1, colm2, colm3 = st.columns([2,1,1])
        nm = colm1.text_input("Nome de exibição", value="")
        role = colm2.selectbox("Papel", ["owner","member","viewer"], index=1)
        parent_id_input = colm3.text_input("Parent ID (opcional)")
        if st.button("Salvar membro"):
            try:
                sb.table("members").upsert({
                    "household_id": HOUSEHOLD_ID,
                    "user_id": None,  # pode ser preenchido ao aceitar convite
                    "display_name": nm.strip(),
                    "role": role,
                    "parent_id": parent_id_input.strip() or None
                }).execute()
                st.toast("✅ Membro salvo!", icon="✅"); st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(str(e))

        mems = fetch_members()
        if not mems:
            st.info("Sem membros cadastrados ainda.")
        else:
            dfm = pd.DataFrame(mems)
            dfm = dfm.rename(columns={
                "display_name":"Nome",
                "role":"Papel",
                "user_id":"Usuário",
                "parent_id":"Pai"
            })

            # Grid AgGrid (se disponível)
            if AgGrid is not None:
                gob = GridOptionsBuilder.from_dataframe(dfm[["id","Nome","Papel","Usuário","Pai"]])
                gob.configure_selection("single")
                gob.configure_grid_options(editType="fullRow")
                gob.configure_columns({
                    "id": {"editable": False},
                    "Nome": {"editable": True},
                    "Papel": {"editable": True, "cellEditor": "agSelectCellEditor", "cellEditorParams": {"values": ["owner","member","viewer"]}},
                    "Usuário": {"editable": False},
                    "Pai": {"editable": True},
                })
                grid = AgGrid(
                    dfm[["id","Nome","Papel","Usuário","Pai"]],
                    gridOptions=gob.build(),
                    update_mode=GridUpdateMode.MODEL_CHANGED,
                    height=320,
                    fit_columns_on_grid_load=True,
                    key="grid_membros"
                )
                edited_rows = grid["data"]
                # Botões de ação
                cmm1, cmm2, cmm3 = st.columns([1,1,2])
                with cmm1:
                    if st.button("💾 Salvar edições"):
                        try:
                            for _, row in edited_rows.iterrows():
                                sb.table("members").update({
                                    "display_name": row["Nome"],
                                    "role": row["Papel"],
                                    "parent_id": row["Pai"] if row["Pai"] else None
                                }).eq("id", row["id"]).execute()
                            st.toast("Edições salvas!", icon="✅"); st.cache_data.clear(); st.rerun()
                        except Exception as e:
                            st.error(f"Falha ao salvar: {e}")
                with cmm2:
                    sel = grid["selected_rows"]
                    if st.button("🗑️ Excluir selecionado"):
                        try:
                            if not sel:
                                st.warning("Selecione um membro no grid.")
                            else:
                                sel_id = sel[0]["id"]
                                sb.table("members").delete().eq("id", sel_id).execute()
                                st.toast("Membro excluído!", icon="🗑️"); st.cache_data.clear(); st.rerun()
                        except Exception as e:
                            st.error(f"Falha ao excluir: {e}")
                with cmm3:
                    invite_email = st.text_input("Enviar convite por e-mail (usuário receberá link do app)")
                    if st.button("✉️ Enviar convite"):
                        try:
                            # MVP: grava um registro (se existir tabela) e envia e-mail (se SMTP configurado)
                            try:
                                sb.table("pending_invites").insert({
                                    "household_id": HOUSEHOLD_ID,
                                    "email": invite_email,
                                    "invited_by": user.id
                                }).execute()
                            except Exception:
                                pass
                            app_url = st.secrets.get("app", {}).get("url", "https://familyfinance.streamlit.app") if hasattr(st, "secrets") else "https://familyfinance.streamlit.app"
                            ok = send_email(
                                [invite_email],
                                "Convite — Family Finance",
                                f"Você foi convidado(a) para o Family Finance.\nAcesse: {app_url}\n\nApós entrar, você será associado(a) ao lar."
                            )
                            st.toast("Convite registrado!" + (" ✉️ E-mail enviado." if ok else " (sem SMTP configurado)"), icon="✉️")
                        except Exception as e:
                            st.error(f"Falha ao convidar: {e}")
            else:
                st.warning("Para edição avançada, instale `st-aggrid` no requirements. Exibindo tabela simples.")
                st.dataframe(dfm, use_container_width=True, hide_index=True)

        # Árvore genealógica (Graphviz)
        st.markdown("### 👪 Árvore familiar")
        try:
            import graphviz
            mems2 = fetch_members()
            if mems2:
                g = graphviz.Digraph(format="svg")
                g.attr("node", shape="box", style="rounded,filled", color="#0b2038", fillcolor="#eef6ff")
                id_to_name = {m["id"]: m["display_name"] for m in mems2}
                for m in mems2:
                    g.node(m["id"], f'{m["display_name"]}\n({m.get("role","")})')
                for m in mems2:
                    pid = m.get("parent_id")
                    if pid and pid in id_to_name:
                        g.edge(pid, m["id"])
                st.graphviz_chart(g)
            else:
                st.info("Cadastre membros e defina **Pai** (parent_id) para montar a árvore.")
        except Exception:
            st.info("Instale `graphviz` no ambiente para visualizar a árvore familiar.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Contas ----------
    with tabs[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Contas")
        an = st.text_input("Nome")
        at = st.selectbox("Tipo", ["checking","savings","wallet","credit"])
        ob = st.number_input("Saldo inicial", min_value=0.0, step=50.0)
        if st.button("Salvar conta"):
            try:
                sb.table("accounts").insert({
                    "household_id": HOUSEHOLD_ID,"name": an.strip(),"type":at,
                    "opening_balance":ob,"currency":"BRL","is_active":True
                }).execute()
                st.toast("✅ Conta salva!", icon="✅"); st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(str(e))
        accs = fetch_accounts(False)
        for a in accs:
            c1,c2,c3 = st.columns([6,3,3])
            with c1: st.write(("✅ " if a["is_active"] else "❌ ") + a["name"])
            with c2: st.write(f"Tipo: `{a.get('type','')}`")
            with c3:
                if a["is_active"]:
                    if st.button("Desativar", key=f"acc_d_{a['id']}"):
                        sb.table("accounts").update({"is_active": False}).eq("id", a["id"]).execute(); st.cache_data.clear(); st.rerun()
                else:
                    if st.button("Ativar", key=f"acc_a_{a['id']}"):
                        sb.table("accounts").update({"is_active": True}).eq("id", a["id"]).execute(); st.cache_data.clear(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Categorias (AgGrid + ícone + excluir) ----------
    with tabs[2]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Categorias")

        # Paleta simples de ícones (emojis) para escolher
        ICON_CHOICES: Dict[str,str] = {
            "—": "",
            "🛒 Mercado": "🛒",
            "⚡ Energia": "⚡",
            "💧 Água": "💧",
            "📶 Internet": "📶",
            "🏠 Aluguel": "🏠",
            "🚗 Transporte": "🚗",
            "🍽️ Alimentação": "🍽️",
            "💊 Saúde": "💊",
            "🎓 Educação": "🎓",
            "💼 Salário": "💼",
            "💳 Cartão": "💳",
            "🎉 Lazer": "🎉",
        }

        colc1, colc2, colc3, colc4 = st.columns([2,1,1,1.5])
        cn = colc1.text_input("Nome da categoria")
        ck = colc2.selectbox("Tipo", ["income","expense"], format_func=lambda k: {"income":"Receita","expense":"Despesa"}[k])
        ic = colc3.selectbox("Ícone", list(ICON_CHOICES.keys()), index=0)
        if st.button("Salvar categoria"):
            try:
                payload = {"household_id": HOUSEHOLD_ID,"name": cn.strip(),"kind": ck}
                # tenta gravar coluna icon se existir
                if ICON_CHOICES.get(ic):
                    try:
                        payload["icon"] = ICON_CHOICES[ic]
                    except Exception:
                        pass
                sb.table("categories").insert(payload).execute()
                st.toast("✅ Categoria salva!", icon="✅"); st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(str(e))

        cats = fetch_categories()
        if not cats:
            st.info("Nenhuma categoria cadastrada.")
        else:
            # Apresenta coluna de ícone se existir
            for c in cats:
                if "icon" not in c: c["icon"] = ""
            dfc = pd.DataFrame(cats).rename(columns={"name":"Nome","kind":"Tipo","icon":"Ícone"})
            # Grid
            if AgGrid is not None:
                gob = GridOptionsBuilder.from_dataframe(dfc[["id","Ícone","Nome","Tipo"]])
                gob.configure_selection("single")
                gob.configure_grid_options(editType="fullRow")
                gob.configure_columns({
                    "id": {"editable": False},
                    "Ícone": {"editable": True},
                    "Nome": {"editable": True},
                    "Tipo": {"editable": True, "cellEditor": "agSelectCellEditor", "cellEditorParams": {"values": ["income","expense"]}},
                })
                grid = AgGrid(
                    dfc[["id","Ícone","Nome","Tipo"]],
                    gridOptions=gob.build(),
                    update_mode=GridUpdateMode.MODEL_CHANGED,
                    height=320,
                    fit_columns_on_grid_load=True,
                    key="grid_categorias"
                )
                edited_rows = grid["data"]
                colg1, colg2 = st.columns([1,1])
                with colg1:
                    if st.button("💾 Salvar edições"):
                        try:
                            for _, row in edited_rows.iterrows():
                                payload = {
                                    "name": row["Nome"],
                                    "kind": row["Tipo"],
                                }
                                # atualiza ícone se a coluna existir
                                try:
                                    payload["icon"] = row["Ícone"]
                                except Exception:
                                    pass
                                sb.table("categories").update(payload).eq("id", row["id"]).execute()
                            st.toast("Edições salvas!", icon="✅"); st.cache_data.clear(); st.rerun()
                        except Exception as e:
                            st.error(f"Falha ao salvar: {e}")
                with colg2:
                    sel = grid["selected_rows"]
                    if st.button("🗑️ Excluir selecionada"):
                        try:
                            if not sel:
                                st.warning("Selecione uma categoria no grid.")
                            else:
                                sel_id = sel[0]["id"]
                                sb.table("categories").delete().eq("id", sel_id).execute()
                                st.toast("Categoria excluída!", icon="🗑️"); st.cache_data.clear(); st.rerun()
                        except Exception as e:
                            st.error(f"Falha ao excluir: {e}")
            else:
                st.warning("Para edição avançada, instale `st-aggrid` no requirements.")
                st.dataframe(dfc[["Ícone","Nome","Tipo"]], use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Cartões ----------
    with tabs[3]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Cartões de crédito")
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
                        "limit_amount": lim, "closing_day": int(closing), "due_day": int(due),
                        "is_active": True, "created_by": user.id
                    }).execute()
                    st.toast("✅ Cartão criado!", icon="✅"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Falha: {e}")

        cards_all = fetch_cards(False)
        limits = fetch_card_limits(); limap = {x["id"]: x for x in limits}
        if not cards_all: st.info("Nenhum cartão cadastrado.")
        for c in cards_all:
            colA,colB,colC,colD = st.columns([4,3,3,2])
            with colA: st.write(f"💳 **{c['name']}**")
            with colB: st.write(f"Limite: {to_brl(c['limit_amount'])}")
            with colC: st.write("Disponível: " + to_brl(limap.get(c["id"],{}).get("available_limit", c["limit_amount"])))
            with colD:
                if c["is_active"]:
                    if st.button("Desativar", key=f"card_d_{c['id']}"):
                        sb.table("credit_cards").update({"is_active": False}).eq("id", c["id"]).execute(); st.cache_data.clear(); st.rerun()
                else:
                    if st.button("Ativar", key=f"card_a_{c['id']}"):
                        sb.table("credit_cards").update({"is_active": True}).eq("id", c["id"]).execute(); st.cache_data.clear(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# =========================
# DASHBOARDS
# =========================
if section == "📊 Dashboards":
    tabs = st.tabs(["Relatórios","Fluxo de caixa"])
    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Relatórios")
        ini = st.date_input("Início", value=date.today().replace(day=1))
        fim = st.date_input("Fim", value=date.today())
        tx = fetch_tx(ini, fim)
        mems = fetch_members(); cats = fetch_categories()
        if not tx: st.info("Sem lançamentos.")
        else:
            df = pd.DataFrame(tx)
            mem_map = {m["id"]: m["display_name"] for m in mems}
            cat_map = {c["id"]: c["name"] for c in cats}
            df["valor_eff"] = df.apply(lambda r: (r.get("paid_amount") if r.get("is_paid") else r.get("planned_amount") or r.get("amount") or 0)
                                                 * (1 if r.get("type")=="income" else -1), axis=1)
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
        txx = fetch_tx_due(ini, fim)
        if not txx: st.info("Sem previstos.")
        else:
            df = pd.DataFrame(txx)
            def eff(r):
                v = r.get("paid_amount") if r.get("is_paid") else (r.get("planned_amount") or r.get("amount") or 0)
                return v if r.get("type")=="income" else -v
            df["Quando"] = pd.to_datetime(df.get("due_date").fillna(df.get("occurred_at")), errors="coerce").dt.date
            df["Saldo"] = df.apply(eff, axis=1)
            st.line_chart(df.groupby("Quando")["Saldo"].sum().reset_index(), x="Quando", y="Saldo")
        st.markdown('</div>', unsafe_allow_html=True)
