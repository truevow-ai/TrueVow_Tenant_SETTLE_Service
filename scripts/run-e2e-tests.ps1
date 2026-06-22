# E2E Integration Test Runner
# Run all E2E tests against a live SETTLE backend

param(
    [string]$BackendUrl = "http://localhost:8002",
    [string]$ApiKey = "test-admin-key",
    [switch]$Verbose
)

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  TrueVow SETTLE — E2E Integration Tests" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend URL: $BackendUrl" -ForegroundColor Yellow
Write-Host "API Key: $($ApiKey.Substring(0, [Math]::Min(8, $ApiKey.Length)))..." -ForegroundColor Yellow
Write-Host ""

# Check if backend is running
Write-Host "[1/3] Checking backend connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  Backend is running ✓" -ForegroundColor Green
    } else {
        Write-Host "  Backend returned status $($response.StatusCode)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  Backend is NOT running at $BackendUrl" -ForegroundColor Red
    Write-Host "  Start the backend first: uvicorn app.main:app --reload --port 8002" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/3] Running E2E integration tests..." -ForegroundColor Yellow
Write-Host ""

$env:SETTLE_BACKEND_URL = $BackendUrl
$env:SETTLE_API_KEY = $ApiKey

if ($Verbose) {
    python -m pytest tests/test_e2e_integration.py -v --tb=long
} else {
    python -m pytest tests/test_e2e_integration.py -v --tb=short
}

$ExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "[3/3] Summary..." -ForegroundColor Yellow

if ($ExitCode -eq 0) {
    Write-Host ""
    Write-Host "  ALL E2E TESTS PASSED ✓" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "  E2E TESTS FAILED ✗" -ForegroundColor Red
    Write-Host ""
}

exit $ExitCode
