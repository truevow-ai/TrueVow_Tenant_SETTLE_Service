"""
Install Phase 2 Dependencies

Quick script to install all Phase 2 dependencies and verify installation.
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def run_command(command, description):
    """Run a command and log output."""
    logger.info(f"\n{'='*60}")
    logger.info(f"🔧 {description}")
    logger.info(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error: {e}")
        logger.error(e.stderr)
        return False


def verify_imports():
    """Verify that all Phase 2 packages can be imported."""
    logger.info(f"\n{'='*60}")
    logger.info("✅ Verifying Phase 2 Package Imports")
    logger.info(f"{'='*60}\n")
    
    packages = {
        "SendGrid (Email)": "sendgrid",
        "WeasyPrint (PDF)": "weasyprint",
        "Pillow (Images)": "PIL",
        "QR Code": "qrcode",
        "Boto3 (AWS)": "boto3",
        "Stripe (Payments)": "stripe",
        "Sentry SDK (Monitoring)": "sentry_sdk"
    }
    
    all_success = True
    
    for name, module in packages.items():
        try:
            __import__(module)
            logger.info(f"✅ {name:30s} - OK")
        except ImportError as e:
            logger.error(f"❌ {name:30s} - FAILED: {e}")
            all_success = False
    
    return all_success


def main():
    """Main installation script."""
    logger.info("\n" + "="*60)
    logger.info("🚀 SETTLE Phase 2 - Dependency Installation")
    logger.info("="*60)
    
    # Step 1: Upgrade pip
    if not run_command(
        f"{sys.executable} -m pip install --upgrade pip",
        "Upgrading pip"
    ):
        logger.error("Failed to upgrade pip")
        return False
    
    # Step 2: Install requirements
    if not run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing Phase 2 dependencies"
    ):
        logger.error("Failed to install dependencies")
        return False
    
    # Step 3: Verify imports
    if not verify_imports():
        logger.error("\n❌ Some packages failed to import. Please check the errors above.")
        return False
    
    # Success!
    logger.info("\n" + "="*60)
    logger.info("🎉 Phase 2 Dependencies Installed Successfully!")
    logger.info("="*60)
    logger.info("\n📋 Next Steps:")
    logger.info("1. Configure environment variables in .env.local")
    logger.info("2. Run: python scripts/check_env.py")
    logger.info("3. Start server: python -m uvicorn app.main:app --reload --port 8002")
    logger.info("4. Test at: http://localhost:8002/docs")
    logger.info("\n📚 See PHASE_2_PROGRESS_REPORT.md for details.\n")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


