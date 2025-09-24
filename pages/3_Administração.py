# pages/3_Administração.py — Family Finance (Página: Administração)
from __future__ import annotations
from datetime import date, timedelta
import pandas as pd
import streamlit as st

from ff_shared import (
    sb, inject_css, sidebar_shell,
    user, bootstrap, to_brl,
    fetch_members, fetch_accounts, fetch_categories,
    fetch_cards, fetch_card_limits
)

# AgGrid (opcional)
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
except Exception:
    AgGrid = None

st.set_page_config(page_title="Family Finance — Administração", layout="wide")
inject_css()

# ====== Auth / contexto do lar ======
u = user()
if not u:
    st.error("Faça login para acessar Administração.")
    st.stop()

ids = bootstrap(u.id)
HOUSEHOLD_ID = ids["household_id"]
MY_MEMBER_ID = ids["member_id"]

# ====== Sidebar padrão ======
with st.sidebar:
    sidebar_shell(show_logout=True)

st.title("Administração")
tabs = st.tabs(["Membros", "Contas", "Categorias", "Cartões"])

# -------------------------------------------------------------------
# 1) Membros (grid editável + excluir + convite + árvore)
# -------------------------------------------------------------------
with tabs[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Membros da família")

    # Cadastro rápido
    colm1, colm2, colm3 = st.columns([2, 1, 1])
    nm = colm1.text_input("Nome de exibição", value="")
    role = colm2.selectbox("Papel", ["owner", "member", "viewer"], index=1)
    parent_id_input = colm3.text_input("Parent ID (opcional)")
    if st.button("Salvar membro"):
        try:
            sb.table("members").upsert({
                "household_id": HOUSEHOLD_ID,
                "user_id": None,                 # definido ao aceitar convite
                "display_name": nm.strip(),
                "role": role,
                "parent_id": parent_id_input.strip() or None
            }).execute()
            st.toast("✅ Membro salvo!", icon="✅")
            st.cache_data.clear(); st.rerun()
        except Exception as e:
            st.error(str(e))

    mems = fetch_members(HOUSEHOLD_ID)
    if not mems:
        st.info("Sem membros cadastrados ainda.")
    else:
        dfm = pd.DataFrame(mems).rename(columns={
            "display_name": "Nome",
            "role": "Papel",
            "user_id": "Usuário",
            "parent_id": "Pai"
        })

        if AgGrid is not None:
            gob = GridOptionsBuilder.from_dataframe(dfm[["id", "Nome", "Papel", "Usuário", "Pai"]])
            gob.configure_selection("single")
            gob.configure_grid_options(editType="fullRow")
            gob.configure_columns({
                "id": {"editable": False},
                "Nome": {"editable": True},
                "Papel": {"editable": True, "cellEditor": "agSelectCellEditor",
                          "cellEditorParams": {"values": ["owner", "member", "viewer"]}},
                "Usuário": {"editable": False},
                "Pai": {"editable": True},
            })
            grid = AgGrid(
                dfm[["id", "Nome", "Papel", "Usuário", "Pai"]],
                gridOptions=gob.build(),
                update_mode=GridUpdateMode.MODEL_CHANGED,
                height=320,
                fit_columns_on_grid_load=True,
                key="grid_membros_admin"
            )
            edited = grid["data"]
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                if st.button("💾 Salvar edições"):
                    try:
                        for _, r in edited.iterrows():
                            sb.table("members").update({
                                "display_name": r["Nome"],
                                "role": r["Papel"],
                                "parent_id": r["Pai"] if r["Pai"] else None
                            }).eq("id", r["id"]).execute()
                        st.toast("Edições salvas!", icon="✅"); st.cache_data.clear(); st.rerun()
                    except Exception as e:
                        st.error(f"Falha ao salvar: {e}")
            with c2:
                sel = grid["selected_rows"]
                if st.button("🗑️ Excluir selecionado"):
                    try:
                        if not sel:
                            st.warning("Selecione um membro no grid.")
                        else:
                            sb.table("members").delete().eq("id", sel[0]["id"]).execute()
                            st.toast("Membro excluído!", icon="🗑️"); st.cache_data.clear(); st.rerun()
                    except Exception as e:
                        st.error(f"Falha ao excluir: {e}")
            with c3:
                invite_email = st.text_input("Enviar convite por e-mail")
                if st.button("✉️ Enviar convite"):
                    try:
                        # registra convite (se a tabela existir) e envia por e-mail via `ff_shared` (SMTP opcional)
                        try:
                            sb.table("pending_invites").insert({
                                "household_id": HOUSEHOLD_ID,
                                "email": invite_email,
                                "invited_by": u.id
                            }).execute()
                        except Exception:
                            pass
                        app_url = st.secrets.get("app", {}).get("url", "https://familyfinance.streamlit.app") \
                                  if hasattr(st, "secrets") else "https://familyfinance.streamlit.app"
                        from ff_shared import send_email
                        ok = send_email([invite_email], "Convite — Family Finance",
                                        f"Você foi convidado(a) para o Family Finance.\nAcesse: {app_url}\n\n"
                                        "Ao entrar, você será associado(a) ao lar.")
                        st.toast("Convite registrado!" + (" ✉️ E-mail enviado." if ok else " (sem SMTP)"), icon="✉️")
                    except Exception as e:
                        st.error(f"Falha ao convidar: {e}")
        else:
            st.warning("Para edição avançada, instale `st-aggrid` no requirements.")
            st.dataframe(dfm, use_container_width=True, hide_index=True)

    st.markdown("### 👪 Árvore familiar")
    try:
        import graphviz
        mems2 = fetch_members(HOUSEHOLD_ID)
        if mems2:
            g = graphviz.Digraph(format="svg")
            g.attr("node", shape="box", style="rounded,filled", color="#0b2038", fillcolor="#eef6ff")
            names = {m["id"]: m["display_name"] for m in mems2}
            for m in mems2:
                g.node(m["id"], f'{m["display_name"]}\n({m.get("role","")})')
            for m in mems2:
                pid = m.get("parent_id")
                if pid and pid in names:
                    g.edge(pid, m["id"])
            st.graphviz_chart(g)
        else:
            st.info("Cadastre membros e defina **Pai** (parent_id) para montar a árvore.")
    except Exception:
        st.info("Instale `graphviz` no ambiente para visualizar a árvore.")
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------------------------
# 2) Contas
# -------------------------------------------------------------------
with tabs[1]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Contas")

    an = st.text_input("Nome")
    at = st.selectbox("Tipo", ["checking", "savings", "wallet", "credit"])
    ob = st.number_input("Saldo inicial", min_value=0.0, step=50.0)

    if st.button("Salvar conta"):
        try:
            sb.table("accounts").insert({
                "household_id": HOUSEHOLD_ID, "name": an.strip(), "type": at,
                "opening_balance": ob, "currency": "BRL", "is_active": True
            }).execute()
            st.toast("✅ Conta salva!", icon="✅"); st.cache_data.clear(); st.rerun()
        except Exception as e:
            st.error(str(e))

    accs = fetch_accounts(HOUSEHOLD_ID, False)
    for a in accs:
        c1, c2, c3 = st.columns([6, 3, 3])
        with c1: st.write(("✅ " if a["is_active"] else "❌ ") + a["name"])
        with c2: st.write(f"Tipo: `{a.get('type','')}`")
        with c3:
            if a["is_active"]:
                if st.button("Desativar", key=f"acc_d_{a['id']}"):
                    sb.table("accounts").update({"is_active": False}).eq("id", a["id"]).execute()
                    st.cache_data.clear(); st.rerun()
            else:
                if st.button("Ativar", key=f"acc_a_{a['id']}"):
                    sb.table("accounts").update({"is_active": True}).eq("id", a["id"]).execute()
                    st.cache_data.clear(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------------------------
# 3) Categorias (grid com ícone/editar/excluir)
# -------------------------------------------------------------------
with tabs[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Categorias")

    ICON_CHOICES = {
        "—": "", "🛒 Mercado": "🛒", "⚡ Energia": "⚡", "💧 Água": "💧", "📶 Internet": "📶",
        "🏠 Aluguel": "🏠", "🚗 Transporte": "🚗", "🍽️ Alimentação": "🍽️",
        "💊 Saúde": "💊", "🎓 Educação": "🎓", "💼 Salário": "💼", "💳 Cartão": "💳", "🎉 Lazer": "🎉",
    }

    col1, col2, col3 = st.columns([2, 1, 1])
    cn = col1.text_input("Nome da categoria")
    ck = col2.selectbox("Tipo", ["income", "expense"], format_func=lambda k: {"income": "Receita", "expense": "Despesa"}[k])
    ic = col3.selectbox("Ícone", list(ICON_CHOICES.keys()), index=0)

    if st.button("Salvar categoria"):
        try:
            payload = {"household_id": HOUSEHOLD_ID, "name": cn.strip(), "kind": ck}
            if ICON_CHOICES.get(ic):
                payload["icon"] = ICON_CHOICES[ic]
            sb.table("categories").insert(payload).execute()
            st.toast("✅ Categoria salva!", icon="✅"); st.cache_data.clear(); st.rerun()
        except Exception as e:
            st.error(str(e))

    cats = fetch_categories(HOUSEHOLD_ID)
    if not cats:
        st.info("Nenhuma categoria cadastrada.")
    else:
        for c in cats:
            if "icon" not in c: c["icon"] = ""
        dfc = pd.DataFrame(cats).rename(columns={"name": "Nome", "kind": "Tipo", "icon": "Ícone"})

        if AgGrid is not None:
            gob = GridOptionsBuilder.from_dataframe(dfc[["id", "Ícone", "Nome", "Tipo"]])
            gob.configure_selection("single")
            gob.configure_grid_options(editType="fullRow")
            gob.configure_columns({
                "id": {"editable": False},
                "Ícone": {"editable": True},
                "Nome": {"editable": True},
                "Tipo": {"editable": True, "cellEditor": "agSelectCellEditor",
                         "cellEditorParams": {"values": ["income", "expense"]}},
            })
            grid = AgGrid(
                dfc[["id", "Ícone", "Nome", "Tipo"]],
                gridOptions=gob.build(),
                update_mode=GridUpdateMode.MODEL_CHANGED,
                height=320,
                fit_columns_on_grid_load=True,
                key="grid_categorias_admin"
            )
            edited = grid["data"]
            g1, g2 = st.columns([1, 1])
            with g1:
                if st.button("💾 Salvar edições"):
                    try:
                        for _, r in edited.iterrows():
                            payload = {"name": r["Nome"], "kind": r["Tipo"], "icon": r["Ícone"]}
                            sb.table("categories").update(payload).eq("id", r["id"]).execute()
                        st.toast("Edições salvas!", icon="✅"); st.cache_data.clear(); st.rerun()
                    except Exception as e:
                        st.error(f"Falha ao salvar: {e}")
            with g2:
                sel = grid["selected_rows"]
                if st.button("🗑️ Excluir selecionada"):
                    try:
                        if not sel:
                            st.warning("Selecione uma categoria no grid.")
                        else:
                            sb.table("categories").delete().eq("id", sel[0]["id"]).execute()
                            st.toast("Categoria excluída!", icon="🗑️"); st.cache_data.clear(); st.rerun()
                    except Exception as e:
                        st.error(f"Falha ao excluir: {e}")
        else:
            st.warning("Para edição avançada, instale `st-aggrid` no requirements.")
            st.dataframe(dfc[["Ícone", "Nome", "Tipo"]], use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------------------------
# 4) Cartões
# -------------------------------------------------------------------
with tabs[3]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Cartões de crédito")

    with st.form("novo_cartao_admin"):
        c1, c2, c3, c4 = st.columns(4)
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
                    "is_active": True, "created_by": u.id
                }).execute()
                st.toast("✅ Cartão criado!", icon="✅"); st.cache_data.clear(); st.rerun()
            except Exception as e:
                st.error(f"Falha: {e}")

    cards_all = fetch_cards(HOUSEHOLD_ID, False)
    limits = fetch_card_limits(HOUSEHOLD_ID); limap = {x["id"]: x for x in limits}
    if not cards_all:
        st.info("Nenhum cartão cadastrado.")
    for c in cards_all:
        colA, colB, colC, colD = st.columns([4, 3, 3, 2])
        with colA: st.write(f"💳 **{c['name']}**")
        with colB: st.write(f"Limite: {to_brl(c['limit_amount'])}")
        with colC: st.write("Disponível: " + to_brl(limap.get(c["id"], {}).get("available_limit", c["limit_amount"])))
        with colD:
            if c["is_active"]:
                if st.button("Desativar", key=f"card_d_{c['id']}"):
                    sb.table("credit_cards").update({"is_active": False}).eq("id", c["id"]).execute()
                    st.cache_data.clear(); st.rerun()
            else:
                if st.button("Ativar", key=f"card_a_{c['id']}"):
                    sb.table("credit_cards").update({"is_active": True}).eq("id", c["id"]).execute()
                    st.cache_data.clear(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

