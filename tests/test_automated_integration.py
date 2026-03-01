"""
Automated Integration Tests for SETTLE Service
Tests all customer scenarios end-to-end
"""

import pytest
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
BASE_URL = "http://localhost:8002"
API_VERSION = "v1"

class SettleTestClient:
    """Automated test client for SETTLE service"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.test_results = []
        
    def set_api_key(self, api_key: str):
        """Set API key for authenticated requests"""
        self.api_key = api_key
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    def _log_test(self, scenario: str, endpoint: str, method: str, 
                  status_code: int, success: bool, details: str):
        """Log test result"""
        self.test_results.append({
            "scenario": scenario,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
    def health_check(self) -> bool:
        """Test: Health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            success = response.status_code == 200
            self._log_test(
                "Health Check",
                "/health",
                "GET",
                response.status_code,
                success,
                response.json().get("status", "unknown") if success else str(response.text)
            )
            return success
        except Exception as e:
            self._log_test("Health Check", "/health", "GET", 0, False, str(e))
            return False
    
    def test_query_estimate(self, request_data: Dict) -> Optional[Dict]:
        """Test: Query settlement range estimate"""
        endpoint = f"/api/{API_VERSION}/query/estimate"
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=request_data,
                headers=self._get_headers()
            )
            success = response.status_code == 200
            data = response.json() if success else None
            
            self._log_test(
                "Query Settlement Estimate",
                endpoint,
                "POST",
                response.status_code,
                success,
                f"Estimate ID: {data.get('estimate_id')}" if data else str(response.text)
            )
            return data
        except Exception as e:
            self._log_test("Query Settlement Estimate", endpoint, "POST", 0, False, str(e))
            return None
    
    def test_submit_contribution(self, contribution_data: Dict) -> Optional[Dict]:
        """Test: Submit settlement contribution"""
        endpoint = f"/api/{API_VERSION}/contribute"
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=contribution_data,
                headers=self._get_headers()
            )
            success = response.status_code in [200, 201]
            data = response.json() if success else None
            
            self._log_test(
                "Submit Contribution",
                endpoint,
                "POST",
                response.status_code,
                success,
                f"Contribution ID: {data.get('contribution_id')}, Status: {data.get('status')}" if data else str(response.text)
            )
            return data
        except Exception as e:
            self._log_test("Submit Contribution", endpoint, "POST", 0, False, str(e))
            return None
    
    def test_get_founding_member_status(self) -> Optional[Dict]:
        """Test: Get founding member status"""
        endpoint = f"/api/{API_VERSION}/stats/founding-member"
        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers()
            )
            success = response.status_code == 200
            data = response.json() if success else None
            
            self._log_test(
                "Get Founding Member Status",
                endpoint,
                "GET",
                response.status_code,
                success,
                f"Status: {data.get('status')}, Contributions: {data.get('approved_contributions')}/10" if data else str(response.text)
            )
            return data
        except Exception as e:
            self._log_test("Get Founding Member Status", endpoint, "GET", 0, False, str(e))
            return None
    
    def test_generate_report(self, estimate_id: str, report_type: str = "summary") -> Optional[Dict]:
        """Test: Generate report"""
        endpoint = f"/api/{API_VERSION}/reports/generate"
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json={"estimate_id": estimate_id, "report_type": report_type},
                headers=self._get_headers()
            )
            success = response.status_code in [200, 201]
            data = response.json() if success else None
            
            self._log_test(
                "Generate Report",
                endpoint,
                "POST",
                response.status_code,
                success,
                f"Report ID: {data.get('report_id')}, Type: {report_type}" if data else str(response.text)
            )
            return data
        except Exception as e:
            self._log_test("Generate Report", endpoint, "POST", 0, False, str(e))
            return None
    
    def test_get_my_reports(self) -> Optional[List[Dict]]:
        """Test: Get user's reports"""
        endpoint = f"/api/{API_VERSION}/reports/my-reports"
        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers()
            )
            success = response.status_code == 200
            data = response.json() if success else None
            
            self._log_test(
                "Get My Reports",
                endpoint,
                "GET",
                response.status_code,
                success,
                f"Reports count: {len(data)}" if data else str(response.text)
            )
            return data
        except Exception as e:
            self._log_test("Get My Reports", endpoint, "GET", 0, False, str(e))
            return None
    
    def test_join_waitlist(self, waitlist_data: Dict) -> Optional[Dict]:
        """Test: Join waitlist"""
        endpoint = f"/api/{API_VERSION}/waitlist/join"
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=waitlist_data,
                headers={"Content-Type": "application/json"}  # No API key needed
            )
            success = response.status_code in [200, 201]
            data = response.json() if success else None
            
            self._log_test(
                "Join Waitlist",
                endpoint,
                "POST",
                response.status_code,
                success,
                f"Waitlist ID: {data.get('waitlist_id')}" if data else str(response.text)
            )
            return data
        except Exception as e:
            self._log_test("Join Waitlist", endpoint, "POST", 0, False, str(e))
            return None
    
    def test_phi_detection(self, notes_with_phi: str) -> bool:
        """Test: PHI detection in contribution"""
        contribution_data = {
            "jurisdiction": "California",
            "case_type": "Personal Injury",
            "practice_area": "Personal Injury",
            "injury_category": ["Broken Bones"],
            "settlement_amount": 50000,
            "notes": notes_with_phi
        }
        
        endpoint = f"/api/{API_VERSION}/contribute"
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=contribution_data,
                headers=self._get_headers()
            )
            
            # Should fail validation if PHI detected
            success = response.status_code == 400 or (response.status_code == 422 and "PHI" in str(response.text))
            
            self._log_test(
                "PHI Detection Test",
                endpoint,
                "POST",
                response.status_code,
                success,
                "PHI correctly detected and blocked" if success else "PHI not detected - SECURITY ISSUE"
            )
            return success
        except Exception as e:
            self._log_test("PHI Detection Test", endpoint, "POST", 0, False, str(e))
            return False
    
    def test_invalid_api_key(self) -> bool:
        """Test: Invalid API key rejection"""
        original_key = self.api_key
        self.api_key = "invalid_key_12345"
        
        endpoint = f"/api/{API_VERSION}/stats/founding-member"
        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers()
            )
            
            # Should return 401 Unauthorized
            success = response.status_code == 401
            
            self._log_test(
                "Invalid API Key Test",
                endpoint,
                "GET",
                response.status_code,
                success,
                "Invalid key correctly rejected" if success else "Invalid key accepted - SECURITY ISSUE"
            )
            
            self.api_key = original_key
            return success
        except Exception as e:
            self.api_key = original_key
            self._log_test("Invalid API Key Test", endpoint, "GET", 0, False, str(e))
            return False
    
    def generate_test_report(self, filename: str = "SETTLE_TEST_REPORT.md"):
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""# SETTLE Automated Integration Test Report

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total Tests:** {total_tests}
**Passed:** {passed_tests} ✅
**Failed:** {failed_tests} ❌
**Success Rate:** {success_rate:.1f}%

---

## Test Results Summary

| Scenario | Endpoint | Method | Status | Result |
|----------|----------|--------|--------|--------|
"""
        
        for result in self.test_results:
            status_icon = "✅" if result["success"] else "❌"
            report += f"| {result['scenario']} | `{result['endpoint']}` | {result['method']} | {result['status_code']} | {status_icon} |\n"
        
        report += "\n---\n\n## Detailed Test Results\n\n"
        
        for i, result in enumerate(self.test_results, 1):
            status_icon = "✅" if result["success"] else "❌"
            report += f"""### Test {i}: {result['scenario']} {status_icon}

**Endpoint:** `{result['method']} {result['endpoint']}`
**Status Code:** {result['status_code']}
**Timestamp:** {result['timestamp']}
**Details:** {result['details']}

---

"""
        
        return report


# Test Scenarios
def run_all_tests(api_key: str) -> str:
    """Run all automated test scenarios"""
    
    client = SettleTestClient(BASE_URL, api_key)
    
    print("🚀 Starting SETTLE Automated Integration Tests...\n")
    
    # Test 1: Health Check
    print("Test 1: Health Check...")
    client.health_check()
    time.sleep(0.5)
    
    # Test 2: Invalid API Key
    print("Test 2: Invalid API Key Rejection...")
    client.test_invalid_api_key()
    time.sleep(0.5)
    
    # Test 3: Get Founding Member Status
    print("Test 3: Get Founding Member Status...")
    member_status = client.test_get_founding_member_status()
    time.sleep(0.5)
    
    # Test 4: Query Settlement Estimate (Personal Injury)
    print("Test 4: Query Settlement Estimate (Personal Injury)...")
    query_data_1 = {
        "jurisdiction": "California",
        "case_type": "Personal Injury",
        "injury_category": ["Broken Bones", "Soft Tissue"],
        "severity": "Moderate",
        "liability_strength": "Strong"
    }
    estimate_1 = client.test_query_estimate(query_data_1)
    time.sleep(0.5)
    
    # Test 5: Query Settlement Estimate (Medical Malpractice)
    print("Test 5: Query Settlement Estimate (Medical Malpractice)...")
    query_data_2 = {
        "jurisdiction": "New York",
        "case_type": "Medical Malpractice",
        "injury_category": ["Brain Injury"],
        "severity": "Catastrophic"
    }
    estimate_2 = client.test_query_estimate(query_data_2)
    time.sleep(0.5)
    
    # Test 6: Submit Valid Contribution
    print("Test 6: Submit Valid Contribution...")
    contribution_data = {
        "jurisdiction": "Texas",
        "case_type": "Personal Injury",
        "practice_area": "Personal Injury",
        "injury_category": ["Broken Bones"],
        "settlement_amount": 150000,
        "case_duration_months": 18,
        "case_outcome": "Settled",
        "notes": "Rear-end collision, clear liability, excellent recovery"
    }
    contribution = client.test_submit_contribution(contribution_data)
    time.sleep(0.5)
    
    # Test 7: PHI Detection Test
    print("Test 7: PHI Detection (Should Block)...")
    phi_notes = "John Smith, SSN 123-45-6789, lives at 123 Main St, phone 555-123-4567"
    client.test_phi_detection(phi_notes)
    time.sleep(0.5)
    
    # Test 8: Generate Report (if estimate exists)
    if estimate_1:
        print("Test 8: Generate Report...")
        report = client.test_generate_report(estimate_1.get("estimate_id"), "summary")
        time.sleep(0.5)
    
    # Test 9: Get My Reports
    print("Test 9: Get My Reports...")
    reports = client.test_get_my_reports()
    time.sleep(0.5)
    
    # Test 10: Join Waitlist (no API key)
    print("Test 10: Join Waitlist...")
    waitlist_data = {
        "firm_name": "Test Law Firm",
        "contact_name": "Jane Attorney",
        "email": "jane@testfirm.com",
        "phone": "555-999-8888",
        "practice_areas": ["Personal Injury", "Medical Malpractice"]
    }
    client.test_join_waitlist(waitlist_data)
    time.sleep(0.5)
    
    print("\n✅ All tests completed!\n")
    
    # Generate report
    report = client.generate_test_report()
    return report


# Main execution
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_automated_integration.py <API_KEY>")
        print("\nExample:")
        print("  python test_automated_integration.py sk_test_abc123xyz")
        sys.exit(1)
    
    api_key = sys.argv[1]
    
    try:
        report = run_all_tests(api_key)
        
        # Save report
        report_path = "SETTLE_TEST_REPORT.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"📊 Test report saved to: {report_path}")
        print("\n" + "="*60)
        print(report)
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

