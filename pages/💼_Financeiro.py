# pages/💼_Financeiro.py
from __future__ import annotations
from datetime import date, datetime, timedelta
import uuid
import os
import streamlit as st
import pandas as pd
from utils import to_brl, _to_date_safe, fetch_categories, fetch_accounts, fetch_cards, fetch_tx, fetch_tx_due

# Acessa o cliente Supabase e IDs do household/membro da sessão
if "sb" not in st.session_state or "HOUSEHOLD_ID" not in st.session_state or "MY_MEMBER_ID" not in st.session_state or "user" not in st.session_state:
    st.warning("Por favor, faça login na página principal.")
    st.stop()

sb = st.session_state.sb
HOUSEHOLD_ID = st.session_state.HOUSEHOLD_ID
MY_MEMBER_ID = st.session_state.MY_MEMBER_ID
user = st.session_state.user

st.title("💼 Financeiro")
tabs = st.tabs(["Lançamentos","Movimentações","Receitas/Despesas fixas","Orçamentos","Fluxo de caixa"])

# Lançamentos
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("➕ Lançar")

    cats = fetch_categories(sb, HOUSEHOLD_ID)
    cat_map = {c["name"]: c for c in cats}
    accs = fetch_accounts(sb, HOUSEHOLD_ID, True)
    acc_map = {a["name"]: a for a in accs}
    cards = fetch_cards(sb, HOUSEHOLD_ID, True)
    card_map = {c["name"]: c for c in cards}

    with st.form("quick_tx"):
        col1,col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo", ["income","expense"], index=1, format_func=lambda x: {"income":"Receita","expense":"Despesa"}[x])
            cat = st.selectbox("Categoria", list(cat_map.keys()) or ["Mercado"])
            desc = st.text_input("Descrição")
            data = st.date_input("Data", value=date.today())
            due = st.date_input("Vencimento", value=date.today())
        with col2:
            val = st.number_input("Valor", min_value=0.0, step=10.0)
            method = st.selectbox("Forma de pagamento", ["account","card"], index=0, format_func=lambda x: "Conta" if x=="account" else "Cartão")
            acc = st.selectbox("Conta", list(acc_map.keys()) or ["Conta Corrente"])
            card_name = st.selectbox("Cartão (se aplicável)", ["—"] + list(card_map.keys()))
            parcelado = st.checkbox("Parcelado? (somente despesa)")
            n_parc = st.number_input("Nº parcelas", min_value=2, max_value=36, value=2, disabled=not (parcelado and tipo=="expense"))

            # Anexo opcional (boleto)
            boleto = st.file_uploader("Anexar boleto (PDF/JPG/PNG) — opcional", type=["pdf","jpg","jpeg","png"])
        ok = st.form_submit_button("Lançar")

        if ok:
            try:
                cat_id = (cat_map.get(cat) or {}).get("id")
                acc_id = (acc_map.get(acc) or {}).get("id")
                card_id = (card_map.get(card_name) or {}).get("id") if method=="card" and card_name!="—" else None
                attachment_url = None

                # upload do boleto (se houver)
                if boleto is not None:
                    ext = os.path.splitext(boleto.name)[1].lower()
                    # Garante que o nome do arquivo seja único e associado ao household e usuário logado para RLS do storage
                    key = f"{HOUSEHOLD_ID}/{user.id}/{uuid.uuid4().hex}{ext}"
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
                        "household_id": HOUSEHOLD_ID,
                        "member_id": MY_MEMBER_ID,
                        "account_id": acc_id,
                        "category_id": cat_id,
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
    tx = fetch_tx(sb, HOUSEHOLD_ID, ini, fim)

    if not tx:
        st.info("Sem lançamentos.")
    else:
        df = pd.DataFrame(tx)
        df["Data"] = pd.to_datetime(df.get("occurred_at"), errors="coerce").dt.strftime("%d/%m/%Y")
        df["Venc"] = pd.to_datetime(df.get("due_date"), errors="coerce").dt.strftime("%d/%m/%Y")
        df["Tipo"] = df.get("type").map({"income":"Receita","expense":"Despesa"})
        df["Previsto (R\$)"] = (df.get("planned_amount").fillna(df.get("amount")).fillna(0.0)).astype(float)
        df["Pago?"] = df.get("is_paid").fillna(False)
        df["Pago (R\$)"] = df.get("paid_amount").fillna("")

        st.dataframe(
            df[["Data","Venc","Tipo","description","Previsto (R\$)","Pago?","Pago (R\$)","attachment_url","id"]]
            .rename(columns={"description":"Descrição","attachment_url":"Boleto"}),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Marcar pagamento / Anexar boleto")
        tx_id_options = df["id"].tolist()
        tx_id = st.selectbox("Transação", tx_id_options, format_func=lambda x: f"ID: {x} - {df[df['id']==x]['description'].iloc[0]}")

        # Valor pago: se não preencher, usa o previsto da transação
        pago_v = st.number_input("Valor pago (R\$) — deixe 0 para usar o previsto", min_value=0.0, step=10.0)
        pago_d = st.date_input("Data pagamento", value=date.today())
        novo_boleto = st.file_uploader("Anexar/atualizar boleto", type=["pdf","jpg","jpeg","png"], key="mv_bol")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Confirmar pagamento"):
                try:
                    row = df[df["id"]==tx_id].iloc[0]
                    previsto = float(row["Previsto (R\$)"]) if row is not None else 0.0
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
                        # Garante que o nome do arquivo seja único e associado ao household e usuário logado
                        key = f"{HOUSEHOLD_ID}/{user.id}/{tx_id}{ext}"
                        data_bytes = novo_boleto.read()
                        sb.storage.from_("boletos").upload(key, data_bytes, {"upsert": True})
                        url = sb.storage.from_("boletos").get_public_url(key)
                        sb.table("transactions").update({"attachment_url": url}).eq("id", tx_id).execute()
                        st.toast("Anexo salvo!", icon="📎"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Falha ao anexar: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# Fixas (cria lançamentos previstos; pagamento é controlado em Movimentações)
with tabs[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("♻️ Receitas/Despesas fixas")

    cats = fetch_categories(sb, HOUSEHOLD_ID); cat_map = {c["name"]: c for c in cats}
    accs = fetch_accounts(sb, HOUSEHOLD_ID, True); acc_map = {a["name"]: a for a in accs}
    cards = fetch_cards(sb, HOUSEHOLD_ID, True); card_map = {c["name"]: c for c in cards}

    with st.form("fixas_form"):
        col1,col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo", ["income","expense"], index=1, format_func=lambda x: {"income":"Receita","expense":"Despesa"}[x])
            cat = st.selectbox("Categoria", list(cat_map.keys()) or ["Energia","Salário"])
            desc = st.text_input("Descrição (ex.: [FIXA] Energia)")
            start_due = st.date_input("Vencimento inicial", value=date.today())
        with col2:
            previsto = st.number_input("Valor previsto (R\$)", min_value=0.0, step=10.0)
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

                # mês inicial
                sb.table("transactions").insert({
                    "household_id": HOUSEHOLD_ID,
                    "member_id": MY_MEMBER_ID,
                    "account_id": acc_id,
                    "category_id": cat_id,
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

                # próximos meses
                d = start_due
                for _ in range(int(meses)):
                    first_next = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
                    try:
                        d = first_next.replace(day=start_due.day)
                    except ValueError: # Caso o dia não exista no próximo mês (ex: 31 de jan -> 31 de fev)
                        last = (first_next + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                        d = last

                    sb.table("transactions").insert({
                        "household_id": HOUSEHOLD_ID,
                        "member_id": MY_MEMBER_ID,
                        "account_id": acc_id,
                        "category_id": cat_id,
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

    cats = fetch_categories(sb, HOUSEHOLD_ID); cat_by_name = {c["name"]: c for c in cats}
    colb1,colb2 = st.columns([2,1])
    with colb1:
        cat_name = st.selectbox("Categoria", list(cat_by_name.keys()) or ["Mercado"])
    with colb2:
        val_orc = st.number_input("Orçado (R\$)", min_value=0.0, step=50.0)

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
    with f1:
        ini = st.date_input("Início", value=date.today().replace(day=1), key="fx_ini")
    with f2:
        fim = st.date_input("Fim", value=date.today()+timedelta(days=60), key="fx_fim")
    txx = fetch_tx_due(sb, HOUSEHOLD_ID, ini, fim)

    if not txx:
        st.info("Sem previstos no período.")
    else:
        df = pd.DataFrame(txx)
        def eff(r):
            v = r.get("paid_amount") if r.get("is_paid") else (r.get("planned_amount") or r.get("amount") or 0)
            return v if r.get("type")=="income" else -v
        df["Quando"] = pd.to_datetime(df.get("due_date").fillna(df.get("occurred_at")), errors="coerce").dt.date
        df["Saldo"] = df.apply(eff, axis=1)
        st.line_chart(df.groupby("Quando")["Saldo"].sum().reset_index(), x="Quando", y="Saldo")
    st.markdown('</div>', unsafe_allow_html=True)
