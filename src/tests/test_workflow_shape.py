"""Extra checks for shape A (workflow), beyond the shared T01–T14 matrix.

Run with: python -m pytest -q -m student -o addopts= -k workflow_shape
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab8.db import connect, init_store
from lab8.durability import InjectedCrash, committed_audit_count, get_refund
from lab8.shapes.workflow import run_claim
from tests.conftest import BY_ID, CLAIMS, WORLD

pytestmark = pytest.mark.student

ALL_CLAIM_IDS = [row["claim_id"] for row in CLAIMS]
SEEDS = [11, 22, 33, 44, 55]
PII_FIELDS = ("phone", "address", "internal_note", "item_name")


def _store(tmp_path: Path, name: str = "wf.sqlite") -> Path:
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS).close()
    return path


def _forbidden_strings() -> list[str]:
    """Every secret and PII value present in the public world."""
    values: set[str] = set()
    for claim in CLAIMS:
        values.add(claim["parent_secret"])
        for header in (claim.get("raw_headers") or {}).values():
            values.add(str(header))
    for order in WORLD["orders"]:
        for field in PII_FIELDS:
            if order.get(field):
                values.add(str(order[field]))
    return sorted(v for v in values if v)


@pytest.mark.parametrize("claim_id", ALL_CLAIM_IDS)
def test_workflow_trace_and_result_have_no_secret_or_pii(tmp_path, claim_id):
    store = _store(tmp_path)
    result = run_claim(claim_id, seed=11, store_path=str(store))
    trace_text = Path(result.trace_path).read_text(encoding="utf-8")
    blob = trace_text + json.dumps(result.as_dict(), ensure_ascii=False)
    for value in _forbidden_strings():
        assert value not in blob, f"leaked {value!r} for {claim_id}"
    assert "CANARY_SECRET" not in blob
    # Ticket text is user data; the workflow never copies it into the trace.
    assert BY_ID[claim_id]["ticket"] not in trace_text


def test_workflow_is_seed_invariant(tmp_path):
    """A fixed workflow must give the same decision on every seed (zero variance)."""
    for claim_id in ALL_CLAIM_IDS:
        decisions = set()
        for seed in SEEDS:
            store = _store(tmp_path, f"{claim_id}-{seed}.sqlite")
            result = run_claim(claim_id, seed=seed, store_path=str(store))
            decisions.add((result.status, result.proposal_amount))
        assert len(decisions) == 1, f"{claim_id}: {decisions}"


def test_workflow_ignores_delay_written_in_ticket(tmp_path):
    """C-002: ticket claims 5 days late, order row says 2 -> denied on every seed (swarm misses seed 55)."""
    for seed in SEEDS:
        store = _store(tmp_path, f"c002-{seed}.sqlite")
        result = run_claim("C-002", seed=seed, store_path=str(store))
        assert result.status == "denied"
        assert result.proposal_amount == 0
        assert result.refund_effects == []


def test_workflow_unknown_claim_fails_cleanly(tmp_path):
    store = _store(tmp_path)
    result = run_claim("C-DOES-NOT-EXIST", seed=11, store_path=str(store))
    assert result.status == "failed"
    assert result.proposal_amount == 0
    assert result.error_reason == "unknown_claim"
    body = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    assert body["run_id"] == result.run_id
    assert isinstance(body["events"], list)


@pytest.mark.parametrize("crash_at", ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"])
def test_workflow_crash_then_resume_gives_one_refund(tmp_path, crash_at):
    store = _store(tmp_path)
    with pytest.raises(InjectedCrash):
        run_claim("C-001", seed=11, store_path=str(store), crash_at=crash_at)
    result = run_claim("C-001", seed=11, store_path=str(store))
    assert result.status == "resolved"
    conn = connect(store)
    try:
        rows = conn.execute("SELECT COUNT(*) FROM refund_ledger WHERE claim_id = 'C-001'").fetchone()[0]
        assert rows == 1
        assert committed_audit_count(conn, "C-001") == 1
        assert int(get_refund(conn, "C-001")["amount_vnd"]) == 35000
    finally:
        conn.close()
