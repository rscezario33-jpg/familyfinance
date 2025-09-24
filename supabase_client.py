# supabase_client.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import socket
import streamlit as st
from typing import Optional
from supabase import create_client, Client


def _read_secrets() -> tuple[str, str]:
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
    except Exception:
        raise RuntimeError(
            "Configure st.secrets['supabase']['url'] e ['key'] com as credenciais do Supabase."
        )
    return str(url).strip(), str(key).strip()


def _sanitize_url(url: str) -> str:
    u = url.strip()
    if not u.startswith("https://"):
        raise ValueError("A URL do Supabase deve iniciar com https://")
    return u


def _validate_dns(url: str) -> None:
    host = re.sub(r"^https://", "", url).split("/")[0]
    try:
        socket.getaddrinfo(host, 443)
    except socket.gaierror as e:
        raise RuntimeError(f"Falha de DNS para {host}: {e}")


@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    """
    Retorna um client do Supabase com cache (um por sessão),
    validando URL/KEY e DNS. Evita múltiplas instâncias e melhora estabilidade.
    """
    url, key = _read_secrets()
    url = _sanitize_url(url)
    _validate_dns(url)
    client: Client = create_client(url, key)
    return client
