import itertools
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

NODE_LABELS = {
    "ingest": ("📥", "Ingest"),
    "triage": ("🧮", "Triage"),
    "auto_approve": ("✅", "Auto-approve"),
    "auto_decline": ("⛔", "Auto-decline"),
    "transaction_analyst": ("💰", "Transaction Analyst"),
    "identity_verifier": ("🪪", "Identity Verifier"),
    "pattern_detector": ("🔍", "Pattern Detector"),
    "aggregator": ("🧭", "Aggregator"),
    "human_review": ("🙋", "Human Review"),
    "resolution": ("🏁", "Resolution"),
}


def risk_badge(score: float) -> str:
    if score >= 0.65:
        return f":red[**HIGH RISK** — {score:.2f}]"
    if score >= 0.30:
        return f":orange[**MEDIUM RISK** — {score:.2f}]"
    return f":green[**LOW RISK** — {score:.2f}]"


def render_trace(audit_log: list[dict]) -> None:
    for node, group in itertools.groupby(audit_log, key=lambda entry: entry["node"]):
        entries = list(group)
        icon, label = NODE_LABELS.get(node, ("•", node))
        headline = next((e for e in entries if e["kind"] in ("info", "summary", "decision")), None)
        tool_steps = [e for e in entries if e["kind"] in ("tool_call", "tool_result")]

        st.markdown(f"**{icon} {label}**")
        if headline:
            st.write(headline["text"])
        if tool_steps:
            with st.expander(f"{len(tool_steps) // 2} tool call(s)"):
                for step in tool_steps:
                    if step["kind"] == "tool_call":
                        st.code(f"{step['tool']}({step['args']})", language="python")
                    else:
                        result = step["result"]
                        if isinstance(result, (dict, list)):
                            st.json(result)
                        else:
                            st.text(str(result))


with st.sidebar:
    st.header("📖 Terminology")

    st.markdown("**Source**")
    st.caption("📜 curated — one of the 4 hand-scripted demo cases")
    st.caption("🎲 generated — synthesized deterministically from the ID you typed")

    st.markdown("**Triage decision**")
    st.caption("`auto_approve` — score < 0.30, resolved instantly, no LLM calls")
    st.caption("`investigate` — score 0.30–0.65, fans out to the 3 specialist agents")
    st.caption("`auto_decline` — score ≥ 0.65, resolved instantly, no LLM calls")

    st.markdown("**Composite score**")
    st.caption(
        "Set only by the aggregator, after the specialists run. Stays **—** for "
        "auto_approve/auto_decline transactions since they skip investigation "
        "entirely — that's the point of the tiered design, not a missing value."
    )

    st.markdown("**Risk badge** *(on composite score)*")
    st.caption(":green[LOW] < 0.30 · :orange[MEDIUM] 0.30–0.65 · :red[HIGH] ≥ 0.65")

    st.markdown("**Final decision**")
    st.caption("✅ approved · ⛔ declined · 🚨 escalated (sent to a senior reviewer)")

    st.markdown("**Investigation trace nodes**")
    for _node_key, (_icon, _label) in NODE_LABELS.items():
        st.caption(f"{_icon} {_label}")

st.markdown(
    """
    <style>
    .hero {
        background: linear-gradient(135deg, #2F6FED 0%, #1B4FBF 100%);
        color: white; padding: 2rem 2.5rem; border-radius: 16px; margin-bottom: 1.25rem;
    }
    .hero h1 { color: white; margin: 0 0 0.4rem 0; font-size: 2.1rem; }
    .hero p { color: #DCE6FF; margin: 0; font-size: 1.05rem; }
    .problem-statement {
        background: #F4F7FB; border-left: 4px solid #2F6FED; padding: 1.1rem 1.4rem;
        border-radius: 8px; margin-bottom: 1.5rem; font-size: 0.98rem; line-height: 1.6;
    }
    .problem-statement b { color: #1B4FBF; }
    .outcome-card {
        border-radius: 12px; padding: 1.2rem 1.4rem; margin-bottom: 1rem;
        border: 1px solid #E5E9F0; background: #FFFFFF;
    }
    .outcome-card h4 { margin: 0 0 0.5rem 0; }
    .outcome-card.approve { border-left: 5px solid #16A34A; }
    .outcome-card.decline { border-left: 5px solid #DC2626; }
    .outcome-card.investigate { border-left: 5px solid #D97706; }
    </style>
    <div class="hero">
        <h1>🛡️ Fraud Guard</h1>
        <p>Live transaction review — deterministic triage, parallel specialist investigation, human-in-the-loop review</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="problem-statement">
    <b>The problem.</b> Every transaction carries risk. Block too aggressively and
    legitimate customers get turned away; look too little and fraud slips
    through, at real financial and reputational cost. Investigating every
    transaction with the same depth is too slow and too expensive to do at
    scale — but a system that treats every case with the same rigid rules is
    too blunt to catch what matters and too quick to flag what doesn't.
    Fraud Guard resolves the overwhelming majority of transactions instantly
    on their own, reserves deeper investigation for the genuinely ambiguous
    ones, and keeps a human accountable for any decision with real
    consequences — with a full explanation behind every outcome.
    </div>
    """,
    unsafe_allow_html=True,
)

how_it_works_tab, submit_tab, history_tab = st.tabs(["How It Works", "Submit & Review", "Decision History"])

with how_it_works_tab:
    st.subheader("Every transaction ends up in one of five places")

    st.markdown(
        """
        <div class="outcome-card approve">
        <h4>✅ Auto-approve</h4>
        <b>Trigger:</b> initial screening scores the transaction as low-risk.<br>
        <b>What happens:</b> resolved instantly — no further investigation, no review needed.<br>
        <b>Example:</b> <code>clean_coffee</code> — a small, ordinary purchase from a familiar device.
        </div>

        <div class="outcome-card decline">
        <h4>⛔ Auto-decline</h4>
        <b>Trigger:</b> initial screening finds enough strong red flags at once to be confident this is fraud.<br>
        <b>What happens:</b> blocked instantly — the signals already speak for themselves.<br>
        <b>Example:</b> <code>impossible_travel</code> — a purchase from a brand-new device in a country
        the account has never been active in, minutes after activity somewhere else entirely.
        </div>

        <div class="outcome-card investigate">
        <h4>🔎 Investigate → Approved</h4>
        <b>Trigger:</b> initial signals are ambiguous — not clearly safe, not clearly fraudulent.<br>
        <b>What happens:</b> a deeper investigation weighs the account's history, device and location,
        and comparison to known fraud patterns; a reviewer examines the findings and decides the
        activity is legitimate.<br>
        <b>Example:</b> submit <code>borderline_wire</code> and click Approve.
        </div>

        <div class="outcome-card investigate">
        <h4>🔎 Investigate → Declined</h4>
        <b>Trigger:</b> same as above — ambiguous initial signals.<br>
        <b>What happens:</b> the same investigation runs, but the reviewer determines the activity is
        fraudulent and blocks it.<br>
        <b>Example:</b> submit <code>borderline_wire</code> and click Decline instead.
        </div>

        <div class="outcome-card investigate">
        <h4>🔎 Investigate → Escalated</h4>
        <b>Trigger:</b> same as above, but the reviewer isn't confident enough to decide alone.<br>
        <b>What happens:</b> the case is sent to a senior reviewer for a final call, rather than being
        resolved on the spot.<br>
        <b>Example:</b> <code>borderline_restart_demo</code> — flagged beneficiary, escalate rather than
        decide immediately.
        </div>
        """,
        unsafe_allow_html=True,
    )

with submit_tab:
    if "txn_id_input" not in st.session_state:
        st.session_state.txn_id_input = "clean_coffee"

    def _set_quick_pick(name: str) -> None:
        st.session_state.txn_id_input = name

    st.caption("Type any transaction ID — known IDs use their scripted case, anything else is synthesized:")
    quick_cols = st.columns(len(SCENARIOS))
    for col, name in zip(quick_cols, SCENARIOS.keys()):
        col.button(name, key=f"quickpick_{name}", on_click=_set_quick_pick, args=(name,), use_container_width=True)

    id_col, button_col = st.columns([3, 1])
    with id_col:
        st.text_input("Transaction ID", key="txn_id_input", label_visibility="collapsed")
    with button_col:
        submit_clicked = st.button("Submit transaction", type="primary", use_container_width=True)
    if submit_clicked:
        with st.spinner("Running triage → investigation..."):
            start_transaction(graph, st.session_state.txn_id_input)
        st.success(f"Submitted `{st.session_state.txn_id_input}`")

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
                source_tag = "📜 curated" if txn.get("source") == "curated" else "🎲 generated"
                st.markdown(
                    f"**{txn['transaction_id']}** — ${txn['amount']:,.2f} at `{txn['merchant_id']}` · {source_tag}"
                )
            with badge_col:
                st.markdown(risk_badge(case["composite_score"]))

            st.write(case["aggregate_reasoning"])

            with st.expander("Investigation trace"):
                render_trace(case["audit_log"])

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
        rows = [
            "| Transaction | Source | Amount | Triage | Composite score | Decision |",
            "|---|---|---|---|---|---|",
        ]
        for case in history:
            txn = case["transaction"]
            source_label = "📜 curated" if txn.get("source") == "curated" else "🎲 generated"
            decision_label = f"{DECISION_ICON.get(case['final_decision'], '')} {case['final_decision']}"
            composite_label = (
                f"{case['composite_score']:.2f}" if case["composite_score"] is not None else "—"
            )
            rows.append(
                f"| {txn['transaction_id']} | {source_label} | ${txn['amount']:,.2f} | {case['triage_decision']} "
                f"| {composite_label} | {decision_label} |"
            )
        st.markdown("\n".join(rows))

        selected_thread = st.selectbox(
            "View full trace for", [case["thread_id"] for case in history]
        )
        selected_case = next(case for case in history if case["thread_id"] == selected_thread)
        with st.expander("Full audit trail", expanded=True):
            render_trace(selected_case["audit_log"])
