# SETTLE Comprehensive Test Runner
# Runs all automated tests and generates reports

Write-Host "=" -ForegroundColor Cyan
Write-Host "🚀 SETTLE Comprehensive Test Suite" -ForegroundColor Cyan
Write-Host "="*60 -ForegroundColor Cyan
Write-Host ""

# Check if SETTLE backend is running
Write-Host "1️⃣  Checking SETTLE Backend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8002/health" -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ SETTLE Backend is running on port 8002" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ SETTLE Backend is NOT running!" -ForegroundColor Red
    Write-Host "   Please start the backend first:" -ForegroundColor Yellow
    Write-Host "   cd C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\2025-TrueVow-Settle-Service" -ForegroundColor Gray
    Write-Host "   python -m uvicorn app.main:app --reload --port 8002" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host ""

# Get API key
Write-Host "2️⃣  API Key Configuration..." -ForegroundColor Yellow
$apiKey = $env:SETTLE_API_KEY
if (-not $apiKey) {
    Write-Host "⚠️  No API key found in environment variable SETTLE_API_KEY" -ForegroundColor Yellow
    Write-Host "   Using test key..." -ForegroundColor Gray
    $apiKey = "sk_test_comprehensive_testing_key"
}
Write-Host "✅ API Key: $($apiKey.Substring(0, [Math]::Min(20, $apiKey.Length)))..." -ForegroundColor Green
Write-Host ""

# Run integration tests
Write-Host "3️⃣  Running Integration Tests..." -ForegroundColor Yellow
try {
    python tests/test_automated_integration.py $apiKey
    Write-Host "✅ Integration tests completed" -ForegroundColor Green
} catch {
    Write-Host "❌ Integration tests failed: $_" -ForegroundColor Red
}
Write-Host ""

# Run customer scenario tests
Write-Host "4️⃣  Running Customer Scenario Tests..." -ForegroundColor Yellow
try {
    python tests/test_customer_scenarios.py $apiKey
    Write-Host "✅ Customer scenario tests completed" -ForegroundColor Green
} catch {
    Write-Host "❌ Customer scenario tests failed: $_" -ForegroundColor Red
}
Write-Host ""

# Summary
Write-Host "=" -ForegroundColor Cyan
Write-Host "📊 Test Reports Generated:" -ForegroundColor Cyan
Write-Host "="*60 -ForegroundColor Cyan
Write-Host "1. SETTLE_TEST_REPORT.md                - Integration tests" -ForegroundColor White
Write-Host "2. SETTLE_CUSTOMER_SCENARIO_REPORT.md   - Customer scenarios" -ForegroundColor White
Write-Host ""
Write-Host "✅ All tests complete!" -ForegroundColor Green
Write-Host ""

