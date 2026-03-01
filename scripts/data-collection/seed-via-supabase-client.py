"""
Seed Database via Supabase Client Library
Alternative method if direct PostgreSQL connection fails
"""

import json
import os
from datetime import datetime
from dotenv import load_dotenv
import pathlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env.local from project root
project_root = pathlib.Path(__file__).parent.parent.parent
env_local = project_root / '.env.local'
if env_local.exists():
    load_dotenv(env_local)

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not installed. Install with: pip install supabase")


def seed_via_supabase(json_file: str):
    """Seed database using Supabase client library"""
    
    if not SUPABASE_AVAILABLE:
        logger.error("Supabase client library not available")
        logger.info("Install with: pip install supabase")
        return False
    
    # Get Supabase credentials
    # For Supabase client, we need the HTTPS URL, not the PostgreSQL connection string
    supabase_url = (
        os.getenv("SETTLE_SUPABASE_URL") or
        os.getenv("SUPABASE_URL")
    )
    
    # If we have DATABASE_URL, extract the project URL from it
    if not supabase_url:
        db_url = os.getenv("SETTLE_DATABASE_URL") or os.getenv("DATABASE_URL")
        if db_url and "supabase.co" in db_url:
            # Extract project ID and construct Supabase URL
            # Format: db.PROJECT_ID.supabase.co -> https://PROJECT_ID.supabase.co
            import re
            match = re.search(r'db\.([^.]+)\.supabase\.co', db_url)
            if match:
                project_id = match.group(1)
                supabase_url = f"https://{project_id}.supabase.co"
                logger.info(f"Extracted Supabase URL from connection string: {supabase_url}")
    
    supabase_key = (
        os.getenv("SETTLE_DATABASE_SERVICE_KEY") or
        os.getenv("SETTLE_SUPABASE_SERVICE_KEY") or
        os.getenv("SUPABASE_SERVICE_KEY")
    )
    
    # Fallback to anon key if service key not available (limited permissions)
    if not supabase_key:
        supabase_key = (
            os.getenv("SETTLE_DATABASE_ANON_KEY") or
            os.getenv("SETTLE_SUPABASE_ANON_KEY") or
            os.getenv("SUPABASE_ANON_KEY") or
            os.getenv("SUPABASE_KEY")
        )
        if supabase_key:
            logger.warning("Using anon key instead of service key - may have limited permissions")
    
    if not supabase_url or not supabase_key:
        logger.error("Missing Supabase credentials")
        logger.info("Need: SETTLE_DATABASE_URL (or SUPABASE_URL)")
        logger.info("Need: SETTLE_DATABASE_SERVICE_KEY (or SUPABASE_SERVICE_KEY)")
        return False
    
    # Create Supabase client
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Connected to Supabase")
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return False
    
    # Load cases
    logger.info(f"Loading cases from {json_file}...")
    with open(json_file, 'r') as f:
        cases = json.load(f)
    
    logger.info(f"Found {len(cases)} cases to seed")
    
    # Prepare data for Supabase
    db_cases = []
    for case in cases:
        db_case = {
            "jurisdiction": case.get('jurisdiction'),
            "case_type": case.get('case_type'),
            "injury_category": case.get('injury_category', []),
            "primary_diagnosis": case.get('primary_diagnosis'),
            "treatment_type": case.get('treatment_type', []),
            "duration_of_treatment": case.get('duration_of_treatment'),
            "imaging_findings": case.get('imaging_findings', []),
            "medical_bills": case.get('medical_bills', 0.0),
            "lost_wages": case.get('lost_wages'),
            "policy_limits": case.get('policy_limits'),
            "defendant_category": case.get('defendant_category', 'Unknown'),
            "outcome_type": case.get('outcome_type', 'Settlement'),
            "outcome_amount_range": case.get('outcome_amount_range'),
            "status": "approved",
            "consent_confirmed": True,
            "created_at": datetime.now().isoformat()
        }
        db_cases.append(db_case)
    
    # Insert cases
    inserted = 0
    errors = 0
    
    for i, case in enumerate(db_cases, 1):
        try:
            result = supabase.table("settle_contributions").insert(case).execute()
            inserted += 1
            
            if inserted % 5 == 0:
                logger.info(f"Inserted {inserted}/{len(db_cases)} cases...")
                
        except Exception as e:
            logger.error(f"Error inserting case {i}: {e}")
            errors += 1
    
    logger.info(f"\nSeeding complete: {inserted} inserted, {errors} errors")
    
    # Verify
    try:
        result = supabase.table("settle_contributions").select("id", count="exact").execute()
        total = result.count if hasattr(result, 'count') else len(result.data) if result.data else 0
        logger.info(f"Total cases in database: {total}")
    except Exception as e:
        logger.warning(f"Could not verify count: {e}")
    
    return inserted > 0


if __name__ == "__main__":
    import sys
    json_file = sys.argv[1] if len(sys.argv) > 1 else "verified_cases.json"
    
    if not os.path.exists(json_file):
        logger.error(f"File not found: {json_file}")
        sys.exit(1)
    
    success = seed_via_supabase(json_file)
    
    if success:
        logger.info("\n" + "=" * 60)
        logger.info("Database seeding successful via Supabase client!")
        logger.info("=" * 60)
    else:
        logger.error("\nDatabase seeding failed.")

