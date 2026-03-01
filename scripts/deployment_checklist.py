"""
TrueVow SETTLE Service - Deployment Checklist Script

Validates that all production requirements are met before deployment.
"""

import os
import sys
from pathlib import Path

# Fix Unicode encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


def check_environment_variables():
    """Check that all required environment variables are set"""
    print("\n🔍 Checking Environment Variables...")
    
    # Check if we're in mock mode
    use_mock = getattr(settings, "USE_MOCK_DATA", False)
    if use_mock:
        print("  ℹ️  Running in MOCK MODE - Database credentials optional")
    
    required_vars = [
        "SERVICE_NAME",
        "SERVICE_VERSION",
        "ENVIRONMENT",
    ]
    
    # Database vars only required in production mode
    db_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
    ]
    
    optional_vars = [
        "PLATFORM_SERVICE_URL",
        "PLATFORM_SERVICE_API_KEY",
        "INTERNAL_OPS_SERVICE_URL",
        "INTERNAL_OPS_SERVICE_API_KEY",
        "TENANT_SERVICE_URL",
        "TENANT_SERVICE_API_KEY",
    ]
    
    missing = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing.append(var)
            print(f"  ❌ {var}: MISSING")
        else:
            print(f"  ✅ {var}: SET")
    
    # Check database vars
    print("\n💾 Database Configuration:")
    for var in db_vars:
        if not getattr(settings, var, None):
            if not use_mock:
                missing.append(var)
                print(f"  ❌ {var}: MISSING (required for production)")
            else:
                print(f"  ⚠️  {var}: NOT SET (OK in mock mode)")
        else:
            print(f"  ✅ {var}: SET")
    
    print("\n📋 Optional Integration Variables:")
    for var in optional_vars:
        if getattr(settings, var, None):
            print(f"  ✅ {var}: SET")
        else:
            print(f"  ⚠️  {var}: NOT SET (integration disabled)")
    
    return len(missing) == 0


def check_documentation():
    """Check that all documentation files exist"""
    print("\n📚 Checking Documentation...")
    
    docs = [
        "docs/API_DOCUMENTATION.md",
        "docs/DATABASE_SCHEMA.md",
        "docs/INTEGRATION_GUIDE.md",
        "docs/TESTING_GUIDE.md",
        "README.md",
        "env.template",
    ]
    
    missing = []
    for doc in docs:
        if Path(doc).exists():
            print(f"  ✅ {doc}")
        else:
            print(f"  ❌ {doc}: MISSING")
            missing.append(doc)
    
    return len(missing) == 0


def check_core_files():
    """Check that all core application files exist"""
    print("\n🔧 Checking Core Files...")
    
    files = [
        "app/main.py",
        "app/core/config.py",
        "app/core/security.py",
        "app/core/service_auth.py",
        "app/core/database.py",
        "app/services/integrations/platform/client.py",
        "app/services/integrations/internal_ops/client.py",
    ]
    
    missing = []
    for file in files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file}: MISSING")
            missing.append(file)
    
    return len(missing) == 0


def check_test_files():
    """Check that test files exist"""
    print("\n🧪 Checking Test Files...")
    
    tests = [
        "tests/comprehensive_test_suite.py",
        "scripts/run_all_tests.py",
    ]
    
    missing = []
    for test in tests:
        if Path(test).exists():
            print(f"  ✅ {test}")
        else:
            print(f"  ❌ {test}: MISSING")
            missing.append(test)
    
    return len(missing) == 0


def print_summary(results):
    """Print deployment readiness summary"""
    print("\n" + "="*60)
    print("📊 DEPLOYMENT READINESS SUMMARY")
    print("="*60)
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {check}")
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 ALL CHECKS PASSED! 🎉")
        print("✅ Service is READY FOR DEPLOYMENT")
        print("\nNext Steps:")
        print("  1. Run: python -m pytest tests/comprehensive_test_suite.py")
        print("  2. Review: PRODUCTION_READINESS_REPORT.md")
        print("  3. Deploy to pre-production environment")
        print("  4. Execute Week 16 integration tests")
        print("  5. Deploy to production")
        return 0
    else:
        print("\n⚠️  DEPLOYMENT CHECKS FAILED")
        print("❌ Service is NOT ready for deployment")
        print("\nPlease fix the issues above before deploying.")
        return 1


def main():
    """Run all deployment checks"""
    print("="*60)
    print("🚀 TrueVow SETTLE Service - Deployment Checklist")
    print("="*60)
    
    results = {
        "Environment Variables": check_environment_variables(),
        "Documentation": check_documentation(),
        "Core Files": check_core_files(),
        "Test Files": check_test_files(),
    }
    
    return print_summary(results)


if __name__ == "__main__":
    sys.exit(main())

