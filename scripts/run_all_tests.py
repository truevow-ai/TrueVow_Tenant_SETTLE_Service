"""
Run All Tests - Comprehensive Automated Testing

This script runs all tests with detailed reporting and coverage analysis.
"""

import subprocess
import sys
import os
from datetime import datetime

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def run_command(cmd, description):
    """Run command and return success status"""
    print(f"> {description}...")
    print(f"  Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            print(f"[PASS] {description}")
            return True
        else:
            print(f"[FAIL] {description} (exit code: {result.returncode})")
            return False
    except Exception as e:
        print(f"[ERROR] {description}: {str(e)}")
        return False

def main():
    """Run all tests"""
    
    print_header("SETTLE SERVICE - COMPREHENSIVE AUTOMATED TEST SUITE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    
    results = []
    
    # Test 1: Configuration Tests
    print_header("TEST 1: Configuration & Environment")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestConfiguration", "-v"],
        "Configuration Tests"
    ))
    
    # Test 2: Health Check Tests
    print_header("TEST 2: Health Checks")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestHealthChecks", "-v"],
        "Health Check Tests"
    ))
    
    # Test 3: Public Endpoint Tests
    print_header("TEST 3: Public Endpoints")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestPublicEndpoints", "-v"],
        "Public Endpoint Tests"
    ))
    
    # Test 4: Authentication Tests
    print_header("TEST 4: Authentication")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestAuthentication", "-v"],
        "Authentication Tests"
    ))
    
    # Test 5: Service-to-Service Authentication Tests
    print_header("TEST 5: Service-to-Service Authentication")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestServiceAuthentication", "-v"],
        "Service Auth Tests"
    ))
    
    # Test 6: Query Endpoint Tests
    print_header("TEST 6: Query Endpoints")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestQueryEndpoints", "-v"],
        "Query Endpoint Tests"
    ))
    
    # Test 7: Contribution Endpoint Tests
    print_header("TEST 7: Contribution Endpoints")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestContributionEndpoints", "-v"],
        "Contribution Endpoint Tests"
    ))
    
    # Test 8: Report Endpoint Tests
    print_header("TEST 8: Report Endpoints")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestReportEndpoints", "-v"],
        "Report Endpoint Tests"
    ))
    
    # Test 9: Admin Endpoint Tests
    print_header("TEST 9: Admin Endpoints")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestAdminEndpoints", "-v"],
        "Admin Endpoint Tests"
    ))
    
    # Test 10: Service Integration Client Tests
    print_header("TEST 10: Service Integration Clients")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestServiceIntegrationClients", "-v"],
        "Service Integration Tests"
    ))
    
    # Test 11: Edge Case Tests
    print_header("TEST 11: Edge Cases & Boundary Conditions")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestEdgeCases", "-v"],
        "Edge Case Tests"
    ))
    
    # Test 12: Error Handling Tests
    print_header("TEST 12: Error Handling")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestErrorHandling", "-v"],
        "Error Handling Tests"
    ))
    
    # Test 13: Performance Tests
    print_header("TEST 13: Performance")
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/comprehensive_test_suite.py::TestPerformance", "-v"],
        "Performance Tests"
    ))
    
    # Test 14: Run All Tests with Coverage
    print_header("TEST 14: Full Test Suite with Coverage")
    results.append(run_command(
        [
            sys.executable, "-m", "pytest",
            "tests/comprehensive_test_suite.py",
            "-v",
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term"
        ],
        "Full Test Suite with Coverage"
    ))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(results)
    failed = len(results) - passed
    total = len(results)
    
    print(f"Total Test Suites: {total}")
    print(f"[PASS] Passed: {passed}")
    print(f"[FAIL] Failed: {failed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    print()
    
    if failed == 0:
        print("*** ALL TESTS PASSED! ***")
        print()
        print("[PASS] Configuration")
        print("[PASS] Health Checks")
        print("[PASS] Public Endpoints")
        print("[PASS] Authentication")
        print("[PASS] Service Auth")
        print("[PASS] Query Endpoints")
        print("[PASS] Contribution Endpoints")
        print("[PASS] Report Endpoints")
        print("[PASS] Admin Endpoints")
        print("[PASS] Service Integration")
        print("[PASS] Edge Cases")
        print("[PASS] Error Handling")
        print("[PASS] Performance")
        print()
        print("*** SETTLE Service is READY FOR PRODUCTION! ***")
        return 0
    else:
        print("*** SOME TESTS FAILED ***")
        print()
        print("Please review the test output above for details.")
        print("Fix any failing tests before deploying to production.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

