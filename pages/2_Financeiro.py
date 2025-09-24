# pages/2_Financeiro.py — Financeiro (Lançamentos, Movimentações, Fixas, Orçamentos, Fluxo)
from datetime import date, timedelta
import os, uuid
import pandas as pd
import streamlit as st
from ff_shared import (
    inject_css, sidebar_shell, user, bootstrap, fetch_categories, fetch_accounts, fetch_cards,
    fetch_card_limits, fetch_tx, fetch_tx_due, to_brl, sb
)

st.set_page_config(page_title="Family Finance — Financeiro", layout="wide")
inject_css()

u = user()
if not u: st.switch_page("app.py")
hid_mid = bootstrap(u.id); HOUSEHOLD_ID = hid_mid["household_id"]; MY_MEMBER_ID = hid_mid["member_id"]

with st.sidebar: sidebar_shell()

st.title("💼 Financeiro")
tabs = st.tabs(["Lançamentos","Movimentações","Receitas/Despesas fixas","Orçamentos","Fluxo de caixa"])

# ---- Lançamentos
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("➕ Lançar")
    cats = fetch_categories(HOUSEHOLD_ID); cat_map = {c["name"]: c for c in cats}
    accs = fetch_accounts(HOUSEHOLD_ID, True); acc_map = {a["name"]: a for a in accs}
    cards = fetch_cards(HOUSEHOLD_ID, True); card_map = {c["name"]: c for c in cards}

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
                attachment_url=None
                if boleto is not None:
                    ext = os.path.splitext(boleto.name)[1].lower()
                    key = f"{HOUSEHOLD_ID}/{uuid.uuid4().hex}{ext}"
                    data_bytes = boleto.read()
                    sb.storage.from_("boletos").upload(key, data_bytes)
                    attachment_url = sb.storage.from_("boletos").get_public_url(key)

                if tipo=="expense" and parcelado:
                    sb.rpc("create_installments", {
                        "p_household": HOUSEHOLD_ID,"p_member": MY_MEMBER_ID,"p_account": acc_id,
                        "p_category": cat_id,"p_desc": desc,"p_total": val,"p_n": int(n_parc),
                        "p_first_due": due.isoformat(),"p_payment_method": method,"p_card_id": card_id
                    }).execute()
                else:
                    planned = val
                    sb.table("transactions").insert({
                        "household_id": HOUSEHOLD_ID, "member_id": MY_MEMBER_ID,
                        "account_id": acc_id, "category_id": cat_id,
                        "type": tipo, "amount": val, "planned_amount": planned,
                        "occurred_at": data.isoformat(), "due_date": due.isoformat(),
                        "description": desc, "payment_method": method, "card_id": card_id,
                        "attachment_url": attachment_url, "created_by": u.id
                    }).execute()
                st.toast("✅ Lançamento registrado!", icon="✅"); st.cache_data.clear(); st.rerun()
            except Exception as e:
                st.error(f"Falha: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# ---- Movimentações
with tabs[1]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📋 Movimentações")
    ini = st.date_input("Início", value=date.today().replace(day=1), key="mv_ini")
    fim = st.date_input("Fim", value=date.today(), key="mv_fim")
    tx = fetch_tx(HOUSEHOLD_ID, ini, fim)
    if not tx: st.info("Sem lançamentos.")
    else:
        df = pd.DataFrame(tx)
        df["Data"] = pd.to_datetime(df.get("occurred_at"), errors="coerce").dt.strftime("%d/%m/%Y")
        df["Venc"] = pd.to_datetime(df.get("due_date"), errors="coerce").dt.strftime("%d/%m/%Y")
        df["Tipo"] = df.get("type").map({"income":"Receita","expense":"Despesa"})
        df["Previsto (R$)"] = (df.get("planned_amount").fillna(df.get("amount")).fillna(0.0)).astype(float)
        df["Pago?"] = df

