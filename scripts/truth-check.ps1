# TrueVow SETTLE — Truth Command Automation
# Run all verification gates and report results
# Usage: .\scripts\truth-check.ps1

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  TrueVow SETTLE Service — Truth Commands" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$ExitCode = 0
$PassCount = 0
$FailCount = 0

function Run-Test {
    param(
        [string]$Name,
        [string]$Command
    )
    
    Write-Host "[$Name] Running..." -ForegroundColor Yellow
    Write-Host "Command: $Command" -ForegroundColor Gray
    Write-Host ""
    
    $Output = & powershell -Command $Command 2>&1
    $LastExit = $LASTEXITCODE
    
    if ($LastExit -eq 0) {
        Write-Host "  PASS" -ForegroundColor Green
        $script:PassCount++
    } else {
        Write-Host "  FAIL (exit code: $LastExit)" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Last 30 lines of output:" -ForegroundColor Red
        $Output | Select-Object -Last 30 | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
        $script:FailCount++
        $script:ExitCode = 1
    }
    Write-Host ""
}

# Test 1: Core tests
Run-Test "1/4 Core Tests" "python -m pytest tests/test_estimator.py tests/test_intelligence_gate.py tests/test_anonymizer.py tests/test_validator.py -v --tb=short"

# Test 2: New feature tests
Run-Test "2/4 New Feature Tests" "python -m pytest tests/test_phase1_phase2.py -v --tb=short"

# Test 3: Full suite
Run-Test "3/4 Full Test Suite" "python -m pytest tests/ -v --tb=short --ignore=tests/test_customer_scenarios.py --ignore=tests/test_automated_integration.py --ignore=tests/test_functional.py --ignore=tests/comprehensive_test_suite.py"

# Test 4: Import check
Run-Test "4/4 Import Check" "python -c 'from app.main import app; print(\"Import OK\")'"

# Summary
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Results: $PassCount passed, $FailCount failed" -ForegroundColor $(if ($FailCount -eq 0) { "Green" } else { "Red" })
Write-Host "================================================================" -ForegroundColor Cyan

if ($ExitCode -eq 0) {
    Write-Host ""
    Write-Host "  ALL TRUTH COMMANDS PASSED" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "  TRUTH COMMANDS FAILED — Fix failures before committing" -ForegroundColor Red
    Write-Host ""
}

exit $ExitCode
