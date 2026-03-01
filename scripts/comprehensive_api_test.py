"""
Comprehensive API Testing for SETTLE Service

Tests all API endpoints and user scenarios:
1. Health check
2. Waitlist join
3. Settlement estimation (query)
4. Settlement contribution
5. Report generation
6. Admin operations
7. Founding Member stats
"""

import requests
import json
from typing import Dict, Any
from uuid import uuid4

BASE_URL = "http://localhost:8002"

class APITester:
    """Comprehensive API test suite"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def test(self, name: str, method: str, endpoint: str, data: Dict = None, headers: Dict = None, expected_status: int = 200):
        """Test an API endpoint"""
        
        url = f"{BASE_URL}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            
            success = response.status_code == expected_status
            
            result = {
                "name": name,
                "method": method,
                "endpoint": endpoint,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "success": success,
                "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            }
            
            self.results.append(result)
            
            if success:
                self.passed += 1
                print(f"✅ PASS: {name}")
                print(f"   {method} {endpoint}")
                print(f"   Status: {response.status_code}")
            else:
                self.failed += 1
                print(f"❌ FAIL: {name}")
                print(f"   {method} {endpoint}")
                print(f"   Expected: {expected_status}, Got: {response.status_code}")
                print(f"   Response: {json.dumps(result['response'], indent=2)[:200]}")
            
            print()
            return result
            
        except requests.exceptions.ConnectionError:
            self.failed += 1
            print(f"❌ FAIL: {name}")
            print(f"   ERROR: Cannot connect to {url}")
            print(f"   Make sure server is running: python -m uvicorn app.main:app --reload --port 8002")
            print()
            return None
        except Exception as e:
            self.failed += 1
            print(f"❌ FAIL: {name}")
            print(f"   ERROR: {str(e)}")
            print()
            return None
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {self.passed} ({pass_rate:.1f}%)")
        print(f"❌ Failed: {self.failed}")
        print("=" * 70)
        
        if self.failed == 0:
            print("\n🎉 ALL TESTS PASSED! 🎉")
        else:
            print(f"\n⚠️  {self.failed} test(s) failed. Review output above.")
        
        print()


def main():
    """Run comprehensive API tests"""
    
    print("\n" + "="*70)
    print("🧪 SETTLE SERVICE - COMPREHENSIVE API TESTING")
    print("="*70)
    print()
    
    tester = APITester()
    
    # ==========================================================================
    # TEST 1: HEALTH CHECK
    # ==========================================================================
    print("="*70)
    print("TEST 1: HEALTH CHECK")
    print("="*70)
    print()
    
    tester.test(
        name="Health Check",
        method="GET",
        endpoint="/health",
        expected_status=200
    )
    
    tester.test(
        name="Root Endpoint",
        method="GET",
        endpoint="/",
        expected_status=200
    )
    
    # ==========================================================================
    # TEST 2: WAITLIST
    # ==========================================================================
    print("="*70)
    print("TEST 2: WAITLIST OPERATIONS")
    print("="*70)
    print()
    
    # Join waitlist with valid data
    waitlist_data = {
        "email": f"attorney.{uuid4().hex[:8]}@testfirm.com",
        "law_firm_name": "Test Law Firm",
        "practice_area": "Personal Injury",
        "state": "AZ",
        "referral_source": "Colleague Recommendation"
    }
    
    tester.test(
        name="Join Waitlist - Valid Data",
        method="POST",
        endpoint="/api/v1/waitlist/join",
        data=waitlist_data,
        expected_status=200
    )
    
    # Join waitlist with invalid email
    invalid_waitlist = {
        "email": "not-an-email",
        "law_firm_name": "Test Firm",
        "state": "AZ"
    }
    
    tester.test(
        name="Join Waitlist - Invalid Email",
        method="POST",
        endpoint="/api/v1/waitlist/join",
        data=invalid_waitlist,
        expected_status=422  # Validation error
    )
    
    # ==========================================================================
    # TEST 3: SETTLEMENT ESTIMATION (Requires API Key)
    # ==========================================================================
    print("="*70)
    print("TEST 3: SETTLEMENT ESTIMATION")
    print("="*70)
    print()
    
    # Test without API key (should fail)
    estimate_data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["Spinal Injury"],
        "medical_bills": 75000.00
    }
    
    tester.test(
        name="Settlement Estimate - No API Key",
        method="POST",
        endpoint="/api/v1/query/estimate",
        data=estimate_data,
        expected_status=403  # Forbidden
    )
    
    # Test with mock API key (if mock mode enabled)
    mock_headers = {
        "Authorization": "Bearer settle_test_key_123456"
    }
    
    tester.test(
        name="Settlement Estimate - With Mock API Key",
        method="POST",
        endpoint="/api/v1/query/estimate",
        data=estimate_data,
        headers=mock_headers,
        expected_status=200  # Should work in mock mode OR fail with 401 if auth is strict
    )
    
    # Test with complete data
    complete_estimate = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["Spinal Injury", "Soft Tissue Injury"],
        "primary_diagnosis": "Herniated Disc",
        "treatment_type": ["Physical Therapy", "Surgery"],
        "duration_of_treatment": "6-12 months",
        "imaging_findings": ["Herniated Disc", "Fracture"],
        "medical_bills": 125000.00,
        "lost_wages": 35000.00,
        "policy_limits": "$100k/$300k",
        "defendant_category": "Business"
    }
    
    tester.test(
        name="Settlement Estimate - Complete Data",
        method="POST",
        endpoint="/api/v1/query/estimate",
        data=complete_estimate,
        headers=mock_headers,
        expected_status=200
    )
    
    # ==========================================================================
    # TEST 4: CONTRIBUTION SUBMISSION (Requires API Key)
    # ==========================================================================
    print("="*70)
    print("TEST 4: SETTLEMENT CONTRIBUTION")
    print("="*70)
    print()
    
    contribution_data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["Spinal Injury"],
        "primary_diagnosis": "Herniated Disc",
        "treatment_type": ["Physical Therapy", "Surgery"],
        "duration_of_treatment": "6-12 months",
        "imaging_findings": ["Herniated Disc"],
        "medical_bills": 85000.00,
        "lost_wages": 25000.00,
        "policy_limits": "$100k/$300k",
        "defendant_category": "Individual",
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": True
    }
    
    tester.test(
        name="Submit Contribution - Without API Key",
        method="POST",
        endpoint="/api/v1/contribute/submit",
        data=contribution_data,
        expected_status=403  # Forbidden
    )
    
    tester.test(
        name="Submit Contribution - With Mock API Key",
        method="POST",
        endpoint="/api/v1/contribute/submit",
        data=contribution_data,
        headers=mock_headers,
        expected_status=200
    )
    
    # Test with invalid outcome range
    invalid_contribution = contribution_data.copy()
    invalid_contribution["outcome_amount_range"] = "$999k"  # Invalid range
    
    tester.test(
        name="Submit Contribution - Invalid Outcome Range",
        method="POST",
        endpoint="/api/v1/contribute/submit",
        data=invalid_contribution,
        headers=mock_headers,
        expected_status=422  # Validation error
    )
    
    # ==========================================================================
    # TEST 5: REPORT GENERATION (Requires API Key)
    # ==========================================================================
    print("="*70)
    print("TEST 5: REPORT GENERATION")
    print("="*70)
    print()
    
    report_data = {
        "estimate_id": str(uuid4()),
        "format": "pdf"
    }
    
    tester.test(
        name="Generate Report - PDF Format",
        method="POST",
        endpoint="/api/v1/reports/generate",
        data=report_data,
        headers=mock_headers,
        expected_status=200
    )
    
    report_json = {
        "estimate_id": str(uuid4()),
        "format": "json"
    }
    
    tester.test(
        name="Generate Report - JSON Format",
        method="POST",
        endpoint="/api/v1/reports/generate",
        data=report_json,
        headers=mock_headers,
        expected_status=200
    )
    
    # Invalid format
    invalid_report = {
        "estimate_id": str(uuid4()),
        "format": "docx"  # Invalid
    }
    
    tester.test(
        name="Generate Report - Invalid Format",
        method="POST",
        endpoint="/api/v1/reports/generate",
        data=invalid_report,
        headers=mock_headers,
        expected_status=400
    )
    
    # ==========================================================================
    # TEST 6: FOUNDING MEMBER STATS
    # ==========================================================================
    print("="*70)
    print("TEST 6: FOUNDING MEMBER STATS")
    print("="*70)
    print()
    
    tester.test(
        name="Get Founding Member Stats",
        method="GET",
        endpoint="/api/v1/stats/founding-members",
        expected_status=200
    )
    
    # ==========================================================================
    # TEST 7: ADMIN ENDPOINTS (Requires Admin API Key)
    # ==========================================================================
    print("="*70)
    print("TEST 7: ADMIN OPERATIONS")
    print("="*70)
    print()
    
    admin_headers = {
        "Authorization": "Bearer settle_admin_key_123456"
    }
    
    tester.test(
        name="Get Pending Contributions",
        method="GET",
        endpoint="/api/v1/admin/contributions/pending",
        headers=admin_headers,
        expected_status=200
    )
    
    tester.test(
        name="Get Analytics Dashboard",
        method="GET",
        endpoint="/api/v1/admin/analytics/dashboard",
        headers=admin_headers,
        expected_status=200
    )
    
    # ==========================================================================
    # TEST 8: ERROR HANDLING
    # ==========================================================================
    print("="*70)
    print("TEST 8: ERROR HANDLING")
    print("="*70)
    print()
    
    # Test 404 for non-existent endpoint
    tester.test(
        name="Non-Existent Endpoint",
        method="GET",
        endpoint="/api/v1/nonexistent",
        expected_status=404
    )
    
    # Test malformed JSON
    print("⏭️  SKIP: Malformed JSON test (requires special handling)")
    print()
    
    # ==========================================================================
    # FINAL SUMMARY
    # ==========================================================================
    tester.print_summary()
    
    # Return exit code
    return 0 if tester.failed == 0 else 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)

