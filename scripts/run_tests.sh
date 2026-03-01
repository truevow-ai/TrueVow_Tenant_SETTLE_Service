#!/bin/bash

# ============================================================================
# Run Tests for SETTLE Service
# ============================================================================

echo "🧪 Running TrueVow SETTLE Service Tests..."
echo "============================================"

# Activate virtual environment (if exists)
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run unit tests
echo ""
echo "📋 Running Unit Tests..."
pytest tests/test_estimator.py tests/test_validator.py tests/test_anonymizer.py -v

# Run functional tests
echo ""
echo "🔗 Running Functional Tests..."
pytest tests/test_functional.py -v

# Run all tests with coverage
echo ""
echo "📊 Running All Tests with Coverage..."
pytest tests/ -v --cov=app --cov-report=term --cov-report=html

echo ""
echo "✅ Tests Complete!"
echo "📄 Coverage report: htmlcov/index.html"

