# pages/🧰_Administracao.py
from __future__ import annotations
from datetime import date
import streamlit as st
import pandas as pd

# Utils/projeto
from utils import (
    to_brl,
    fetch_members, fetch_accounts, fetch_categories, fetch_cards, fetch_card_limits,
    send_email,  # fallback de e-mail (mantido, mas não usado neste fluxo)
)

# =========================
# 0) Gate de autenticação
# =========================
if "sb" not in st.session_state or "HOUSEHOLD_ID" not in st.session_state or "user" not in st.session_state:
    st.warning("🔒 Por favor, faça login na página principal para acessar a administração.")
    st.stop()

sb = st.session_state.sb
HOUSEHOLD_ID = st.session_state.HOUSEHOLD_ID
USER = st.session_state.user

st.title("🧰 Administração do Sistema Financeiro")

# URL base do app para construir o link de convite
APP_URL = "https://familyfinance.streamlit.app"

# =========================
# Helpers
# =========================
def _toast(msg: str, icon: str = "✅"):
    try:
        st.toast(msg, icon=icon)
    except Exception:
        st.success(msg)

def _is_owner() -> bool:
    try:
        mems = fetch_members(sb, HOUSEHOLD_ID) or []
        me = next((m for m in mems if m.get("user_id") == USER.id), None)
        return bool(me and me.get("role") == "owner")
    except Exception:
        return False

OWNER = _is_owner()

def _safe_rpc(name: str, params: dict | None = None):
    try:
        return sb.rpc(name, params or {}).execute()
    except Exception:
        return None

def _exists_table(name: str) -> bool:
    try:
        sb.table(name).select("id").eq("household_id", HOUSEHOLD_ID).limit(1).execute()
        return True
    except Exception:
        return False

def _signed_or_public_url(bucket: str, path: str, expires: int = 3600) -> str | None:
    try:
        url = sb.storage.from_(bucket).create_signed_url(path, expires)
        if isinstance(url, dict):
            return url.get("signedURL") or url.get("signed_url")
        return url
    except Exception:
        try:
            pub = sb.storage.from_(bucket).get_public_url(path)
            if isinstance(pub, dict):
                return pub.get("publicURL") or pub.get("public_url")
            return pub
        except Exception:
            return None

def _unique_name_guard(existing_names: list[str], name: str) -> bool:
    return name.strip().lower() not in {n.strip().lower() for n in existing_names}

# =========================
# 1) Aba: Membros
# =========================
def render_members_tab():
    st.subheader("👥 Membros da Família")

    # --- 1.1 Meu perfil (nome + foto)
    with st.expander("Meu perfil", expanded=True):
        mems = fetch_members(sb, HOUSEHOLD_ID) or []
        me = next((m for m in mems if m.get("user_id") == USER.id), None)
        current_name = me.get("display_name") if me else "Você"

        colA, colB = st.columns([2, 1])
        with colA:
            new_name = st.text_input("Seu nome de exibição", value=current_name, key="adm_member_display_name")
            if st.button("Salvar meu nome", use_container_width=True):
                try:
                    role = me.get("role") if me else "member"
                    sb.table("members").upsert({
                        "household_id": HOUSEHOLD_ID,
                        "user_id": USER.id,
                        "display_name": new_name.strip() or "Você",
                        "role": role
                    }, on_conflict="household_id,user_id").execute()
                    _toast("Nome salvo!")
                except Exception as e:
                    st.error(f"Erro ao salvar nome: {e}")

        with colB:
            st.write("**Foto do perfil**")
            my_member_id = me.get("id") if me else None
            if my_member_id:
                avatar_path = f"{HOUSEHOLD_ID}/{my_member_id}.png"
                url = _signed_or_public_url("avatars", avatar_path, 3600)
                if url:
                    st.image(url, width=128, caption="Atual")
            file = st.file_uploader("Enviar nova foto (PNG/JPG)", type=["png", "jpg", "jpeg"], key="upload_avatar")
            if file and my_member_id:
                try:
                    # verifica existência do bucket
                    sb.storage.from_("avatars").list("")
                except Exception:
                    st.error("Bucket 'avatars' não existe no Storage. Crie-o como público em Supabase → Storage.")
                else:
                    try:
                        content = file.read()
                        avatar_path = f"{HOUSEHOLD_ID}/{my_member_id}.png"
                        sb.storage.from_("avatars").upload(
                            avatar_path, content,
                            {"content-type": "image/png", "upsert": "true"}
                        )
                        _toast("Foto atualizada!")
                    except Exception as e:
                        st.error(f"Falha ao salvar foto: {e}")

    st.markdown("---")

    # --- 1.2 Convites (owner) — fluxo por link copiável (pending_invites + RPCs)
    with st.expander("Convidar novo membro (somente owner)", expanded=False):
        if not OWNER:
            st.info("Apenas o **owner** pode enviar convites.")
        else:
            st.caption("Gere um link único para compartilhar com o convidado. Ele expira automaticamente.")
            invite_email = st.text_input("E-mail do convidado (opcional)", key="invite_email").strip()
            invite_name = st.text_input("Nome a exibir (opcional)", key="invite_name").strip()
            expires_in = st.number_input("Expirar em (dias)", min_value=1, max_value=30, value=7, step=1)

            if st.button("Gerar link de convite", use_container_width=True, key="btn_create_invite_link"):
                # Chama RPC create_invite_link (security definer) conforme migração
                res = _safe_rpc("create_invite_link", {
                    "p_household_id": HOUSEHOLD_ID,
                    "p_email": invite_email or None,
                    "p_display_name": invite_name or None,
                    "p_expires_in_days": int(expires_in),
                    "p_app_url": APP_URL,
                })
                data = (res.data[0] if res and isinstance(res.data, list) and res.data else
                        res.data if res and isinstance(res.data, dict) else None)
                if data and data.get("url"):
                    st.success("Convite criado!")
                    st.text_input("Link do convite", value=data["url"], label_visibility="visible", disabled=True)
                    st.caption("Envie este link ao convidado. Ao acessar logado, ele será incluído na sua família.")
                else:
                    st.error(f"Falha ao criar convite. Detalhes: {getattr(res, 'data', None)}")

            st.markdown("##### Convites pendentes")
            try:
                # lista os pendentes do household
                pend = sb.table("pending_invites") \
                         .select("id, email, display_name, token, status, expires_at, created_at") \
                         .eq("household_id", HOUSEHOLD_ID) \
                         .neq("status", "used") \
                         .order("created_at", desc=True) \
                         .execute().data or []
                if not pend:
                    st.info("Nenhum convite pendente.")
                else:
                    for inv in pend:
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([4, 3, 2])
                            with c1:
                                st.markdown(f"**Para:** {inv.get('email') or '(sem e-mail)'} — {inv.get('display_name') or ''}")
                                # constrói o link a partir do token (caso queira copiar de novo)
                                url = f"{APP_URL}/?join={inv.get('token')}"
                                st.caption(f"Link: {url}")
                            with c2:
                                st.write(f"Expira em: {inv.get('expires_at')}")
                                st.info(f"Status: {inv.get('status')}")
                            with c3:
                                if st.button("Revogar", key=f"revoke_{inv['id']}"):
                                    r = _safe_rpc("revoke_invite", {"p_invite_id": inv["id"]})
                                    if r is not None:
                                        _toast("Convite revogado!")
                                    else:
                                        st.error("Falha ao revogar convite.")
            except Exception as e:
                st.error(f"Erro ao listar convites: {e}")

    st.markdown("---")

    # --- 1.3 Lista de membros com AG-Grid (editar/excluir)
    st.markdown("#### Membros cadastrados")
    mems = fetch_members(sb, HOUSEHOLD_ID) or []
    if not mems:
        st.info("Nenhum membro ainda.")
        return

    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
        df = pd.DataFrame([{
            "id": m.get("id"),
            "Nome": m.get("display_name"),
            "Papel": m.get("role"),
            "User ID": m.get("user_id"),
        } for m in mems])

        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_selection("single")
        gb.configure_column("id", hide=True)
        gb.configure_column("Nome", editable=OWNER)
        gb.configure_column("Papel", editable=OWNER, cellEditor="agSelectCellEditor",
                            cellEditorParams={"values": ["member", "owner"]})
        grid_options = gb.build()

        grid = AgGrid(
            df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.VALUE_CHANGED | GridUpdateMode.SELECTION_CHANGED,
            allow_unsafe_jscode=True,
            height=320,
            fit_columns_on_grid_load=True,
            theme="balham"
        )

        colU, colD = st.columns(2)
        with colU:
            if st.button("Salvar alterações (Nome/Papel)", use_container_width=True, disabled=not OWNER):
                try:
                    new_df = grid.data
                    new_map = {row["id"]: row for _, row in new_df.iterrows()}
                    for m in mems:
                        row = new_map.get(m["id"])
                        if not row:
                            continue
                        new_name = row["Nome"]
                        new_role = row["Papel"]
                        if new_name != m["display_name"] or new_role != m["role"]:
                            sb.table("members").update({
                                "display_name": str(new_name),
                                "role": str(new_role)
                            }).eq("id", m["id"]).execute()
                    _toast("Alterações salvas!")
                except Exception as e:
                    st.error(f"Erro ao salvar alterações: {e}")

        with colD:
            sel = grid["selected_rows"]
            disabled = not (OWNER and sel)
            if st.button("Excluir selecionado", use_container_width=True, disabled=disabled):
                try:
                    target = sel[0]["id"]
                    sb.table("members").delete().eq("id", target).execute()
                    _toast("Membro excluído!")
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

    except Exception:
        st.info("Para edição/exclusão com AG-Grid, instale `streamlit-aggrid` no requirements.")
        df = pd.DataFrame([{
            "Nome": m.get("display_name"),
            "Papel": "Owner" if m.get("role") == "owner" else "Membro",
            "User ID": m.get("user_id"),
        } for m in mems])
        st.dataframe(df, use_container_width=True)

# =========================
# 2) Aba: Contas
# =========================
def render_accounts_tab():
    st.subheader("💰 Contas")
    st.caption("Cadastre contas (corrente/poupança/carteira). *Cartões ficam na aba Cartões.*")

    with st.form("form_new_account", clear_on_submit=True):
        an = st.text_input("Nome da Conta")
        at = st.selectbox("Tipo de Conta", ["checking", "savings", "wallet"], format_func=str.capitalize)
        ob = st.number_input("Saldo Inicial (R$)", min_value=0.0, step=50.0, value=0.0)
        can_save = st.form_submit_button("Salvar Nova Conta")

        if can_save:
            if not OWNER:
                st.error("Apenas o **owner** pode criar contas.")
            elif not an.strip():
                st.error("Informe um nome válido.")
            else:
                accs = fetch_accounts(sb, HOUSEHOLD_ID, active_only=False) or []
                if not _unique_name_guard([a["name"] for a in accs], an):
                    st.error("Já existe uma conta com este nome.")
                else:
                    try:
                        sb.table("accounts").insert({
                            "household_id": HOUSEHOLD_ID,
                            "name": an.strip(),
                            "type": at,
                            "opening_balance": ob,
                            "currency": "BRL",
                            "is_active": True
                        }).execute()
                        _toast("Conta criada!")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

    st.markdown("---")
    st.markdown("#### Suas Contas")
    accs = fetch_accounts(sb, HOUSEHOLD_ID, active_only=False) or []
    if not accs:
        st.info("Nenhuma conta cadastrada.")
        return

    for a in accs:
        col1, col2, col3, col4, col5 = st.columns([3,2,2,2,2])
        with col1: st.markdown(f"**{a['name']}**")
        with col2: st.write(f"Tipo: {a.get('type','').capitalize()}")
        with col3: st.write(f"Saldo inicial: {to_brl(a.get('opening_balance',0))}")
        with col4: st.info("Ativa" if a.get("is_active") else "Inativa")
        with col5:
            lbl = "Desativar" if a.get("is_active") else "Ativar"
            if st.button(lbl, key=f"acc_toggle_{a['id']}"):
                if not OWNER:
                    st.error("Apenas owner pode alterar status.")
                else:
                    try:
                        sb.table("accounts").update({"is_active": not a["is_active"]}).eq("id", a["id"]).execute()
                        _toast("Status atualizado!")
                    except Exception as e:
                        st.error(f"Erro: {e}")

# =========================
# 3) Aba: Categorias (com ícone)
# =========================
def render_categories_tab():
    st.subheader("🏷️ Categorias")
    st.caption("Organize suas transações. Dica: escolha um ícone para facilitar os gráficos.")

    ICONES = ["💸","🛒","🍔","🍽️","🏠","🚗","🎓","🎮","🧾","📦","🧺","💊","🐶","🎁","✈️","📱","🛠️","🎬","🧒","👗","💼","🧘","⚽","🔥","🌐","💡","🍻","🧃","📚","💳","🪙","🏦","🧴","🪜"]
    with st.form("form_new_category", clear_on_submit=True):
        col1, col2, col3 = st.columns([2,1,1])
        with col1:
            cn = st.text_input("Nome da Categoria")
        with col2:
            ck = st.selectbox("Tipo", ["income", "expense"], format_func=lambda k: {"income":"Receita","expense":"Despesa"}[k])
        with col3:
            icon = st.selectbox("Ícone", ICONES, index=0)
        can_save = st.form_submit_button("Salvar Categoria")

        if can_save:
            if not OWNER:
                st.error("Apenas owner pode criar categorias.")
            elif not cn.strip():
                st.error("Informe um nome.")
            else:
                full_name = f"{icon} {cn.strip()}"
                cats = fetch_categories(sb, HOUSEHOLD_ID) or []
                if not _unique_name_guard([c["name"] for c in cats], full_name):
                    st.error("Já existe uma categoria com este nome/ícone.")
                else:
                    try:
                        sb.table("categories").insert({
                            "household_id": HOUSEHOLD_ID,
                            "name": full_name,
                            "kind": ck
                        }).execute()
                        _toast("Categoria criada!")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

    st.markdown("---")
    st.markdown("#### Suas Categorias")
    cats = fetch_categories(sb, HOUSEHOLD_ID) or []
    if not cats:
        st.info("Nenhuma categoria cadastrada.")
        return

    col_inc, col_exp = st.columns(2)
    with col_inc:
        st.markdown("##### ➕ Receitas")
        inc = [c for c in cats if c.get("kind") == "income"]
        if inc:
            for c in inc:
                st.success(f"• **{c['name']}**")
        else:
            st.info("Nenhuma categoria de receita.")
    with col_exp:
        st.markdown("##### ➖ Despesas")
        exp = [c for c in cats if c.get("kind") == "expense"]
        if exp:
            for c in exp:
                st.warning(f"• **{c['name']}**")
        else:
            st.info("Nenhuma categoria de despesa.")

# =========================
# 4) Aba: Cartões
# =========================
def render_cards_tab():
    st.subheader("💳 Cartões de Crédito")

    with st.form("form_new_card", clear_on_submit=True):
        col_nm, col_lim, col_closing, col_due = st.columns(4)
        with col_nm: nm = st.text_input("Nome do Cartão")
        with col_lim: lim = st.number_input("Limite (R$)", min_value=0.0, step=100.0, value=0.0)
        with col_closing: closing = st.number_input("Dia de Fechamento (1-31)", min_value=1, max_value=31, value=5)
        with col_due:     due = st.number_input("Dia de Vencimento (1-31)", min_value=1, max_value=31, value=15)
        can_save = st.form_submit_button("Salvar Cartão")

        if can_save:
            if not OWNER:
                st.error("Apenas owner pode criar cartões.")
            elif not nm.strip():
                st.error("Informe um nome.")
            elif lim <= 0:
                st.error("Limite deve ser positivo.")
            else:
                cards_all = fetch_cards(sb, HOUSEHOLD_ID, active_only=False) or []
                if not _unique_name_guard([c["name"] for c in cards_all], nm):
                    st.error("Já existe cartão com este nome.")
                else:
                    try:
                        sb.table("credit_cards").insert({
                            "household_id": HOUSEHOLD_ID,
                            "name": nm.strip(),
                            "limit_amount": lim,
                            "closing_day": int(closing),
                            "due_day": int(due),
                            "is_active": True,
                            "created_by": USER.id
                        }).execute()
                        _toast("Cartão criado!")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

    st.markdown("---")
    st.markdown("#### Seus Cartões")
    cards_all = fetch_cards(sb, HOUSEHOLD_ID, active_only=False) or []
    limits = fetch_card_limits(sb, HOUSEHOLD_ID) or []
    limap = {x.get("id"): x for x in limits}
    if not cards_all:
        st.info("Nenhum cartão cadastrado.")
        return
    for c in cards_all:
        available = limap.get(c["id"], {}).get("available_limit")
        with st.container(border=True):
            colA, colB, colC, colD, colE = st.columns([3,2,2,2,2])
            with colA: st.markdown(f"**{c['name']}**")
            with colB: st.write(f"Limite: {to_brl(c['limit_amount'])}")
            with colC:
                if available is None:
                    st.caption("Disponível: —")
                else:
                    st.write(f"Disponível: {to_brl(available)}")
            with colD:
                st.info(f"Fecha {c['closing_day']} • Vence {c['due_day']}")
            with colE:
                lbl = "Desativar" if c.get("is_active") else "Ativar"
                if st.button(lbl, key=f"card_toggle_{c['id']}"):
                    if not OWNER:
                        st.error("Apenas owner pode alterar status.")
                    else:
                        try:
                            sb.table("credit_cards").update({"is_active": not c["is_active"]}).eq("id", c["id"]).execute()
                            _toast("Status atualizado!")
                        except Exception as e:
                            st.error(f"Erro: {e}")

# =========================
# 5) Aba: Vínculos (membro ↔ contas/cartões)
# =========================
def render_links_tab():
    st.subheader("🔗 Vínculos (Membro ↔ Contas / Cartões)")
    st.caption("Defina responsáveis por contas e cartões. Útil para relatórios por pessoa.")

    if not OWNER:
        st.info("Apenas o **owner** pode gerenciar vínculos.")
        return

    has_acc_tbl = _exists_table("account_members")
    has_card_tbl = _exists_table("card_members")
    if not (has_acc_tbl or has_card_tbl):
        st.warning("Tabelas de vínculo não foram encontradas (`account_members`, `card_members`). "
                   "Os lançamentos ainda podem atribuir `member_id` normalmente. "
                   "Crie essas tabelas no banco para persistir os vínculos.")

    mems = fetch_members(sb, HOUSEHOLD_ID) or []
    accs = fetch_accounts(sb, HOUSEHOLD_ID, active_only=True) or []
    cards = fetch_cards(sb, HOUSEHOLD_ID, active_only=True) or []

    if not mems:
        st.info("Cadastre membros primeiro.")
        return

    member = st.selectbox("Selecione o membro", mems, format_func=lambda m: m.get("display_name"))

    with st.expander("Vincular Contas", expanded=True):
        chosen_accs = st.multiselect(
            f"Contas sob responsabilidade de {member.get('display_name')}",
            accs, format_func=lambda a: a.get("name")
        )
        if st.button("Salvar vínculos de contas", use_container_width=True, key="save_link_accounts"):
            if not has_acc_tbl:
                st.warning("Tabela `account_members` ausente. Sem persistência.")
            else:
                try:
                    sb.table("account_members").delete().eq("household_id", HOUSEHOLD_ID).eq("member_id", member["id"]).execute()
                    if chosen_accs:
                        rows = [{
                            "household_id": HOUSEHOLD_ID,
                            "account_id": a["id"],
                            "member_id": member["id"]
                        } for a in chosen_accs]
                        sb.table("account_members").insert(rows).execute()
                    _toast("Vínculos de contas salvos!")
                except Exception as e:
                    st.error(f"Erro ao salvar vínculos de contas: {e}")

    with st.expander("Vincular Cartões", expanded=False):
        chosen_cards = st.multiselect(
            f"Cartões sob responsabilidade de {member.get('display_name')}",
            cards, format_func=lambda c: c.get("name")
        )
        if st.button("Salvar vínculos de cartões", use_container_width=True, key="save_link_cards"):
            if not has_card_tbl:
                st.warning("Tabela `card_members` ausente. Sem persistência.")
            else:
                try:
                    sb.table("card_members").delete().eq("household_id", HOUSEHOLD_ID).eq("member_id", member["id"]).execute()
                    if chosen_cards:
                        rows = [{
                            "household_id": HOUSEHOLD_ID,
                            "card_id": c["id"],
                            "member_id": member["id"]
                        } for c in chosen_cards]
                        sb.table("card_members").insert(rows).execute()
                    _toast("Vínculos de cartões salvos!")
                except Exception as e:
                    st.error(f"Erro ao salvar vínculos de cartões: {e}")

# =========================
# 6) Aba: Família / Árvore (cadastro de relações)
# =========================
def render_family_tab():
    st.subheader("🌳 Família / Relações")
    st.caption("Cadastre relações (pais, filhos, cônjuge, tios, primos, etc.).")

    if not OWNER:
        st.info("Apenas **owner** pode editar relações familiares.")
        return

    has_rel_tbl = _exists_table("relationships")
    if not has_rel_tbl:
        st.warning("Tabela `relationships` não encontrada. Crie-a para registrar relações familiares.")
        return

    mems = fetch_members(sb, HOUSEHOLD_ID) or []
    if len(mems) < 2:
        st.info("Cadastre pelo menos duas pessoas para criar uma relação.")
        return

    left = st.selectbox("Pessoa A", mems, format_func=lambda m: m.get("display_name"))
    right = st.selectbox("Pessoa B", [m for m in mems if m["id"] != left["id"]], format_func=lambda m: m.get("display_name"))
    relation = st.selectbox(
        "Relação de A para B",
        ["parent", "child", "spouse", "sibling", "uncle_aunt", "nephew_niece", "cousin", "in_law", "other"],
        format_func=lambda k: {
            "parent": "Ascendente (A é pai/mãe de B)",
            "child": "Descendente (A é filho/filha de B)",
            "spouse": "Cônjuge",
            "sibling": "Irmão/irmã",
            "uncle_aunt": "Tio/Tia",
            "nephew_niece": "Sobrinho/Sobrinha",
            "cousin": "Primo/Prima",
            "in_law": "Parente por afinidade (cunhado/…)",
            "other": "Outro",
        }[k]
    )
    if st.button("Salvar relação", use_container_width=True):
        try:
            sb.table("relationships").upsert({
                "household_id": HOUSEHOLD_ID,
                "member_a": left["id"],
                "member_b": right["id"],
                "relation": relation
            }, on_conflict="household_id,member_a,member_b").execute()
            _toast("Relação salva!")
        except Exception as e:
            st.error(f"Erro ao salvar relação: {e}")

    st.markdown("---")
    st.markdown("#### Relações existentes")
    try:
        rows = sb.table("relationships").select("*").eq("household_id", HOUSEHOLD_ID).execute().data or []
        if not rows:
            st.info("Nenhuma relação registrada.")
        else:
            def name(mid):
                m = next((x for x in mems if x["id"] == mid), None)
                return m["display_name"] if m else mid
            df = pd.DataFrame([{
                "A": name(r["member_a"]),
                "Relação": r["relation"],
                "B": name(r["member_b"])
            } for r in rows])
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao ler relações: {e}")

# =========================
# 7) Renderização das Abas
# =========================
tabs = st.tabs(["👥 Membros", "💰 Contas", "🏷️ Categorias", "💳 Cartões", "🔗 Vínculos", "🌳 Família"])

with tabs[0]:
    with st.container(border=True):
        render_members_tab()

with tabs[1]:
    with st.container(border=True):
        render_accounts_tab()

with tabs[2]:
    with st.container(border=True):
        render_categories_tab()

with tabs[3]:
    with st.container(border=True):
        render_cards_tab()

with tabs[4]:
    with st.container(border=True):
        render_links_tab()

with tabs[5]:
    with st.container(border=True):
        render_family_tab()
