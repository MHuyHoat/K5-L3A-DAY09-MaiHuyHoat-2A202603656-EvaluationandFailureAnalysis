#!/usr/bin/env bash
# Integration gate: run from src/ after merging a teammate's branch.
# Stops at the first failing step so a broken merge is caught before benchmarking.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1. smoke"
python -m lab8.smoke

echo "== 2. host gate (must stay green)"
python -m pytest -q

echo "== 3. guard: measurement files must be untouched"
if git diff --name-only origin/main -- lab8/metrics.py lab8/durability.py lab8/policy.py config data | grep .; then
  echo "FAIL: measurement files changed vs origin/main (see list above)"; exit 1
fi

echo "== 4. student matrix per shape"
# Select by the shape parameter in the test id ("-k single" would also match *single_run_cases*).
for shape in workflow single orchestrator; do
  ids=$(python -m pytest -q --co -m student -o addopts= tests/test_public_matrix.py | grep -E "[[-]${shape}[]-]" || true)
  printf '%-13s ' "$shape"
  # shellcheck disable=SC2086
  python -m pytest -q -m student -o addopts= $ids 2>&1 | tail -1
done

echo "== 5. crash suite"
python -m lab8.crash_test --count 20 --out reports/crash.json

if [[ "${1:-}" == "--benchmark" ]]; then
  echo "== 6. benchmark (4 shapes x 5 seeds)"
  python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm \
    --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
fi

echo "== 7. submission check"
python -m lab8.check_submission || true
