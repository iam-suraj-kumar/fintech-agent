import streamlit as st

from data.synthetic_transactions import SCENARIOS
from graph import graph
from ui.logic import get_pending_reviews, resume_transaction, start_transaction

st.set_page_config(page_title="Fraud Guard", layout="wide")
st.title("Fraud Guard — Live Transaction Review")

st.header("Run a scenario")
scenario_choice = st.selectbox("Scenario", list(SCENARIOS.keys()))
if st.button("Submit transaction"):
    thread_id = start_transaction(graph, scenario_choice)
    st.success(f"Submitted {thread_id}")

st.header("Pending human review")
for case in get_pending_reviews(graph):
    with st.container(border=True):
        st.subheader(case["thread_id"])
        st.write(f"Composite score: {case['composite_score']:.2f}")
        st.write(case["aggregate_reasoning"])
        cols = st.columns(3)
        if cols[0].button("Approve", key=f"approve_{case['thread_id']}"):
            resume_transaction(graph, case["thread_id"], "approve")
            st.rerun()
        if cols[1].button("Decline", key=f"decline_{case['thread_id']}"):
            resume_transaction(graph, case["thread_id"], "decline")
            st.rerun()
        if cols[2].button("Escalate", key=f"escalate_{case['thread_id']}"):
            resume_transaction(graph, case["thread_id"], "escalate")
            st.rerun()
        st.write("Audit log:")
        for line in case["audit_log"]:
            st.text(line)
