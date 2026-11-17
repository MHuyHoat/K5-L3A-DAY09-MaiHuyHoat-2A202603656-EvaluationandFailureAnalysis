# Integration gate (Windows PowerShell). Run from src\ after merging a teammate's branch:
#   powershell -ExecutionPolicy Bypass -File scripts\integration_check.ps1 [-Benchmark]
param([switch]$Benchmark)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

function Step($name, [scriptblock]$cmd) {
    Write-Host "== $name" -ForegroundColor Cyan
    & $cmd
    if ($LASTEXITCODE -ne 0) { Write-Host "FAIL at: $name" -ForegroundColor Red; exit 1 }
}

Step "1. smoke" { python -m lab8.smoke }
Step "2. host gate (must stay green)" { python -m pytest -q }

Write-Host "== 3. guard: measurement files must be untouched" -ForegroundColor Cyan
$changed = git diff --name-only origin/main -- lab8/metrics.py lab8/durability.py lab8/policy.py config data
if ($changed) { Write-Host "FAIL: measurement files changed vs origin/main:`n$changed" -ForegroundColor Red; exit 1 }

Write-Host "== 4. student matrix per shape" -ForegroundColor Cyan
$all = python -m pytest -q --co -m student -o addopts= tests/test_public_matrix.py
foreach ($shape in "workflow", "single", "orchestrator") {
    # Select by the shape parameter in the test id ("-k single" would also match *single_run_cases*).
    $ids = $all | Where-Object { $_ -match "[\[-]$shape[\]-]" }
    $last = python -m pytest -q -m student -o addopts= @ids 2>&1 | Select-Object -Last 1
    Write-Host ("{0,-13} {1}" -f $shape, $last)
}

Step "5. crash suite" { python -m lab8.crash_test --count 20 --out reports/crash.json }

if ($Benchmark) {
    Step "6. benchmark (4 shapes x 5 seeds)" {
        python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm `
            --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
    }
}

Write-Host "== 7. submission check" -ForegroundColor Cyan
python -m lab8.check_submission
