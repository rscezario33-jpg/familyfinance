# pages/🧰_Administracao.py
from __future__ import annotations
from datetime import date
from io import BytesIO
import base64
import streamlit as st
import pandas as pd

# Utils/projeto
from utils import (
    to_brl,
    fetch_members, fetch_accounts, fetch_categories, fetch_cards, fetch_card_limits,
    send_email,
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

# =========================
# Helpers
# =========================
def _clear_and_rerun():
    st.cache_data.clear()
    st.rerun()

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
    except Exception as e:
        return None

def _exists_table(name: str) -> bool:
    # tentativa simples: selecionar 1 linha
    try:
        sb.table(name).select("id").eq("household_id", HOUSEHOLD_ID).limit(1).execute()
        return True
    except Exception:
        return False

def _signed_or_public_url(bucket: str, path: str, expires: int = 3600) -> str | None:
    try:
        # tenta signed
        url = sb.storage.from_(bucket).create_signed_url(path, expires)
        if url and isinstance(url, dict):
            return url.get("signedURL") or url.get("signed_url")
        # fallback: público
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
                    # Não promove papel: se já existir, mantém papel atual; senão, cria como 'member'
                    role = me.get("role") if me else "member"
                    sb.table("members").upsert({
                        "household_id": HOUSEHOLD_ID,
                        "user_id": USER.id,
                        "display_name": new_name.strip() or "Você",
                        "role": role
                    }, on_conflict="household_id,user_id").execute()
                    _toast("Nome salvo!")
                    _clear_and_rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar nome: {e}")

        with colB:
            st.write("**Foto do perfil**")
            # caminho convenção: avatars/{household_id}/{member_id}.png
            my_member_id = me.get("id") if me else None
            if my_member_id:
                avatar_path = f"{HOUSEHOLD_ID}/{my_member_id}.png"
                url = _signed_or_public_url("avatars", avatar_path, 3600)
                if url:
                    st.image(url, width=128, caption="Atual")
            file = st.file_uploader("Enviar nova foto (PNG/JPG)", type=["png", "jpg", "jpeg"], key="upload_avatar")
            if file and my_member_id:
                try:
                    content = file.read()
                    # normaliza extensão para png no path final
                    avatar_path = f"{HOUSEHOLD_ID}/{my_member_id}.png"
                    sb.storage.from_("avatars").upload(avatar_path, content, {"content-type": "image/png", "upsert": "true"})
                    _toast("Foto atualizada!")
                    _clear_and_rerun()
                except Exception as e:
                    st.error(f"Falha ao salvar foto: {e}")

    st.markdown("---")

    # --- 1.2 Convites (owner)
    with st.expander("Convidar novo membro (somente owner)", expanded=False):
        if not OWNER:
            st.info("Apenas o **owner** pode enviar convites.")
        else:
            invite_email = st.text_input("E-mail do convidado", key="invite_email").strip()
            invite_name = st.text_input("Nome a exibir (opcional)", key="invite_name").strip()
            colx, coly = st.columns([1,1])
            with colx:
                if st.button("Enviar convite", use_container_width=True, key="btn_send_invite"):
                    if not invite_email:
                        st.warning("Informe um e-mail válido.")
                    else:
                        # tenta RPC invite_member; se não existir, envia e-mail manual
                        called = _safe_rpc("invite_member", {
                            "p_household_id": HOUSEHOLD_ID,
                            "p_email": invite_email,
                            "p_display_name": invite_name or None
                        })
                        if called is not None:
                            _toast("Convite registrado! O convidado receberá instruções por e-mail.")
                        else:
                            # fallback: e-mail manual
                            ok = send_email(
                                [invite_email],
                                subject="Convite - Family Finance",
                                body=(
                                    "Olá!\n\n"
                                    "Você foi convidado para participar do Family Finance.\n"
                                    "Crie sua conta e, após login, aceite o convite pendente.\n\n"
                                    "Abraços!"
                                )
                            )
                            if ok:
                                _toast("Convite enviado por e-mail!")
                            else:
                                st.warning("Não foi possível enviar e-mail neste ambiente. Repasse o convite manualmente.")
            with coly:
                st.caption("Dica: o convidado aparecerá em **Membros** assim que aceitar e concluir o cadastro.")

    st.markdown("---")

    # --- 1.3 Lista de membros
    st.markdown("#### Membros cadastrados")
    mems = fetch_members(sb, HOUSEHOLD_ID) or []
    if not mems:
        st.info("Nenhum membro ainda.")
        return

    df = pd.DataFrame([{
        "Nome": m.get("display_name"),
        "Papel": "Owner" if m.get("role") == "owner" else "Membro",
        "User ID": m.get("user_id"),
    } for m in mems])
    st.dataframe(df, use_container_width=True)

    # Governança de papéis (owner)
    if OWNER:
        with st.expander("Governança de papéis (somente owner)", expanded=False):
            tgt = st.selectbox("Escolha um membro", options=mems, format_func=lambda m: m.get("display_name"))
            new_role = st.selectbox("Novo papel", options=["member", "owner"], index=0)
            if st.button("Atualizar papel", use_container_width=True):
                try:
                    sb.table("members").update({"role": new_role}).eq("id", tgt["id"]).execute()
                    _toast("Papel atualizado!")
                    _clear_and_rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar papel: {e}")

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
                # unicidade por família
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
                        _clear_and_rerun()
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
        with col4:
            st.info("Ativa" if a.get("is_active") else "Inativa")
        with col5:
            lbl = "Desativar" if a.get("is_active") else "Ativar"
            if st.button(lbl, key=f"acc_toggle_{a['id']}"):
                if not OWNER:
                    st.error("Apenas owner pode alterar status.")
                else:
                    try:
                        sb.table("accounts").update({"is_active": not a["is_active"]}).eq("id", a["id"]).execute()
                        _toast("Status atualizado!")
                        _clear_and_rerun()
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
                # Ícone embutido no nome (não altera schema)
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
                        _clear_and_rerun()
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
        with col_closing: closing = st.number_input("Dia de Fechamento (1-28)", min_value=1, max_value=28, value=5)
        with col_due: due = st.number_input("Dia de Vencimento (1-28)", min_value=1, max_value=28, value=15)
        can_save = st.form_submit_button("Salvar Cartão")

        if can_save:
            if not OWNER:
                st.error("Apenas owner pode criar cartões.")
            elif not nm.strip():
                st.error("Informe um nome.")
            elif lim <= 0:
                st.error("Limite deve ser positivo.")
            elif closing == due:
                st.error("Fechamento e vencimento não devem ser iguais.")
            else:
                # unicidade
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
                        _clear_and_rerun()
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
                            _clear_and_rerun()
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
                   "Se quiser vínculos formais, crie essas tabelas no banco.")

    mems = fetch_members(sb, HOUSEHOLD_ID) or []
    accs = fetch_accounts(sb, HOUSEHOLD_ID, active_only=True) or []
    cards = fetch_cards(sb, HOUSEHOLD_ID, active_only=True) or []

    if not mems:
        st.info("Cadastre membros primeiro.")
        return

    member = st.selectbox("Selecione o membro", mems, format_func=lambda m: m.get("display_name"))

    with st.expander("Vincular Contas", expanded=True):
        chosen_accs = st.multiselect(
            "Contas sob responsabilidade de {}".format(member.get("display_name")),
            accs, format_func=lambda a: a.get("name")
        )
        if st.button("Salvar vínculos de contas", use_container_width=True, key="save_link_accounts"):
            if not has_acc_tbl:
                st.warning("Tabela `account_members` ausente. Sem persistência.")
            else:
                try:
                    # estratégia simples: apagar vínculos do membro e recriar
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
            "Cartões sob responsabilidade de {}".format(member.get("display_name")),
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
