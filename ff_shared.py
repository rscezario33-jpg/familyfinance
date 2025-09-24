# ff_shared.py — utilitários compartilhados
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
import os, uuid, smtplib
from email.message import EmailMessage

import pandas as pd
import streamlit as st
from supabase_client import get_supabase

# ============ CSS ============
def inject_css():
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] > div {
      background: #0b2038 !important; color: #f0f6ff !important; padding-top: 0; height: 100%;
    }
    .sidebar-title{color:#e6f0ff;font-weight:700;letter-spacing:.6px;text-transform:uppercase;font-size:.80rem;margin:6px 0 6px 6px;}
    .sidebar-group{border-top:1px solid rgba(255,255,255,.08);margin:10px 0 8px 0;padding-top:8px;}
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span{color:#f0f6ff !important;}
    .stButton>button{border-radius:10px;padding:.55rem .9rem;font-weight:600;border:1px solid #0ea5e9;background:#0ea5e9;color:#fff;}
    .stButton>button:hover{transform:translateY(-1px);background:#0284c7;border-color:#0284c7;}
    .card{background:linear-gradient(180deg,#fff 0%,#f8fafc 100%);border:1px solid #e2e8f0;border-radius:16px;padding:16px 18px;box-shadow:0 6px 20px rgba(0,0,0,.06);margin-bottom:12px;}
    .badge{display:inline-flex;align-items:center;gap:.5rem;background:#eef6ff;color:#0369a1;border:1px solid #bfdbfe;padding:.35rem .6rem;border-radius:999px;font-weight:600;margin:4px 6px 0 0;}
    .badge.red{background:#fff1f2;color:#9f1239;border-color:#fecdd3;} .badge.green{background:#ecfdf5;color:#065f46;border-color:#bbf7d0;}
    .small{font-size:.85rem;opacity:.75;}
    .sidebar-flex{display:flex;flex-direction:column;height:100%;}
    .sidebar-top,.sidebar-bottom{display:flex;flex-direction:column;align-items:center;}
    .sidebar-top{padding:12px 12px 8px;} .sidebar-bottom{padding:8px 12px 14px;}
    </style>
    """, unsafe_allow_html=True)

# ============ Supabase ============
sb = get_supabase()

# ============ Helpers ============
def to_brl(v: float) -> str:
    try: return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def _to_date_safe(s):
    if not s: return None
    try: return datetime.fromisoformat(str(s)).date()
    except:
        from datetime import datetime as dt
        for fmt in ("%Y-%m-%d","%Y-%m-%d %H:%M:%S"):
            try: return dt.strptime(str(s)[:len(fmt)], fmt).date()
            except: pass
    return None

def user():
    sess = sb.auth.get_session()
    return sess.user if sess and sess.user else None

# household bootstrap
@st.cache_data(show_spinner=False)
def bootstrap(user_id: str):
    try: sb.rpc("accept_pending_invite").execute()
    except Exception: pass
    res = sb.rpc("create_household_and_member", {"display_name": "Você"}).execute().data
    return {"household_id": res[0]["household_id"], "member_id": res[0]["member_id"]}

# queries
def fetch_members(hid):
    try:
        return sb.table("members").select("id,display_name,role,user_id,parent_id") \
            .eq("household_id", hid).order("display_name").execute().data
    except Exception: return []

def fetch_categories(hid):
    try:
        return sb.table("categories").select("id,name,kind,icon") \
            .eq("household_id", hid).order("name").execute().data
    except Exception:
        try:
            return sb.table("categories").select("id,name,kind") \
                .eq("household_id", hid).order("name").execute().data
        except Exception: return []

def fetch_accounts(hid, active_only=False):
    q = sb.table("accounts").select("id,name,is_active,type").eq("household_id", hid)
    if active_only: q = q.eq("is_active", True)
    try: data = q.execute().data or []
    except Exception: data = []
    data.sort(key=lambda a:(a.get("name") or "").lower()); return data

def fetch_cards(hid, active_only=True):
    q = sb.table("credit_cards").select("id,household_id,name,limit_amount,closing_day,due_day,is_active,created_by") \
        .eq("household_id", hid)
    if active_only: q = q.eq("is_active", True)
    try: data = q.execute().data or []
    except Exception: data = []
    data.sort(key=lambda c:(c.get("name") or "").lower()); return data

def fetch_card_limits(hid):
    try: data = sb.table("v_card_limit").select("*").eq("household_id", hid).execute().data or []
    except Exception: data = []
    data.sort(key=lambda c:(c.get("name") or "").lower()); return data

def fetch_tx(hid, start: date, end: date):
    try: rows = sb.table("transactions").select("*").eq("household_id", hid).execute().data or []
    except Exception: rows=[]
    out=[]; 
    for t in rows:
        d = _to_date_safe(t.get("occurred_at"))
        if d and start <= d <= end: out.append(t)
    out.sort(key=lambda t: (_to_date_safe(t.get("due_date")) or _to_date_safe(t.get("occurred_at")) or date.min))
    return out

def fetch_tx_due(hid, start: date, end: date):
    try: rows = sb.table("transactions").select("*").eq("household_id", hid).execute().data or []
    except Exception: rows=[]
    out=[]; 
    for t in rows:
        dd = _to_date_safe(t.get("due_date")); od = _to_date_safe(t.get("occurred_at"))
        key = dd or od
        if key and start <= key <= end: out.append(t)
    out.sort(key=lambda t: (_to_date_safe(t.get("due_date")) or _to_date_safe(t.get("occurred_at")) or date.min))
    return out

# ============ E-mail lembretes ============
def _smtp_cfg():
    cfg = getattr(st.secrets, "smtp", None) if hasattr(st, "secrets") else None
    if not cfg: return None
    return {
        "host": cfg.get("host"), "port": int(cfg.get("port", 587)),
        "user": cfg.get("user"), "password": cfg.get("password"),
        "from_email": cfg.get("from_email", cfg.get("user")),
        "use_tls": bool(cfg.get("use_tls", True)),
    }

def send_email(to_emails: List[str], subject: str, body: str):
    smtp = _smtp_cfg()
    if not smtp: return False
    try:
        msg = EmailMessage(); msg["Subject"]=subject; msg["From"]=smtp["from_email"]; msg["To"]=",".join(to_emails)
        msg.set_content(body)
        with smtplib.SMTP(smtp["host"], smtp["port"]) as s:
            if smtp["use_tls"]: s.starttls()
            if smtp["user"]: s.login(smtp["user"], smtp["password"])
            s.send_message(msg)
        return True
    except Exception: return False

@st.cache_data(show_spinner=False)
def _today_str(): return date.today().isoformat()

def notify_due_bills(hid, uemail):
    key = f"__notified__{_today_str()}"
    if st.session_state.get(key): return
    try:
        start=date.today(); end=date.today()+timedelta(days=3)
        txs = fetch_tx_due(hid, start, end)
        pend=[t for t in txs if (t.get("type")=="expense" and not t.get("is_paid"))]
        if not pend or not uemail: 
            st.session_state[key]=True; return
        lines=[]
        for t in pend:
            due = _to_date_safe(t.get("due_date")) or _to_date_safe(t.get("occurred_at"))
            val = t.get("planned_amount") or t.get("amount") or 0.0
            lines.append(f"- {t.get('description','(sem descrição)')} — {due.strftime('%d/%m/%Y')} — {to_brl(val)}")
        send_email([uemail], "Lembrete: contas a vencer", "Olá!\n\n"+"\n".join(lines)+"\n\n— Family Finance")
    finally:
        st.session_state[key]=True

# ============ Sidebar padrão (logos topo/rodapé + sair) ============
def sidebar_shell(show_logout=True):
    st.markdown('<div class="sidebar-flex">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-top">', unsafe_allow_html=True)
    st.image("assets/logo_family_finance.png", width=110)
    st.markdown('</div><div class="sidebar-group"></div>', unsafe_allow_html=True)
    if show_logout and st.button("Sair"):
        sb.auth.sign_out(); st.session_state.clear()
        try: st.switch_page("app.py")
        except Exception: st.experimental_rerun()
    st.markdown('<div class="sidebar-bottom">', unsafe_allow_html=True)
    st.markdown('<div class="small" style="text-align:center;opacity:.9;">Powered by</div>', unsafe_allow_html=True)
    st.image("assets/logo_automaGO.png", width=80)
    st.markdown('</div></div>', unsafe_allow_html=True)
