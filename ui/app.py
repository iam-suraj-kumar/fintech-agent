import os
import sys

# streamlit puts the script's own directory (ui/) on sys.path, not the
# project root, so imports below would fail without this regardless of cwd.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from data.synthetic_transactions import SCENARIOS
from graph import graph
from ui.logic import get_decision_history, get_pending_reviews, resume_transaction, start_transaction

st.set_page_config(page_title="Fraud Guard", layout="wide", page_icon="🛡️")

DECISION_ICON = {"approved": "✅", "declined": "⛔", "escalated": "🚨"}


def risk_badge(score: float) -> str:
    if score >= 0.65:
        return f":red[**HIGH RISK** — {score:.2f}]"
    if score >= 0.30:
        return f":orange[**MEDIUM RISK** — {score:.2f}]"
    return f":green[**LOW RISK** — {score:.2f}]"


st.title("🛡️ Fraud Guard — Live Transaction Review")
st.caption(
    "LangGraph fraud pipeline: deterministic triage → parallel specialist agents → human-in-the-loop review"
)

submit_tab, history_tab = st.tabs(["Submit & Review", "Decision History"])

with submit_tab:
    scenario_col, button_col = st.columns([3, 1])
    with scenario_col:
        scenario_choice = st.selectbox("Scenario", list(SCENARIOS.keys()), label_visibility="collapsed")
    with button_col:
        submit_clicked = st.button("Submit transaction", type="primary", use_container_width=True)
    if submit_clicked:
        with st.spinner("Running triage → investigation..."):
            thread_id = start_transaction(graph, scenario_choice)
        st.success(f"Submitted `{scenario_choice}` — thread `{thread_id}`")

    st.divider()
    st.subheader("Pending human review")

    pending = get_pending_reviews(graph)
    if not pending:
        st.info("No transactions are currently awaiting review.")

    for case in pending:
        txn = case["transaction"]
        with st.container(border=True):
            header_col, badge_col = st.columns([3, 1])
            with header_col:
                st.markdown(f"**{txn['transaction_id']}** — ${txn['amount']:,.2f} at `{txn['merchant_id']}`")
            with badge_col:
                st.markdown(risk_badge(case["composite_score"]))

            st.write(case["aggregate_reasoning"])

            with st.expander("Investigation trace"):
                for line in case["audit_log"]:
                    st.text(line)

            approve_col, decline_col, escalate_col = st.columns(3)
            if approve_col.button("✅ Approve", key=f"approve_{case['thread_id']}", use_container_width=True):
                resume_transaction(graph, case["thread_id"], "approve")
                st.rerun()
            if decline_col.button("⛔ Decline", key=f"decline_{case['thread_id']}", use_container_width=True):
                resume_transaction(graph, case["thread_id"], "decline")
                st.rerun()
            if escalate_col.button(
                "🚨 Escalate", key=f"escalate_{case['thread_id']}", use_container_width=True
            ):
                resume_transaction(graph, case["thread_id"], "escalate")
                st.rerun()

with history_tab:
    st.subheader("All decisions")

    history = sorted(get_decision_history(graph), key=lambda c: c["thread_id"])
    if not history:
        st.info("No transactions have been resolved yet.")
    else:
        # st.dataframe/st.table route through pyarrow, which segfaults under
        # Python 3.14 on this machine - render a plain markdown table instead.
        rows = ["| Transaction | Amount | Triage | Composite score | Decision |", "|---|---|---|---|---|"]
        for case in history:
            txn = case["transaction"]
            decision_label = f"{DECISION_ICON.get(case['final_decision'], '')} {case['final_decision']}"
            rows.append(
                f"| {txn['transaction_id']} | ${txn['amount']:,.2f} | {case['triage_decision']} "
                f"| {case['composite_score']:.2f} | {decision_label} |"
            )
        st.markdown("\n".join(rows))

        selected_thread = st.selectbox(
            "View full trace for", [case["thread_id"] for case in history]
        )
        selected_case = next(case for case in history if case["thread_id"] == selected_thread)
        with st.expander("Full audit trail", expanded=True):
            for line in selected_case["audit_log"]:
                st.text(line)
