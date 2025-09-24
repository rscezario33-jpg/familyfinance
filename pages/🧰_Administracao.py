# pages/🧰_Administracao.py
from __future__ import annotations
from datetime import date
import streamlit as st
from utils import to_brl, fetch_members, fetch_accounts, fetch_categories, fetch_cards, fetch_card_limits

# Acessa o cliente Supabase e IDs do household/membro da sessão
if "sb" not in st.session_state or "HOUSEHOLD_ID" not in st.session_state or "user" not in st.session_state:
    st.warning("Por favor, faça login na página principal.")
    st.stop()

sb = st.session_state.sb
HOUSEHOLD_ID = st.session_state.HOUSEHOLD_ID
user = st.session_state.user

st.title("🧰 Administração")
tabs = st.tabs(["Membros","Contas","Categorias","Cartões"])

# Membros
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Membros")
    nm = st.text_input("Seu nome de exibição", value="Você")

    if st.button("Salvar"):
        try:
            sb.table("members").upsert({
                "household_id": HOUSEHOLD_ID,
                "user_id": user.id,
                "display_name": nm.strip(),
                "role":"owner" # Assumimos que o criador é owner
            }, on_conflict="household_id,user_id").execute()
            st.toast("✅ Salvo!", icon="✅"); st.cache_data.clear(); st.rerun()
        except Exception as e:
            st.error(str(e))

    mems = fetch_members(sb, HOUSEHOLD_ID)
    if mems:
        chips = " ".join([f'<span class="badge">�� {m["display_name"]}{" · owner" if m["role"]=="owner" else ""}</span>' for m in mems])
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
                "household_id": HOUSEHOLD_ID,
                "name": an.strip(),
                "type":at,
                "opening_balance":ob,
                "currency":"BRL",
                "is_active":True
            }).execute()
            st.toast("✅ Conta salva!", icon="✅"); st.cache_data.clear(); st.rerun()
        except Exception as e:
            st.error(str(e))

    accs = fetch_accounts(sb, HOUSEHOLD_ID, False)
    for a in accs:
        c1,c2,c3 = st.columns([6,3,3])
        with c1:
            st.write(("✅ " if a["is_active"] else "❌ ") + a["name"])
        with c2:
            st.write(f"Tipo: {a.get('type','')}")
        with c3:
            if a["is_active"]:
                if st.button("Desativar", key=f"acc_d_{a['id']}"):
                    sb.table("accounts").update({"is_active": False}).eq("id", a["id"]).execute(); st.cache_data.clear(); st.rerun()
            else:
                if st.button("Ativar", key=f"acc_a_{a['id']}"):
                    sb.table("accounts").update({"is_active": True}).eq("id", a["id"]).execute(); st.cache_data.clear(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Categorias
with tabs[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Categorias")
    cn = st.text_input("Nome da categoria")
    ck = st.selectbox("Tipo", ["income","expense"], format_func=lambda k: {"income":"Receita","expense":"Despesa"}[k])

    if st.button("Salvar categoria"):
        try:
            sb.table("categories").insert({"household_id": HOUSEHOLD_ID,"name": cn.strip(),"kind": ck}).execute()
            st.toast("✅ Categoria salva!", icon="✅"); st.cache_data.clear(); st.rerun()
        except Exception as e:
            st.error(str(e))

    cats = fetch_categories(sb, HOUSEHOLD_ID)
    if cats:
        chips_inc = " ".join([f'<span class="badge green">#{c["name"]}</span>' for c in cats if c["kind"]=="income"])
        chips_exp = " ".join([f'<span class="badge red">#{c["name"]}</span>' for c in cats if c["kind"]=="expense"])
        st.markdown("**Receitas**"); st.markdown(chips_inc or "_(vazio)_", unsafe_allow_html=True)
        st.markdown("**Despesas**"); st.markdown(chips_exp or "_(vazio)_", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Cartões (somente aqui)
with tabs[3]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Cartões de crédito")
    with st.form("novo_cartao_admin"):
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            nm = st.text_input("Nome do cartão")
        with c2:
            lim = st.number_input("Limite (R\$)", min_value=0.0, step=100.0)
        with c3:
            closing = st.number_input("Fechamento (1-28)", min_value=1, max_value=28, value=5)
        with c4:
            due = st.number_input("Vencimento (1-28)", min_value=1, max_value=28, value=15)
        okc = st.form_submit_button("Salvar cartão")

        if okc and nm.strip():
            try:
                sb.table("credit_cards").insert({
                    "household_id": HOUSEHOLD_ID,
                    "name": nm.strip(),
                    "limit_amount": lim,
                    "closing_day": int(closing),
                    "due_day": int(due),
                    "is_active": True,
                    "created_by": user.id
                }).execute()
                st.toast("✅ Cartão criado!", icon="✅"); st.cache_data.clear(); st.rerun()
            except Exception as e:
                st.error(f"Falha: {e}")

    cards_all = fetch_cards(sb, HOUSEHOLD_ID, False)
    limits = fetch_card_limits(sb, HOUSEHOLD_ID); limap = {x["id"]: x for x in limits}

    if not cards_all:
        st.info("Nenhum cartão cadastrado.")

    for c in cards_all:
        colA,colB,colC,colD = st.columns([4,3,3,2])
        with colA:
            st.write(f"�� **{c['name']}**")
        with colB:
            st.write(f"Limite: {to_brl(c['limit_amount'])}")
        with colC:
            st.write("Disponível: " + to_brl(limap.get(c["id"],{}).get("available_limit", c["limit_amount"])))
        with colD:
            if c["is_active"]:
                if st.button("Desativar", key=f"card_d_{c['id']}"):
                    sb.table("credit_cards").update({"is_active": False}).eq("id", c["id"]).execute(); st.cache_data.clear(); st.rerun()
            else:
                if st.button("Ativar", key=f"card_a_{c['id']}"):
                    sb.table("credit_cards").update({"is_active": True}).eq("id", c["id"]).execute(); st.cache_data.clear(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
