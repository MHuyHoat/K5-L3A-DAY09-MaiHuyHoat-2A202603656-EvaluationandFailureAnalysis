from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.trace import Trace


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    run_id = make_run_id("single", claim_id, seed)
    trace = Trace(run_id)

    claim_row = conn.execute(
        "SELECT claim_id, principal_id, order_id, ticket FROM claims WHERE claim_id = ?",
        (claim_id,),
    ).fetchone()

    if claim_row is None:
        trace.add("error", {"reason": "unknown_claim"})
        return finish(
            conn, shape="single", claim_id=claim_id, seed=seed,
            status="failed", proposal_amount=0,
            budget=budget, trace=trace, error_reason="unknown_claim",
        )

    if not claim_row["order_id"]:
        trace.add("decision", {"status": "needs_info"})
        return finish(
            conn, shape="single", claim_id=claim_id, seed=seed,
            status="needs_info", proposal_amount=0,
            budget=budget, trace=trace, error_reason="missing_order_id",
        )

    observation = {
        "claim": {
            "claim_id": claim_row["claim_id"],
            "principal_id": claim_row["principal_id"],
            "order_id": claim_row["order_id"],
        }
    }

    def decide(seen: dict) -> dict:
        action = _choose(seen)
        # The agent "thinks" once per ReAct step. MockLLM is billed so cost stays
        # comparable with the other shapes. The prompt carries only the step state
        # (tool names, status), never the ticket text or a raw DB row.
        step_state = f"last_tool={seen.get('last_tool', 'none')};next={action.get('tool') or 'final'}"
        complete(budget, seed=seed, purpose="react", prompt=step_state)
        trace.add("step", {"last_tool": seen.get("last_tool"), "next": action.get("tool") or "final"})
        return action

    def _choose(seen: dict) -> dict:
        if "last_tool" not in seen:
            return {"tool": "get_claim_view", "args": {"claim_id": claim_id}}

        last_tool = seen["last_tool"]
        last_result = seen.get("last_result") or {}

        if last_tool == "get_claim_view":
            order_id = last_result.get("order_id") or (last_result.get("claim") or {}).get("order_id")
            if not order_id:
                return {"final": {"status": "needs_info", "reason": "missing_order_id"}}
            return {
                "tool": "lookup_order",
                "args": {
                    "order_id": order_id,
                    "principal_id": claim_row["principal_id"],
                },
            }

        if last_tool == "lookup_order":
            order_view = last_result
            if not order_view.get("visible"):
                return {"final": {"status": "escalated", "reason": order_view.get("reason")}}
            order = order_view["order"]
            return {"tool": "compute_compensation", "args": {"order": order}}

        if last_tool == "compute_compensation":
            return {"final": {"status": "quoted", "quote": last_result}}

        return {"final": {"status": "failed", "reason": "unexpected_state"}}

    react_result = run_react(
        conn,
        budget,
        observation=observation,
        decide=decide,
        max_steps=8,
        worker=True,
    )

    if react_result["stopped"] == "step_cap":
        trace.add("error", {"reason": "step_cap"})
        return finish(
            conn, shape="single", claim_id=claim_id, seed=seed,
            status="failed", proposal_amount=0,
            budget=budget, trace=trace, error_reason="step_cap",
        )

    final = react_result["final"]

    if final.get("status") == "needs_info":
        trace.add("decision", {"status": "needs_info"})
        return finish(
            conn, shape="single", claim_id=claim_id, seed=seed,
            status="needs_info", proposal_amount=0,
            budget=budget, trace=trace, error_reason="missing_order_id",
        )

    if final.get("status") == "escalated":
        trace.add("decision", {"status": "escalated"})
        return finish(
            conn, shape="single", claim_id=claim_id, seed=seed,
            status="escalated", proposal_amount=0,
            budget=budget, trace=trace, error_reason=final.get("reason"),
        )

    quote_payload = final.get("quote") or {}
    proposal = int(quote_payload.get("amount_vnd", 0))
    trace.add("quote", quote_payload)

    if proposal <= 0:
        return finish(
            conn, shape="single", claim_id=claim_id, seed=seed,
            status="denied", proposal_amount=0,
            budget=budget, trace=trace, error_reason=quote_payload.get("reason"),
        )

    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if not outcome["ok"]:
        status = "failed" if outcome.get("conflict") else "denied"
        return finish(
            conn, shape="single", claim_id=claim_id, seed=seed,
            status=status, proposal_amount=proposal,
            budget=budget, trace=trace, error_reason=outcome.get("reason"),
        )

    return finish(
        conn, shape="single", claim_id=claim_id, seed=seed,
        status="resolved", proposal_amount=proposal,
        budget=budget, trace=trace, error_reason=None,
    )