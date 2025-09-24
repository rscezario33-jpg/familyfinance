# pages/🧰_Administracao.py
from __future__ import annotations
from datetime import date
import io
from typing import Optional, Tuple

import streamlit as st

# tenta usar AG-Grid; se não existir, cai no fallback
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
    HAS_AGGRID = True
except Exception:
    HAS_AGGRID = False

# utils do seu projeto
from utils import (
    to_brl,
    fetch_members,
    fetch_accounts,
    fetch_categories,
    fetch_cards,
    fetch_card_limits,
)

# =========================
# Gate de autenticação
# =========================
if "sb" not in st.session_state or "HOUSEHOLD_ID" not in st.session_state or "user" not in st.session_state:
    st.warning("🔒 Por favor, faça login na página principal para acessar a administração.")
    st.stop()

sb = st.session_state.sb
HOUSEHOLD_ID = st.session_state.HOUSEHOLD_ID
user = st.session_state.user

st.title("🧰 Administração do Sistema Financeiro")

# =========================
# Helpers de UI / persistência
# =========================
def toast_ok(msg: str): st.toast(msg, icon="✅")
def toast_warn(msg: str): st.toast(msg, icon="⚠️")
def toast_err(msg: str): st.toast(msg, icon="❌")

def clear_and_refresh_soft():
    """Atualiza dados limpando apenas cache; evita st.rerun() para não voltar à primeira aba."""
    try:
        st.cache_data.clear()
    except Exception:
        pass

# ---- NOVO: detecção de imagem sem imghdr (compatível com Py 3.13)
def sniff_image_mime(file_bytes: bytes, declared_mime: Optional[str] = None) -> Tuple[str, str]:
    """
    Retorna (mime, ext) baseado no header do arquivo e/ou MIME informado pelo navegador.
    Suporta png/jpg/jpeg/webp; fallback para PNG.
    """
    # 1) se o navegador informou um MIME confiável, use
    if declared_mime in ("image/png", "image/jpeg", "image/webp"):
        if declared_mime == "image/png":
            return "image/png", "png"
        if declared_mime == "image/jpeg":
            return "image/jpeg", "jpg"
        if declared_mime == "image/webp":
            return "image/webp", "webp"

    # 2) inspeção do header
    sig = file_bytes[:12]
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if sig.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    # JPEG: FF D8 FF
    if sig.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    # WEBP: RIFF....WEBP
    if sig[:4] == b"RIFF" and sig[8:12] == b"WEBP":
        return "image/webp", "webp"

    # 3) fallback seguro
    return "image/png", "png"

def ensure_avatars_bucket() -> None:
    """Garante existência do bucket 'avatars' (público); ignora erro de 'já existe'."""
    try:
        sb.storage.create_bucket("avatars", {"public": True})
    except Exception:
        pass  # já existe

# =========================
# Abas
# =========================
tabs = st.tabs(["👥 Membros", "💰 Contas", "🏷️ Categorias", "💳 Cartões", "🔗 Vínculos"])

# -------------------------
# 👥 Membros
# -------------------------
with tabs[0]:
    st.subheader("Gestão de Membros")

    # 1) Definir/alterar nome de exibição do usuário atual
    with st.form("form_member_name", clear_on_submit=False):
        mems = fetch_members(sb, HOUSEHOLD_ID) or []
        current_name = "Você"
        my_member = None
        for m in mems:
            if m.get("user_id") == getattr(user, "id", None):
                current_name = m.get("display_name") or current_name
                my_member = m
                break

        new_display = st.text_input("Seu nome de exibição", value=current_name)
        col_a, col_b = st.columns([1, 1])

        # 2) Upload de foto do membro (avatar)
        with col_a:
            avatar_file = st.file_uploader(
                "Foto (png/jpg/webp)",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=False,
                help="Imagem do seu perfil para usar nos dashboards.",
                key="member_avatar_uploader",
            )
        with col_b:
            st.write("")  # espaçamento

        submitted = st.form_submit_button("Salvar")

        if submitted:
            if not new_display.strip():
                st.error("Informe um nome válido.")
            else:
                # upsert do membro
                try:
                    sb.table("members").upsert(
                        {
                            "household_id": HOUSEHOLD_ID,
                            "user_id": user.id,
                            "display_name": new_display.strip(),
                            "role": my_member["role"] if my_member else "owner",
                        },
                        on_conflict="household_id,user_id",
                    ).execute()
                except Exception as e:
                    st.error(f"Erro ao salvar nome: {e}")
                else:
                    # upload do avatar se houver
                    if avatar_file is not None:
                        try:
                            ensure_avatars_bucket()
                            file_bytes = avatar_file.read()
                            mime, ext = sniff_image_mime(file_bytes, getattr(avatar_file, "type", None))
                            path = f"{HOUSEHOLD_ID}/{user.id}.{ext}"
                            sb.storage.from_("avatars").upload(
                                path=path,
                                file=io.BytesIO(file_bytes),
                                file_options={"content-type": mime, "upsert": True},
                            )
                            toast_ok("Foto enviada com sucesso.")
                        except Exception as e:
                            st.error(f"Falha ao salvar foto: {e}")

                    toast_ok("Membro atualizado.")
                    clear_and_refresh_soft()

    st.markdown("---")

    # 3) Convidar novo membro (via Edge Function SendGrid)
    st.markdown("#### Convidar pessoa para o agregado")
    with st.form("form_invite_member", clear_on_submit=True):
        invite_email = st.text_input("E-mail do convidado")
        invite_name = st.text_input("Nome do convidado (opcional)")
        col_i1, col_i2 = st.columns([1, 2])
        with col_i1:
            send_btn = st.form_submit_button("Enviar convite ✉️")

        if send_btn:
            if not invite_email or "@" not in invite_email:
                st.error("Informe um e-mail válido.")
            else:
                try:
                    resp = sb.functions.invoke(
                        "send-invite",
                        body={
                            "household_id": HOUSEHOLD_ID,
                            "email": invite_email.strip(),
                            "display_name": (invite_name or "").strip() or None,
                            "invited_by": user.id,
                            "app_url": "https://familyfinance.streamlit.app",
                        },
                    )
                    data = getattr(resp, "data", {}) or {}
                    if data.get("ok") and data.get("email_sent"):
                        toast_ok("Convite enviado! Peça para o convidado verificar a caixa de entrada/spam.")
                    else:
                        st.error(f"Falha ao enviar convite: {data or resp}")
                except Exception as e:
                    st.error(f"Erro ao chamar função de convite: {e}")

    st.markdown("---")
    st.markdown("#### Membros cadastrados")

    mems = fetch_members(sb, HOUSEHOLD_ID) or []
    if not mems:
        st.info("Nenhum membro cadastrado ainda.")
    else:
        if HAS_AGGRID:
            import pandas as pd
            df = pd.DataFrame(mems)[["display_name", "role", "user_id", "id"]]
            df.rename(
                columns={
                    "display_name": "Nome",
                    "role": "Papel",
                    "user_id": "Usuário (auth)",
                    "id": "ID membro",
                },
                inplace=True,
            )
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_selection("single", use_checkbox=True)
            gb.configure_grid_options(domLayout="autoHeight")
            gb.configure_default_column(editable=True)
            grid = AgGrid(
                df,
                gridOptions=gb.build(),
                update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.VALUE_CHANGED,
                height=350,
                fit_columns_on_grid_load=True,
                theme="alpine",
            )

            col_left, col_right = st.columns([1, 3])
            with col_left:
                if st.button("Salvar edição"):
                    try:
                        sel = grid["selected_rows"]
                        if sel:
                            row = sel[0]
                            sb.table("members").update(
                                {"display_name": row["Nome"], "role": row["Papel"]}
                            ).eq("id", row["ID membro"]).execute()
                            toast_ok("Membro atualizado.")
                            clear_and_refresh_soft()
                        else:
                            toast_warn("Selecione uma linha para editar.")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
                if st.button("Excluir selecionado"):
                    try:
                        sel = grid["selected_rows"]
                        if sel:
                            row = sel[0]
                            sb.table("members").delete().eq("id", row["ID membro"]).execute()
                            toast_ok("Membro excluído.")
                            clear_and_refresh_soft()
                        else:
                            toast_warn("Selecione uma linha para excluir.")
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")
        else:
            # Fallback simples
            for m in mems:
                st.write(f"• **{m['display_name']}** — {m['role']}")

# -------------------------
# 💰 Contas
# -------------------------
with tabs[1]:
    st.subheader("Gestão de Contas")

    with st.form("form_new_account", clear_on_submit=True):
        an = st.text_input("Nome da conta")
        at = st.selectbox(
            "Tipo de conta",
            ["checking", "savings", "wallet", "credit"],
            format_func=lambda x: x.capitalize(),
        )
        ob = st.number_input("Saldo inicial (R$)", min_value=0.0, step=50.0, value=0.0)
        ok = st.form_submit_button("Salvar conta")
        if ok:
            if not an.strip():
                st.error("Informe um nome para a conta.")
            else:
                try:
                    sb.table("accounts").insert(
                        {
                            "household_id": HOUSEHOLD_ID,
                            "name": an.strip(),
                            "type": at,
                            "opening_balance": ob,
                            "currency": "BRL",
                            "is_active": True,
                        }
                    ).execute()
                    toast_ok("Conta salva.")
                    clear_and_refresh_soft()
                except Exception as e:
                    st.error(f"Erro ao salvar conta: {e}")

    st.markdown("#### Suas contas")
    accs = fetch_accounts(sb, HOUSEHOLD_ID, include_inactive=True) or []
    if not accs:
        st.info("Nenhuma conta cadastrada.")
    else:
        for a in accs:
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            with col1:
                st.markdown(f"{'🟢' if a['is_active'] else '🔴'} **{a['name']}**")
            with col2:
                st.write(f"Tipo: {a.get('type','').capitalize()}")
            with col3:
                st.write(f"Saldo inicial: {to_brl(a['opening_balance'])}")
            with col4:
                st.info("Ativa" if a["is_active"] else "Inativa")
            with col5:
                if st.button("Desativar" if a["is_active"] else "Ativar", key=f"acc_tgl_{a['id']}"):
                    try:
                        sb.table("accounts").update({"is_active": not a["is_active"]}).eq("id", a["id"]).execute()
                        toast_ok("Status atualizado.")
                        clear_and_refresh_soft()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")

# -------------------------
# 🏷️ Categorias
# -------------------------
with tabs[2]:
    st.subheader("Gestão de Categorias")
    st.caption("Dica: escolha um ícone/emoji para facilitar a leitura nos dashboards (ex.: 💡, 🛒, 🚗).")

    with st.form("form_new_category", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            cn = st.text_input("Nome da categoria (sem emoji)")
        with c2:
            ck = st.selectbox("Tipo", ["income", "expense"], format_func=lambda k: {"income": "Receita", "expense": "Despesa"}[k])
        with c3:
            emoji = st.text_input("Ícone/emoji", value="🏷️", max_chars=3, help="Cole um emoji aqui (ex.: 🛒)")
        ok = st.form_submit_button("Salvar categoria")
        if ok:
            base = cn.strip()
            if not base:
                st.error("Informe um nome.")
            else:
                try:
                    name_final = f"{emoji.strip()} {base}" if emoji.strip() else base
                    sb.table("categories").insert(
                        {"household_id": HOUSEHOLD_ID, "name": name_final, "kind": ck}
                    ).execute()
                    toast_ok("Categoria salva.")
                    clear_and_refresh_soft()
                except Exception as e:
                    st.error(f"Erro ao salvar categoria: {e}")

    st.markdown("#### Suas categorias")
    cats = fetch_categories(sb, HOUSEHOLD_ID) or []
    if not cats:
        st.info("Nenhuma categoria cadastrada.")
    else:
        col_inc, col_exp = st.columns(2)
        with col_inc:
            st.markdown("##### ➕ Receitas")
            inc = [c["name"] for c in cats if c["kind"] == "income"]
            if inc:
                for n in inc: st.success(f"• **{n}**")
            else:
                st.info("Nenhuma categoria de receita.")
        with col_exp:
            st.markdown("##### ➖ Despesas")
            exp = [c["name"] for c in cats if c["kind"] == "expense"]
            if exp:
                for n in exp: st.warning(f"• **{n}**")
            else:
                st.info("Nenhuma categoria de despesa.")

# -------------------------
# 💳 Cartões
# -------------------------
with tabs[3]:
    st.subheader("Gestão de Cartões de Crédito")

    with st.form("form_new_card", clear_on_submit=True):
        col_nm, col_lim, col_closing, col_due = st.columns(4)
        with col_nm:
            nm = st.text_input("Nome do cartão")
        with col_lim:
            lim = st.number_input("Limite (R$)", min_value=0.0, step=100.0, value=0.0)
        with col_closing:
            closing = st.number_input("Fechamento (1-31)", min_value=1, max_value=31, value=5)
        with col_due:
            due = st.number_input("Vencimento (1-31)", min_value=1, max_value=31, value=15)

        ok = st.form_submit_button("Salvar cartão")
        if ok:
            if not nm.strip():
                st.error("Informe um nome.")
            elif lim <= 0:
                st.error("Limite deve ser positivo.")
            else:
                try:
                    sb.table("credit_cards").insert(
                        {
                            "household_id": HOUSEHOLD_ID,
                            "name": nm.strip(),
                            "limit_amount": lim,
                            "closing_day": int(closing),
                            "due_day": int(due),
                            "is_active": True,
                            "created_by": user.id,
                        }
                    ).execute()
                    toast_ok("Cartão salvo.")
                    clear_and_refresh_soft()
                except Exception as e:
                    st.error(f"Erro ao salvar cartão: {e}")

    st.markdown("#### Seus cartões")
    cards_all = fetch_cards(sb, HOUSEHOLD_ID, include_inactive=True) or []
    limits = fetch_card_limits(sb, HOUSEHOLD_ID) or []
    limap = {x["id"]: x for x in limits}

    if not cards_all:
        st.info("Nenhum cartão cadastrado.")
    else:
        for c in cards_all:
            available_limit = limap.get(c["id"], {}).get("available_limit", c["limit_amount"])
            with st.container(border=True):
                colA, colB, colC, colD, colE = st.columns([3, 2, 2, 2, 1])
                with colA:
                    st.markdown(f"{'🟢' if c['is_active'] else '🔴'} **{c['name']}**")
                with colB:
                    st.write(f"Limite: {to_brl(c['limit_amount'])}")
                with colC:
                    st.write(f"Disponível: {to_brl(available_limit)}")
                with colD:
                    st.info(f"Fecha {c['closing_day']} • Vence {c['due_day']}")
                with colE:
                    if st.button("Desativar" if c["is_active"] else "Ativar", key=f"card_tgl_{c['id']}"):
                        try:
                            sb.table("credit_cards").update({"is_active": not c["is_active"]}).eq("id", c["id"]).execute()
                            toast_ok("Status atualizado.")
                            clear_and_refresh_soft()
                        except Exception as e:
                            st.error(f"Erro ao atualizar cartão: {e}")

# -------------------------
# 🔗 Vínculos (conta/cartão ↔ membro)
# -------------------------
with tabs[4]:
    st.subheader("Vínculo de Contas e Cartões a Membros")
    st.caption("Opcional. Lançamentos já permitem escolher o member_id. Crie as tabelas para persistir vínculos formais.")

    # tenta carregar vínculos; se as tabelas não existirem, apenas informa
    try:
        sb.table("account_members").select("id").limit(1).execute()
        has_acc_tbl = True
    except Exception:
        has_acc_tbl = False

    try:
        sb.table("card_members").select("id").limit(1).execute()
        has_card_tbl = True
    except Exception:
        has_card_tbl = False

    if not (has_acc_tbl or has_card_tbl):
        st.info("Tabelas de vínculo não foram encontradas (account_members, card_members). "
                "Os lançamentos ainda podem atribuir member_id normalmente. "
                "Se quiser vínculos formais, crie essas tabelas no banco.")
        st.stop()

    mems = fetch_members(sb, HOUSEHOLD_ID) or []
    accs = fetch_accounts(sb, HOUSEHOLD_ID, include_inactive=False) or []
    cards = fetch_cards(sb, HOUSEHOLD_ID, include_inactive=False) or []

    member_map = {m["display_name"]: m["id"] for m in mems}
    acc_map = {a["name"]: a["id"] for a in accs}
    card_map = {c["name"]: c["id"] for c in cards}

    col_v1, col_v2 = st.columns(2)

    with col_v1:
        st.markdown("##### Vínculo de Conta → Membro")
        v_mem = st.selectbox("Membro", list(member_map.keys())) if mems else None
        v_acc = st.selectbox("Conta", list(acc_map.keys())) if accs else None
        if st.button("Vincular conta"):
            if not has_acc_tbl:
                st.warning("Tabela account_members ausente. Sem persistência.")
            elif v_mem and v_acc:
                try:
                    sb.table("account_members").upsert(
                        {"household_id": HOUSEHOLD_ID, "member_id": member_map[v_mem], "account_id": acc_map[v_acc]},
                        on_conflict="household_id,member_id,account_id",
                    ).execute()
                    toast_ok("Vínculo conta↔membro salvo.")
                except Exception as e:
                    st.error(f"Erro ao vincular conta: {e}")

    with col_v2:
        st.markdown("##### Vínculo de Cartão → Membro")
        v_mem2 = st.selectbox("Membro ", list(member_map.keys()), key="vm2") if mems else None
        v_card = st.selectbox("Cartão", list(card_map.keys())) if cards else None
        if st.button("Vincular cartão"):
            if not has_card_tbl:
                st.warning("Tabela card_members ausente. Sem persistência.")
            elif v_mem2 and v_card:
                try:
                    sb.table("card_members").upsert(
                        {"household_id": HOUSEHOLD_ID, "member_id": member_map[v_mem2], "card_id": card_map[v_card]},
                        on_conflict="household_id,member_id,card_id",
                    ).execute()
                    toast_ok("Vínculo cartão↔membro salvo.")
                except Exception as e:
                    st.error(f"Erro ao vincular cartão: {e}")
