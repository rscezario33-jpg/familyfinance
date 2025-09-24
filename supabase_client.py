# supabase_client.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import socket
import streamlit as st
from typing import Optional, Tuple
from supabase import create_client, Client


class FFConfigError(RuntimeError):
    pass


def _read_creds() -> Tuple[str, str]:
    """
    Lê credenciais do Supabase a partir de:
      1) st.secrets['supabase'] -> aceita 'key' OU 'anon_key'
      2) Variáveis de ambiente SUPABASE_URL / SUPABASE_KEY (fallback)
    """
    url: Optional[str] = None
    key: Optional[str] = None

    # 1) st.secrets
    try:
        sect = st.secrets["supabase"]  # type: ignore[index]
        # aceita 'key' ou 'anon_key'
        url = sect.get("url") if isinstance(sect, dict) else None  # type: ignore[attr-defined]
        key = (sect.get("key") or sect.get("anon_key")) if isinstance(sect, dict) else None  # type: ignore[attr-defined]
    except Exception:
        pass

    # 2) Fallback: env vars
    if not url:
        url = os.getenv("SUPABASE_URL")
    if not key:
        key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise FFConfigError(
            "Credenciais do Supabase ausentes. Defina em st.secrets['supabase'] "
            "(url + key/anon_key) ou nas variáveis de ambiente SUPABASE_URL e SUPABASE_KEY."
        )
    return str(url).strip(), str(key).strip()


def _sanitize_url(url: str) -> str:
    u = url.strip()
    if not u.startswith("https://"):
        raise FFConfigError("A URL do Supabase deve iniciar com https://")
    host = re.sub(r"^https://", "", u).split("/")[0]
    if "." not in host:
        raise FFConfigError(f"URL inválida (host sem ponto): {u}")
    return u


def _validate_dns(url: str) -> None:
    host = re.sub(r"^https://", "", url).split("/")[0]
    try:
        socket.getaddrinfo(host, 443)
    except socket.gaierror as e:
        raise FFConfigError(f"Falha de DNS para {host}: {e}")


@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    """
    Retorna um client do Supabase com cache por sessão.
    Lê st.secrets (key/anon_key) ou variáveis de ambiente e valida URL/DNS.
    """
    url, key = _read_creds()
    url = _sanitize_url(url)
    _validate_dns(url)
    client: Client = create_client(url, key)
    return client
