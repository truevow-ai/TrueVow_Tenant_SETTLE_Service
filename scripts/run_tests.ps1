# ============================================================================
# Run Tests for SETTLE Service (PowerShell)
# ============================================================================

Write-Host "🧪 Running TrueVow SETTLE Service Tests..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Activate virtual environment (if exists)
if (Test-Path "venv\Scripts\Activate.ps1") {
    & venv\Scripts\Activate.ps1
} elseif (Test-Path ".venv\Scripts\Activate.ps1") {
    & .venv\Scripts\Activate.ps1
}

# Run unit tests
Write-Host ""
Write-Host "📋 Running Unit Tests..." -ForegroundColor Yellow
pytest tests/test_estimator.py tests/test_validator.py tests/test_anonymizer.py -v

# Run functional tests
Write-Host ""
Write-Host "🔗 Running Functional Tests..." -ForegroundColor Yellow
pytest tests/test_functional.py -v

# Run all tests with coverage
Write-Host ""
Write-Host "📊 Running All Tests with Coverage..." -ForegroundColor Yellow
pytest tests/ -v --cov=app --cov-report=term --cov-report=html

Write-Host ""
Write-Host "✅ Tests Complete!" -ForegroundColor Green
Write-Host "📄 Coverage report: htmlcov\index.html" -ForegroundColor Green

