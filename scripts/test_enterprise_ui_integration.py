#!/usr/bin/env python3
"""
Test script to verify SETTLE API connection and enterprise UI integration
"""

import requests
import json
from typing import Dict, Any

def test_settle_api_connection():
    """Test connection to SETTLE API endpoints"""
    
    base_url = "http://localhost:3008"
    
    print("🔍 Testing SETTLE API Connection...")
    print(f"Base URL: {base_url}")
    print("-" * 50)
    
    # Test endpoints
    endpoints = [
        ("/api/v1/health", "Health Check"),
        ("/api/v1/stats/database", "Database Statistics"),
        ("/api/v1/stats/founding-members", "Founding Members Stats")
    ]
    
    results = {}
    
    for endpoint, description in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            print(f"\n📡 Testing: {description}")
            print(f"   Endpoint: {url}")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results[endpoint] = {
                    "status": "SUCCESS",
                    "data": data
                }
                print(f"   ✅ Status: {response.status_code}")
                print(f"   📊 Response: {json.dumps(data, indent=2)[:200]}...")
            else:
                results[endpoint] = {
                    "status": "FAILED",
                    "error": f"HTTP {response.status_code}"
                }
                print(f"   ❌ Status: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            results[endpoint] = {
                "status": "FAILED",
                "error": "Connection refused - is SETTLE service running?"
            }
            print(f"   ❌ Connection Error: Make sure SETTLE service is running on port 3008")
            
        except requests.exceptions.Timeout:
            results[endpoint] = {
                "status": "FAILED",
                "error": "Request timeout"
            }
            print(f"   ❌ Timeout Error")
            
        except Exception as e:
            results[endpoint] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"   ❌ Error: {str(e)}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 API CONNECTION TEST SUMMARY")
    print("=" * 50)
    
    success_count = sum(1 for result in results.values() if result["status"] == "SUCCESS")
    total_count = len(results)
    
    print(f"Tests Passed: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 All API connections working perfectly!")
        print("\n✅ Ready for enterprise UI integration")
        print("✅ Sidebar will display real-time statistics")
        print("✅ Toast notifications will work with API responses")
    else:
        print("⚠️  Some API connections failed")
        print("🔧 Please check:")
        print("   1. SETTLE service is running on port 3008")
        print("   2. API endpoints are accessible")
        print("   3. No firewall blocking connections")
    
    return results

def generate_sample_data():
    """Generate sample data structure for UI components"""
    
    print("\n" + "=" * 50)
    print("📋 SAMPLE DATA STRUCTURE FOR UI COMPONENTS")
    print("=" * 50)
    
    sample_stats = {
        "database_stats": {
            "total_contributions": 1247,
            "approved_contributions": 892,
            "pending_contributions": 45,
            "flagged_contributions": 12,
            "jurisdictions_covered": 342,
            "states_covered": 47
        },
        "founding_members_stats": {
            "total_members": 156,
            "active_members": 142,
            "slots_remaining": 1944,
            "total_capacity": 2100,
            "total_contributions": 2341,
            "total_queries": 892,
            "total_reports": 156
        }
    }
    
    print(json.dumps(sample_stats, indent=2))
    return sample_stats

if __name__ == "__main__":
    print("🚀 SETTLE Enterprise UI - API Connection Test")
    print("=" * 50)
    
    # Test API connection
    api_results = test_settle_api_connection()
    
    # Generate sample data
    sample_data = generate_sample_data()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Ensure SETTLE service is running: python -m uvicorn app.main:app --port 3008")
    print("2. Update Customer Portal .env.local with SETTLE API URL")
    print("3. Start Customer Portal: npm run dev")
    print("4. Visit: http://localhost:3000/dashboard/settle")
    print("5. Verify real-time statistics in sidebar")