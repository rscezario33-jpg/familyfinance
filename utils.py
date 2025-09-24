# utils.py
from __future__ import annotations
from datetime import date, datetime, timedelta
import uuid
import io
import os
import smtplib
from email.message import EmailMessage
from typing import List, Optional
import pandas as pd
import streamlit as st
from supabase import Client  # IMPORTANTE para hash_funcs

# Assumimos que 'sb' e 'user' serão passados ou acessíveis via st.session_state

def to_brl(v: float) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def _to_date_safe(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s)).date()
    except Exception:
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(str(s)[:len(fmt)], fmt).date()
            except Exception:
                pass
        return None

def _safe_table(sb, HOUSEHOLD_ID, name: str):
    """
    Busca dados de uma tabela com tratamento de erro e filtro por household_id.
    Assume que sb e HOUSEHOLD_ID são passados.
    """
    try:
        return sb.table(name).select("*").eq("household_id", HOUSEHOLD_ID).execute().data or []
    except Exception as e:
        # st.error(f"Erro ao buscar tabela '{name}' via _safe_table: {e}")  # debug opcional
        return []

# --- Fetchers de Dados ---
# Todas as funções fetcher precisarão de 'sb' e 'HOUSEHOLD_ID'

@st.cache_data(ttl=600, hash_funcs={Client: lambda _: None})
def fetch_members(sb, HOUSEHOLD_ID):
    try:
        # inclui user_id para mapeamentos usuário↔membro
        return (
            sb.table("members")
              .select("id,display_name,role,user_id")
              .eq("household_id", HOUSEHOLD_ID)
              .order("display_name")
              .execute()
              .data
        )
    except Exception as e:
        st.error(f"Erro ao buscar membros: {e}")
        return _safe_table(sb, HOUSEHOLD_ID, "members")

@st.cache_data(ttl=600, hash_funcs={Client: lambda _: None})
def fetch_categories(sb, HOUSEHOLD_ID):
    try:
        return (
            sb.table("categories")
              .select("id,name,kind")
              .eq("household_id", HOUSEHOLD_ID)
              .order("name")
              .execute()
              .data
        )
    except Exception as e:
        st.error(f"Erro ao buscar categorias: {e}")
        return _safe_table(sb, HOUSEHOLD_ID, "categories")

@st.cache_data(ttl=600, hash_funcs={Client: lambda _: None})
def fetch_accounts(sb, HOUSEHOLD_ID, active_only=False):
    q = (
        sb.table("accounts")
          .select("id,name,is_active,type,opening_balance")
          .eq("household_id", HOUSEHOLD_ID)
    )
    if active_only:
        q = q.eq("is_active", True)
    try:
        data = q.execute().data or []
    except Exception as e:
        st.error(f"Erro ao buscar contas: {e}")
        data = _safe_table(sb, HOUSEHOLD_ID, "accounts")
    data.sort(key=lambda a: (a.get("name") or "").lower())
    return data

@st.cache_data(ttl=600, hash_funcs={Client: lambda _: None})
def fetch_cards(sb, HOUSEHOLD_ID, active_only=True):
    q = (
        sb.table("credit_cards")
          .select("id,household_id,name,limit_amount,closing_day,due_day,is_active,created_by")
          .eq("household_id", HOUSEHOLD_ID)
    )
    if active_only:
        q = q.eq("is_active", True)
    try:
        data = q.execute().data or []
    except Exception as e:
        st.error(f"Erro ao buscar cartões: {e}")
        data = _safe_table(sb, HOUSEHOLD_ID, "credit_cards")
    data.sort(key=lambda c: (c.get("name") or "").lower())
    return data

@st.cache_data(ttl=600, hash_funcs={Client: lambda _: None})
def fetch_card_limits(sb, HOUSEHOLD_ID):
    try:
        data = (
            sb.table("v_card_limit")
              .select("*")
              .eq("household_id", HOUSEHOLD_ID)
              .execute()
              .data
            or []
        )
    except Exception as e:
        st.error(f"Erro ao buscar limites de cartão: {e}")
        data = []  # views não têm fallback _safe_table
    data.sort(key=lambda c: (c.get("name") or "").lower())
    return data

# ========= MELHORIA: filtrar no banco com fallback local =========

@st.cache_data(ttl=600, hash_funcs={Client: lambda _: None})
def fetch_tx(sb, HOUSEHOLD_ID, start: date, end: date):
    """
    Busca transações pelo occurred_at no intervalo [start, end].
    Tenta filtrar no banco (performático). Se falhar, cai no fallback local.
    """
    try:
        data = (
            sb.table("transactions")
              .select("*")
              .eq("household_id", HOUSEHOLD_ID)
              .gte("occurred_at", start.isoformat())
              .lte("occurred_at", end.isoformat())
              .order("occurred_at", desc=False)
              .execute()
              .data
            or []
        )
        return data
    except Exception:
        # Fallback local (comportamento antigo)
        rows = _safe_table(sb, HOUSEHOLD_ID, "transactions")
        out = []
        for t in rows:
            d = _to_date_safe(t.get("occurred_at"))
            if d and start <= d <= end:
                out.append(t)
        out.sort(key=lambda t: (_to_date_safe(t.get("occurred_at")) or date.min))
        return out

@st.cache_data(ttl=600, hash_funcs={Client: lambda _: None})
def fetch_tx_due(sb, HOUSEHOLD_ID, start: date, end: date):
    """
    Busca transações por data de vencimento. Regra:
      - Se due_date não for NULL: usa due_date no intervalo.
      - Se due_date for NULL: usa occurred_at no intervalo (mesma lógica antiga).
    Implementado com duas consultas (sem exigir view); mantém fallback local.
    """
    try:
        # 1) Com due_date no intervalo
        with_due = (
            sb.table("transactions")
              .select("*")
              .eq("household_id", HOUSEHOLD_ID)
              .gte("due_date", start.isoformat())
              .lte("due_date", end.isoformat())
              .order("due_date", desc=False)
              .execute()
              .data
            or []
        )
        # 2) Sem due_date (NULL): considerar occurred_at no intervalo
        without_due = (
            sb.table("transactions")
              .select("*")
              .eq("household_id", HOUSEHOLD_ID)
              .is_("due_date", "null")
              .gte("occurred_at", start.isoformat())
              .lte("occurred_at", end.isoformat())
              .order("occurred_at", desc=False)
              .execute()
              .data
            or []
        )
        data = with_due + without_due
        # Ordena pelo mesmo critério utilizado anteriormente (due_date ou occurred_at)
        data.sort(
            key=lambda t: (_to_date_safe(t.get("due_date")) or _to_date_safe(t.get("occurred_at")) or date.min)
        )
        return data
    except Exception:
        # Fallback local (comportamento antigo)
        rows = _safe_table(sb, HOUSEHOLD_ID, "transactions")
        out = []
        for t in rows:
            dd = _to_date_safe(t.get("due_date"))
            od = _to_date_safe(t.get("occurred_at"))
            key = dd or od
            if key and start <= key <= end:
                out.append(t)
        out.sort(key=lambda t: (_to_date_safe(t.get("due_date")) or _to_date_safe(t.get("occurred_at")) or date.min))
        return out

# --- SMTP (opcional) ---
def _smtp_cfg():
    cfg = getattr(st.secrets, "smtp", None)
    if hasattr(st, "secrets") and st.secrets and "smtp" in st.secrets:
        cfg = st.secrets["smtp"]
    else:
        return None  # Nenhuma configuração SMTP encontrada

    if not cfg:
        return None
    return {
        "host": cfg.get("host"),
        "port": int(cfg.get("port", 587)),
        "user": cfg.get("user"),
        "password": cfg.get("password"),
        "from_email": cfg.get("from_email", cfg.get("user")),
        "use_tls": bool(cfg.get("use_tls", True)),
    }

def send_email(to_emails: List[str], subject: str, body: str, attach_name: Optional[str]=None, attach_bytes: Optional[bytes]=None):
    smtp = _smtp_cfg()
    if not smtp:
        # silencioso: sem SMTP configurado
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp["from_email"]
        msg["To"] = ", ".join(to_emails)
        msg.set_content(body)
        if attach_bytes and attach_name:
            msg.add_attachment(attach_bytes, maintype="application", subtype="octet-stream", filename=attach_name)
        with smtplib.SMTP(smtp["host"], smtp["port"]) as s:
            if smtp["use_tls"]:
                s.starttls()
            if smtp["user"]:
                s.login(smtp["user"], smtp["password"])
            s.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Falha ao enviar e-mail: {e}")
        return False

@st.cache_data(show_spinner=False)
def _today_str():
    return date.today().isoformat()

def notify_due_bills(sb, HOUSEHOLD_ID, user):
    key = f"__notified__{_today_str()}"
    if st.session_state.get(key):
        return

    try:
        start = date.today()
        end = date.today() + timedelta(days=3)
        txs = fetch_tx_due(sb, HOUSEHOLD_ID, start, end)

        if not txs:
            st.session_state[key] = True
            return

        # filtra despesas não pagas
        pend = [t for t in txs if (t.get("type") == "expense" and not t.get("is_paid"))]
        if not pend:
            st.session_state[key] = True
            return

        to = [user.email] if user and getattr(user, "email", None) else []
        if not to:
            st.session_state[key] = True
            return

        lines = []
        for t in pend:
            due = _to_date_safe(t.get("due_date")) or _to_date_safe(t.get("occurred_at"))
            val = t.get("planned_amount") or t.get("amount") or 0.0
            lines.append(f"- {t.get('description','(sem descrição)')} — vence em {due.strftime('%d/%m/%Y')} — {to_brl(val)}")

        if lines:
            subject = "Lembrete: contas a vencer (3 dias / hoje)"
            body = "Olá!\n\nAs seguintes contas vencem em até 3 dias (ou hoje):\n\n" + "\n".join(lines) + "\n\n— Family Finance"
            send_email(to, subject, body)
    finally:
        st.session_state[key] = True
