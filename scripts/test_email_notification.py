"""
Test Email Notification Service

This script tests the Resend API integration by sending a test email.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.notifications import get_email_service


async def test_welcome_email():
    """Test sending a Founding Member welcome email."""
    print("Testing Founding Member welcome email...")
    
    email_service = get_email_service()
    
    # Test email - replace with your email for testing
    test_email = "shah@intakely.ai"  # Using the verified sender from .env.local
    test_firm = "Test Law Firm"
    test_api_key = "settle_test_key_12345_SAMPLE_DO_NOT_USE"
    
    success = await email_service.send_founding_member_welcome(
        to_email=test_email,
        law_firm_name=test_firm,
        api_key=test_api_key
    )
    
    if success:
        print(f"✅ Welcome email sent successfully to {test_email}")
        return True
    else:
        print(f"❌ Failed to send welcome email to {test_email}")
        return False


async def test_rejection_email():
    """Test sending a waitlist rejection email."""
    print("\nTesting waitlist rejection email...")
    
    email_service = get_email_service()
    
    # Test email
    test_email = "shah@intakely.ai"
    test_firm = "Test Law Firm"
    test_reason = "Application is incomplete - missing state bar number"
    
    success = await email_service.send_waitlist_rejection(
        to_email=test_email,
        law_firm_name=test_firm,
        reason=test_reason
    )
    
    if success:
        print(f"✅ Rejection email sent successfully to {test_email}")
        return True
    else:
        print(f"❌ Failed to send rejection email to {test_email}")
        return False


async def test_basic_email():
    """Test basic email sending functionality."""
    print("\nTesting basic email send...")
    
    email_service = get_email_service()
    
    test_email = "shah@intakely.ai"
    
    success = await email_service.send_email(
        to_email=test_email,
        subject="SETTLE Email Service Test",
        html_content="""
        <html>
        <body>
            <h1>SETTLE Email Test</h1>
            <p>This is a test email from the SETTLE service email notification system.</p>
            <p>If you're seeing this, the Resend API integration is working correctly!</p>
        </body>
        </html>
        """
    )
    
    if success:
        print(f"✅ Basic email sent successfully to {test_email}")
        return True
    else:
        print(f"❌ Failed to send basic email to {test_email}")
        return False


async def main():
    """Run all email tests."""
    print("="*60)
    print("SETTLE Email Notification Test")
    print("="*60)
    print()
    
    # Check if Resend API key is configured
    from app.core.config import settings
    
    if not hasattr(settings, 'RESEND_CS_SUPPORT_API_KEY') or not settings.RESEND_CS_SUPPORT_API_KEY:
        print("❌ ERROR: RESEND_CS_SUPPORT_API_KEY not configured in .env.local")
        print("Please add your Resend API key to continue.")
        return
    
    print(f"✓ Resend API Key found: {settings.RESEND_CS_SUPPORT_API_KEY[:10]}...")
    print(f"✓ From Email: {settings.RESEND_FROM_EMAIL}")
    print(f"✓ From Name: {settings.RESEND_FROM_NAME}")
    print()
    
    # Run tests
    results = []
    
    # Test 1: Basic email
    results.append(await test_basic_email())
    
    # Test 2: Welcome email
    results.append(await test_welcome_email())
    
    # Test 3: Rejection email
    results.append(await test_rejection_email())
    
    # Summary
    print()
    print("="*60)
    print("Test Summary")
    print("="*60)
    print(f"Total tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("\n✅ All email tests passed! Email notifications are working correctly.")
    else:
        print("\n❌ Some email tests failed. Check the logs above for details.")


if __name__ == "__main__":
    asyncio.run(main())
