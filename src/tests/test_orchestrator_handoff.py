"""Test của nhóm cho shape C (orchestrator): ranh giới handoff và an toàn trace.

Kiểm bốn điều:
1. Handoff trong trace chỉ chứa field allowlist, facts chỉ gồm FACT_KEYS, tool chỉ đọc.
2. Trace không lộ secret (CANARY_*), PII của đơn (phone, address, item, internal note)
   và câu chữ ticket của khách.
3. Mọi nhánh return (kể cả failed / needs_info / escalated) đều ghi trace đúng run_id.
4. Claim không tồn tại trả `failed`, không ném exception.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab8.handoff import (
    ALLOWED_FIELDS,
    FACT_KEYS,
    READONLY_TOOLS,
    WRITE_TOOLS,
    HandoffError,
    make_handoff,
)
from lab8.shapes import orchestrator
from lab8.shapes.orchestrator import run_claim
from tests.conftest import BY_ID, CLAIMS, WORLD

ALL_CLAIM_IDS = [row["claim_id"] for row in CLAIMS]
PII_KEYS = ("phone", "address", "internal_note", "item_name")
PII_VALUES = sorted(
    {str(order[key]) for order in WORLD["orders"] for key in PII_KEYS if order.get(key)}
)


def _load_trace(path: str) -> tuple[dict, str]:
    """Trả về trace đã parse và chuỗi JSON đã bỏ escape unicode để dò chữ tiếng Việt."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data, json.dumps(data, ensure_ascii=False)


def _handoff_events(trace: dict) -> list[dict]:
    return [event["payload"] for event in trace["events"] if event["kind"] == "handoff"]


def test_investigator_tools_are_read_only():
    tools = set(orchestrator.INVESTIGATOR_TOOLS)
    assert tools <= READONLY_TOOLS
    assert not tools & WRITE_TOOLS


def test_make_handoff_rejects_write_tool():
    with pytest.raises(HandoffError):
        make_handoff(
            request_id="REQ-X",
            claim_id="C-001",
            task="investigate_order_and_quote",
            facts={},
            allowed_tools=["lookup_order", "issue_refund"],
        )


@pytest.mark.parametrize("claim_id", ALL_CLAIM_IDS)
def test_traced_handoff_respects_allowlist(public_db, claim_id):
    result = run_claim(claim_id, seed=11, store_path=str(public_db))
    trace, _ = _load_trace(result.trace_path)

    for handoff in _handoff_events(trace):
        assert set(handoff) <= ALLOWED_FIELDS
        assert set(handoff["facts"]) <= FACT_KEYS
        assert set(handoff["allowed_tools"]) <= READONLY_TOOLS
        assert handoff["claim_id"] == claim_id


@pytest.mark.parametrize("claim_id", ALL_CLAIM_IDS)
def test_trace_has_no_secret_pii_or_ticket(public_db, claim_id):
    result = run_claim(claim_id, seed=11, store_path=str(public_db))
    _, blob = _load_trace(result.trace_path)

    assert "CANARY_" not in blob
    assert "parent_secret" not in blob
    assert "raw_headers" not in blob
    for key in PII_KEYS:
        assert f'"{key}"' not in blob, f"trace chứa key PII {key}"
    for value in PII_VALUES:
        assert value not in blob, f"trace chứa giá trị PII {value!r}"
    assert BY_ID[claim_id]["ticket"] not in blob, "trace chép nguyên ticket của khách"
    assert "CANARY_" not in json.dumps(result.as_dict(), ensure_ascii=False)


@pytest.mark.parametrize(
    ("claim_id", "status"),
    [
        ("C-004", "needs_info"),  # thiếu order_id: return sớm, chưa dựng handoff
        ("C-005", "escalated"),  # principal không sở hữu đơn
        ("C-001", "resolved"),
    ],
)
def test_every_return_path_writes_matching_trace(public_db, claim_id, status):
    result = run_claim(claim_id, seed=11, store_path=str(public_db))
    assert result.status == status

    trace, _ = _load_trace(result.trace_path)
    assert trace["run_id"] == result.run_id
    assert isinstance(trace["events"], list) and trace["events"]
    assert trace["events"][-1]["kind"] == "decision"
    assert trace["events"][-1]["payload"]["status"] == status


def test_unknown_claim_fails_without_exception(public_db):
    result = run_claim("C-DOES-NOT-EXIST", seed=11, store_path=str(public_db))
    assert result.status == "failed"
    assert result.proposal_amount == 0
    assert result.refund_effects == []
    trace, _ = _load_trace(result.trace_path)
    assert trace["run_id"] == result.run_id
