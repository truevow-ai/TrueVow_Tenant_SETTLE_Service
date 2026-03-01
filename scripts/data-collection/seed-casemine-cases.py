"""
Seed Casemine collected cases into settle_contributions table
Maps scraped data to database schema with proper field mapping
"""

import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv
import pathlib
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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


def parse_amount(amount_str):
    """Parse amount string to numeric value"""
    if not amount_str:
        return 0.0
    
    # Remove currency symbols and commas
    amount_str = str(amount_str).replace('$', '').replace(',', '').strip()
    
    # Handle "million", "M", "thousand", "K"
    multiplier = 1
    if 'million' in amount_str.lower() or 'm' in amount_str.lower():
        multiplier = 1000000
        amount_str = re.sub(r'[^\d.]', '', amount_str)
    elif 'thousand' in amount_str.lower() or 'k' in amount_str.lower():
        multiplier = 1000
        amount_str = re.sub(r'[^\d.]', '', amount_str)
    
    try:
        # Extract numeric value
        numeric = re.search(r'[\d.]+', amount_str)
        if numeric:
            return float(numeric.group()) * multiplier
    except:
        pass
    
    return 0.0


def bucket_amount_range(amount):
    """Convert numeric amount to bucketed range"""
    if amount <= 50000:
        return '$0-$50k'
    elif amount <= 100000:
        return '$50k-$100k'
    elif amount <= 150000:
        return '$100k-$150k'
    elif amount <= 225000:
        return '$150k-$225k'
    elif amount <= 300000:
        return '$225k-$300k'
    elif amount <= 600000:
        return '$300k-$600k'
    elif amount <= 1000000:
        return '$600k-$1M'
    else:
        return '$1M+'


def map_case_to_db(case):
    """Map scraped case data to database schema"""
    
    # Parse extracted amount
    extracted_amount = case.get('extracted_amount', '0')
    amount_value = parse_amount(extracted_amount)
    
    # Determine outcome_amount_range
    outcome_range = case.get('outcome_amount_range', '$0-$50k')
    if amount_value > 0:
        outcome_range = bucket_amount_range(amount_value)
    
    # Ensure required fields have defaults
    jurisdiction = case.get('jurisdiction', 'Unknown')
    if jurisdiction == 'Unknown' or not jurisdiction:
        # Try to extract from court or case_name
        court = case.get('court', '')
        if court and 'County' in court:
            jurisdiction = court.split('County')[0].strip() + ' County'
        else:
            jurisdiction = 'Unknown'
    
    case_type = case.get('case_type', 'Personal Injury')
    if not case_type:
        case_type = 'Personal Injury'
    
    # Map fields
    db_case = {
        # Required fields
        "jurisdiction": jurisdiction,
        "case_type": case_type,
        "injury_category": case.get('injury_category', []) or [],
        "defendant_category": case.get('defendant_category', 'Unknown') or 'Unknown',
        "outcome_type": case.get('outcome_type', 'Settlement') or 'Settlement',
        "outcome_amount_range": outcome_range,
        "medical_bills": float(case.get('medical_bills', 0.0)) or 0.0,
        
        # Optional fields
        "primary_diagnosis": case.get('primary_diagnosis'),
        "treatment_type": case.get('treatment_type', []) or [],
        "duration_of_treatment": case.get('duration_of_treatment'),
        "imaging_findings": case.get('imaging_findings', []) or [],
        "lost_wages": float(case.get('lost_wages', 0.0)) if case.get('lost_wages') else None,
        "policy_limits": case.get('policy_limits'),
        
        # Metadata
        "status": "approved",  # Auto-approve scraped cases
        "consent_confirmed": True,
        "confidence_score": 0.7,  # Scraped data - moderate confidence
    }
    
    # Remove None values for optional fields
    db_case = {k: v for k, v in db_case.items() if v is not None or k in ['jurisdiction', 'case_type', 'injury_category', 'defendant_category', 'outcome_type', 'outcome_amount_range', 'medical_bills']}
    
    return db_case


def seed_casemine_cases(json_file: str):
    """Seed database with Casemine collected cases"""
    
    if not SUPABASE_AVAILABLE:
        logger.error("Supabase client library not available")
        logger.info("Install with: pip install supabase")
        return False
    
    # Get Supabase credentials
    supabase_url = (
        os.getenv("SETTLE_SUPABASE_URL") or
        os.getenv("SUPABASE_URL")
    )
    
    if not supabase_url:
        db_url = os.getenv("SETTLE_DATABASE_URL") or os.getenv("DATABASE_URL")
        if db_url and "supabase.co" in db_url:
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
    with open(json_file, 'r', encoding='utf-8') as f:
        cases = json.load(f)
    
    logger.info(f"Found {len(cases)} cases to seed")
    
    # Map and prepare data
    db_cases = []
    for case in cases:
        db_case = map_case_to_db(case)
        db_cases.append(db_case)
    
    # Insert cases
    inserted = 0
    errors = 0
    
    logger.info("Inserting cases into database...")
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
    json_file = sys.argv[1] if len(sys.argv) > 1 else "settlement_cases_stealth_126_cleaned.json"
    
    if not os.path.exists(json_file):
        logger.error(f"File not found: {json_file}")
        sys.exit(1)
    
    logger.info("=" * 70)
    logger.info("Seeding Casemine Cases into Database")
    logger.info("=" * 70)
    
    success = seed_casemine_cases(json_file)
    
    if success:
        logger.info("\n" + "=" * 70)
        logger.info("Database seeding successful!")
        logger.info("=" * 70)
    else:
        logger.error("\nDatabase seeding failed.")
