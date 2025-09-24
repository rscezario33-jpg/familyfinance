# ff_shared.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict
import streamlit as st
from supabase_client import get_supabase


def bootstrap(user_id: str) -> Dict[str, str]:
    """
    Garante uma household e um member padrão para o usuário.
    É idempotente: se já existir, reutiliza. Retorna e grava na sessão.
    """
    s = get_supabase()

    # 1) Household do usuário (owner_id)
    hh = s.table("households").select("id").eq("owner_id", user_id).limit(1).execute()
    if hh.data:
        household_id = hh.data[0]["id"]
    else:
        new_hh = s.table("households").insert({"owner_id": user_id, "name": "Minha Família"}).execute()
        household_id = new_hh.data[0]["id"]

    # 2) Member vinculado a essa household
    mb = (
        s.table("members")
        .select("id")
        .eq("user_id", user_id)
        .eq("household_id", household_id)
        .limit(1)
        .execute()
    )
    if mb.data:
        member_id = mb.data[0]["id"]
    else:
        new_mb = (
            s.table("members")
            .insert({"user_id": user_id, "household_id": household_id, "name": "Eu"})
            .execute()
        )
        member_id = new_mb.data[0]["id"]

    st.session_state["household_id"] = household_id
    st.session_state["member_id"] = member_id

    return {"household_id": household_id, "member_id": member_id}


def require_session_ids() -> tuple[str, str]:
    """
    Em páginas internas, garanta que household_id e member_id existam.
    """
    hid = st.session_state.get("household_id")
    mid = st.session_state.get("member_id")
    if not hid or not mid:
        st.error("Sessão inválida. Faça login novamente.")
        st.stop()
    return hid, mid
