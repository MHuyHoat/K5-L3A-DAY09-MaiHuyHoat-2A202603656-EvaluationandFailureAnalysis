"""Test của nhóm: rà an toàn trace cho cả 4 shape (CP4).

Chạy cùng một bộ kiểm cho workflow, single, orchestrator và swarm:
1. Trace, RunResult và stdout không lộ secret (CANARY_*), PII của đơn, hay nguyên văn ticket.
2. Handoff (nếu shape có) chỉ chứa field allowlist, facts trong FACT_KEYS, tool chỉ đọc.
3. Mọi nhánh return ghi trace đúng contract v1: file đọc được, run_id khớp, events là list.
4. Claim không tồn tại trả `failed`, không ném exception.

Shape còn là stub (`error_reason == "not_implemented"`) được skip, nên file này xanh
ngay cả khi chưa merge đủ 3 shape; merge xong là test tự chạy cho shape đó.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab8.handoff import ALLOWED_FIELDS, FACT_KEYS, READONLY_TOOLS
from lab8.shapes import SHAPES
from tests.conftest import BY_ID, CLAIMS, WORLD

SHAPE_NAMES = ["workflow", "single", "orchestrator", "swarm"]
ALL_CLAIM_IDS = [row["claim_id"] for row in CLAIMS]
PII_KEYS = ("phone", "address", "internal_note", "item_name")
PII_VALUES = sorted(
    {str(order[key]) for order in WORLD["orders"] for key in PII_KEYS if order.get(key)}
)
SECRET_MARKERS = ("CANARY_", "parent_secret", "raw_headers")


def _run(shape: str, claim_id: str, store) -> object:
    result = SHAPES[shape](claim_id, seed=11, store_path=str(store))
    if result.error_reason == "not_implemented":
        pytest.skip(f"{shape} còn là stub")
    return result


def _load_trace(path: str) -> tuple[dict, str]:
    """Trả về trace đã parse và chuỗi JSON không escape unicode để dò chữ tiếng Việt."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data, json.dumps(data, ensure_ascii=False)


def _assert_no_leak(blob: str, claim_id: str, where: str) -> None:
    for marker in SECRET_MARKERS:
        assert marker not in blob, f"{where} chứa {marker}"
    for key in PII_KEYS:
        assert f'"{key}"' not in blob, f"{where} chứa key PII {key}"
    for value in PII_VALUES:
        assert value not in blob, f"{where} chứa giá trị PII {value!r}"
    assert BY_ID[claim_id]["ticket"] not in blob, f"{where} chép nguyên ticket"


@pytest.mark.parametrize("claim_id", ALL_CLAIM_IDS)
@pytest.mark.parametrize("shape", SHAPE_NAMES)
def test_trace_result_and_stdout_do_not_leak(public_db, capsys, shape, claim_id):
    result = _run(shape, claim_id, public_db)
    stdout = capsys.readouterr()
    _, blob = _load_trace(result.trace_path)

    _assert_no_leak(blob, claim_id, f"trace {shape}")
    _assert_no_leak(json.dumps(result.as_dict(), ensure_ascii=False), claim_id, f"RunResult {shape}")
    _assert_no_leak(stdout.out + stdout.err, claim_id, f"stdout {shape}")


@pytest.mark.parametrize("claim_id", ALL_CLAIM_IDS)
@pytest.mark.parametrize("shape", SHAPE_NAMES)
def test_trace_contract_and_handoff_allowlist(public_db, shape, claim_id):
    result = _run(shape, claim_id, public_db)
    trace, _ = _load_trace(result.trace_path)

    assert trace["run_id"] == result.run_id
    assert isinstance(trace["events"], list)
    for event in trace["events"]:
        if event.get("kind") != "handoff":
            continue
        handoff = event["payload"]
        assert set(handoff) <= ALLOWED_FIELDS
        assert set(handoff.get("facts") or {}) <= FACT_KEYS
        assert set(handoff.get("allowed_tools") or []) <= READONLY_TOOLS
        assert handoff["claim_id"] == claim_id


@pytest.mark.parametrize("shape", SHAPE_NAMES)
def test_unknown_claim_fails_without_exception(public_db, shape):
    result = _run(shape, "C-DOES-NOT-EXIST", public_db)
    assert result.status == "failed"
    assert result.proposal_amount == 0
    assert result.refund_effects == []
    trace, _ = _load_trace(result.trace_path)
    assert trace["run_id"] == result.run_id
