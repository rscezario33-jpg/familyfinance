# pages/1_Entrada.py — Entrada
from datetime import date
import pandas as pd
import streamlit as st
from ff_shared import inject_css, sidebar_shell, user, bootstrap, fetch_tx, fetch_members, to_brl, notify_due_bills

st.set_page_config(page_title="Family Finance — Entrada", layout="wide")
inject_css()

u = user()
if not u:
    st.switch_page("app.py")
hid_mid = bootstrap(u.id); HOUSEHOLD_ID = hid_mid["household_id"]

with st.sidebar: sidebar_shell()

st.title("Family Finance — Entrada")

first_day = date.today().replace(day=1)
txm = fetch_tx(HOUSEHOLD_ID, first_day, date.today())
res = sum([(t.get("paid_amount") if t.get("is_paid") else t.get("planned_amount") or t.get("amount") or 0)
           * (1 if t.get("type")=="income" else -1) for t in txm]) if txm else 0

c1,c2,c3 = st.columns(3)
with c1: st.metric("Período", f"{first_day.strftime('%d/%m')}—{date.today().strftime('%d/%m')}")
with c2: st.metric("Lançamentos", len(txm))
with c3: st.metric("Resultado (previsto)", to_brl(res))

st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("Visão por membro (mês)")
mems = fetch_members(HOUSEHOLD_ID); mem_map = {m["id"]: m["display_name"] for m in mems}
if txm:
    df = pd.DataFrame(txm)
    df["valor_eff"] = df.apply(lambda r: (r.get("paid_amount") if r.get("is_paid") else r.get("planned_amount") or r.get("amount") or 0)
                                         * (1 if r.get("type")=="income" else -1), axis=1)
    df["Membro"] = df["member_id"].map(mem_map).fillna("—")
    st.bar_chart(df.groupby("Membro")["valor_eff"].sum().reset_index(), x="Membro", y="valor_eff")
else:
    st.info("Sem lançamentos no mês.")
st.markdown('</div>', unsafe_allow_html=True)

# lembretes
notify_due_bills(HOUSEHOLD_ID, u.email)

