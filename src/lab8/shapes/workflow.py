"""Shape A — deterministic workflow.

Signature (do not change):

    run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult

Fixed Python steps. Money stays in code (`lab8.tools.compute_compensation`);
the host (`durability.issue_refund`) checks approval, per-order cap and
idempotency before it writes the ledger. MockLLM is used once, only to draft
the customer reply, and never sees the ticket text or decides an amount.

Steps:

1. Read the claim through `get_claim_view` (allowlisted columns, not SELECT *).
2. Unknown claim -> `failed`. Missing order_id -> `needs_info`, no ledger write.
   The order id is never parsed out of the ticket text.
3. `lookup_order` scoped to the claim's principal. Not visible -> `escalated`.
4. Quote from the order row via `compute_compensation`. Delay numbers written in
   the ticket are ignored (the ticket is user data, not an instruction).
5. Quote 0 -> `denied`, issue_refund is not called.
6. Quote > 0 -> `issue_refund(conn, claim_id, <full quote>, crash_at=crash_at)`.
   The FULL quote is passed; the host subtracts earlier refunds on the same
   order (T13, T14). `InjectedCrash` is not caught (T12 / crash suite).
   Host refusal -> `denied` (host wrote `policy_denied`), conflict -> `failed`.
7. Success -> `resolved`.

Trace (contract v1): every return path goes through `finish()`, which writes
`traces/<run_id>.json`. Only allowlisted fields are recorded: claim_id,
order_id, the order view from `lookup_order` (no phone, address, item or
internal note), the quote, and host outcome reasons. The ticket text, the
principal id and any raw DB row are never written.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import compute_compensation, get_claim_view, lookup_order, tool_cost
from lab8.trace import Trace

SHAPE = "workflow"


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
    trace = Trace(make_run_id(SHAPE, claim_id, seed))

    def done(status: str, proposal: int, reason: str | None) -> RunResult:
        # One model call, for the reply text only. The prompt carries the
        # decision, never the ticket, so user text cannot steer anything.
        if status != "failed":
            complete(budget, seed=seed, purpose="draft", prompt=f"status={status};amount={proposal}")
        trace.add("decision", {"status": status, "proposal_amount": proposal, "reason": reason})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    # 1. Claim view (allowlisted columns).
    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    if not claim["found"]:
        trace.add("claim", {"claim_id": claim_id, "found": False})
        return done("failed", 0, "unknown_claim")
    order_id = claim.get("order_id")
    trace.add("claim", {"claim_id": claim_id, "found": True, "order_id": order_id})

    # 2. No order id on the claim row -> ask for it. Never read it from the ticket.
    if not order_id:
        return done("needs_info", 0, "missing_order_id")

    # 3. Order lookup scoped to the claim's principal.
    budget.add_tool(tool_cost())
    order_view = lookup_order(conn, order_id, claim["principal_id"])
    if not order_view.get("visible"):
        trace.add("order", {"order_id": order_id, "visible": False, "reason": order_view.get("reason")})
        return done("escalated", 0, order_view.get("reason"))
    order: dict[str, Any] = dict(order_view["order"])
    trace.add("order", safe_dump({"visible": True, "order": order}))

    # 4. Quote from the DB row only.
    budget.add_tool(tool_cost())
    quote = compute_compensation(conn, order)
    proposal = int(quote["amount_vnd"])
    trace.add("quote", safe_dump(quote))

    # 5. Nothing owed -> deny without touching the host write path.
    if proposal <= 0:
        return done("denied", 0, quote.get("reason"))

    # 6. Host gate. Full quote in; crash_at passed through; InjectedCrash propagates.
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise
    trace.add(
        "host",
        {"ok": bool(outcome["ok"]), "reason": outcome["reason"], "conflict": bool(outcome["conflict"])},
    )

    if not outcome["ok"]:
        return done("failed" if outcome["conflict"] else "denied", proposal, outcome["reason"])

    # 7. Committed (or idempotent replay of the same amount).
    return done("resolved", proposal, None)
