"""Shape B must bill its ReAct steps so cost/success is comparable across shapes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab8.db import init_store
from lab8.shapes.single import run_claim
from tests.conftest import BY_ID, CLAIMS, WORLD

pytestmark = pytest.mark.student


def _store(tmp_path: Path) -> Path:
    path = tmp_path / "single.sqlite"
    init_store(path, WORLD, CLAIMS).close()
    return path


def test_single_counts_one_model_call_per_react_step(tmp_path):
    result = run_claim("C-001", seed=11, store_path=str(_store(tmp_path)))
    body = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    steps = [e for e in body["events"] if e["kind"] == "step"]
    assert result.status == "resolved"
    assert steps, "ReAct steps must appear in the trace"
    assert result.model_calls == len(steps)
    assert result.cost_estimate > result.tool_calls * 10  # tools alone cost 10 VND each


def test_single_step_trace_never_contains_ticket(tmp_path):
    result = run_claim("C-002", seed=55, store_path=str(_store(tmp_path)))
    text = Path(result.trace_path).read_text(encoding="utf-8")
    assert BY_ID["C-002"]["ticket"] not in text
    assert "CANARY_SECRET" not in text
    assert result.status == "denied"
