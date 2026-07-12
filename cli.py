#!/usr/bin/env python3
"""Terminal companion to the Streamlit UI - same graph, same database files,
safe to run alongside it since both talk to the same checkpointed state."""

import argparse

from graph import graph
from ui.logic import get_decision_history, get_pending_reviews, resume_transaction, start_transaction

DECISIONS = ("approve", "decline", "escalate")


def _print_trace(audit_log: list[dict]) -> None:
    for entry in audit_log:
        node, kind = entry["node"], entry["kind"]
        if kind == "tool_call":
            print(f"    [{node}] -> {entry['tool']}({entry['args']})")
        elif kind == "tool_result":
            print(f"    [{node}] <- {entry['tool']} returned: {entry['result']}")
        else:
            print(f"  [{node}] {entry['text']}")


def cmd_submit(args: argparse.Namespace) -> None:
    thread_id = start_transaction(graph, args.transaction_id)
    print(f"Submitted `{args.transaction_id}` (thread {thread_id})\n")

    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    _print_trace(snapshot.values["audit_log"])

    if snapshot.next == ("human_review",):
        print(f"\nComposite score: {snapshot.values['composite_score']:.2f}")
        print(snapshot.values["aggregate_reasoning"])
        decision = input(f"\nDecision [{'/'.join(DECISIONS)}]: ").strip().lower()
        while decision not in DECISIONS:
            decision = input(f"Please enter one of {', '.join(DECISIONS)}: ").strip().lower()
        result = resume_transaction(graph, thread_id, decision)
        print(f"\nFinal decision: {result['final_decision']}")
    else:
        print(f"\nFinal decision: {snapshot.values['final_decision']}")


def cmd_pending(args: argparse.Namespace) -> None:
    pending = get_pending_reviews(graph)
    if not pending:
        print("No transactions are currently awaiting review.")
        return
    for case in pending:
        txn = case["transaction"]
        print(
            f"{case['thread_id']:24s} {txn['transaction_id']:12s} "
            f"${txn['amount']:>10,.2f}  score={case['composite_score']:.2f}"
        )


def cmd_review(args: argparse.Namespace) -> None:
    result = resume_transaction(graph, args.thread_id, args.decision)
    _print_trace(result["audit_log"])
    print(f"\nFinal decision: {result['final_decision']}")


def cmd_history(args: argparse.Namespace) -> None:
    history = get_decision_history(graph)
    if not history:
        print("No transactions have been resolved yet.")
        return
    for case in history:
        txn = case["transaction"]
        score = f"{case['composite_score']:.2f}" if case["composite_score"] is not None else "—"
        print(
            f"{txn['transaction_id']:12s} {case['triage_decision']:12s} "
            f"{case['final_decision']:10s} score={score:>5s}  ${txn['amount']:>10,.2f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fraud Guard CLI - terminal companion to the Streamlit UI, same graph."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    submit_p = sub.add_parser("submit", help="Submit a transaction ID and watch the investigation run")
    submit_p.add_argument("transaction_id")
    submit_p.set_defaults(func=cmd_submit)

    pending_p = sub.add_parser("pending", help="List transactions awaiting human review")
    pending_p.set_defaults(func=cmd_pending)

    review_p = sub.add_parser("review", help="Approve/decline/escalate a pending transaction by thread ID")
    review_p.add_argument("thread_id")
    review_p.add_argument("decision", choices=DECISIONS)
    review_p.set_defaults(func=cmd_review)

    history_p = sub.add_parser("history", help="Show all resolved transactions")
    history_p.set_defaults(func=cmd_history)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
