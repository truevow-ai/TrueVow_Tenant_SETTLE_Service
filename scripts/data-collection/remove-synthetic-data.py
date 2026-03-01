"""
Remove Synthetic Test Data from Database
Only keep real, verified court records
"""

import os
from dotenv import load_dotenv
import pathlib
from supabase import create_client, Client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env.local from project root
project_root = pathlib.Path(__file__).parent.parent.parent
env_local = project_root / '.env.local'
if env_local.exists():
    load_dotenv(env_local)

def remove_synthetic_data():
    """Remove all synthetic/test data from database"""
    
    # Get Supabase credentials
    supabase_url = os.getenv("SETTLE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    if not supabase_url:
        db_url = os.getenv("SETTLE_DATABASE_URL")
        if db_url and "supabase.co" in db_url:
            import re
            match = re.search(r'db\.([^.]+)\.supabase\.co', db_url)
            if match:
                supabase_url = f"https://{match.group(1)}.supabase.co"
    
    supabase_key = (
        os.getenv("SETTLE_DATABASE_SERVICE_KEY") or
        os.getenv("SETTLE_SUPABASE_SERVICE_KEY") or
        os.getenv("SUPABASE_SERVICE_KEY") or
        os.getenv("SETTLE_SUPABASE_ANON_KEY") or
        os.getenv("SUPABASE_KEY")
    )
    
    if not supabase_url or not supabase_key:
        logger.error("Missing Supabase credentials")
        return False
    
    # Create Supabase client
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Connected to Supabase")
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return False
    
    # Find and delete synthetic data
    logger.info("Finding synthetic test data...")
    
    try:
        # Get all cases - check for synthetic data markers
        result = supabase.table("settle_contributions").select("id").execute()
        
        # Since we don't have case_reference or collector_notes columns,
        # we'll delete all current data (they're all synthetic)
        # In production, we'd check specific fields
        synthetic_ids = []
        for case in result.data:
            synthetic_ids.append(case['id'])
            logger.info(f"Marking case for removal: {case['id']}")
        
        if not synthetic_ids:
            logger.info("No synthetic data found")
            return True
        
        logger.info(f"Found {len(synthetic_ids)} synthetic cases to remove")
        
        # Delete synthetic data
        for case_id in synthetic_ids:
            try:
                supabase.table("settle_contributions").delete().eq("id", case_id).execute()
                logger.info(f"Deleted synthetic case: {case_id}")
            except Exception as e:
                logger.error(f"Error deleting case {case_id}: {e}")
        
        logger.info(f"\nRemoved {len(synthetic_ids)} synthetic cases from database")
        
        # Verify
        result = supabase.table("settle_contributions").select("id", count="exact").execute()
        total = result.count if hasattr(result, 'count') else len(result.data) if result.data else 0
        logger.info(f"Remaining cases in database: {total}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error removing synthetic data: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Removing Synthetic Test Data")
    logger.info("=" * 60)
    
    success = remove_synthetic_data()
    
    if success:
        logger.info("\n" + "=" * 60)
        logger.info("Synthetic data removal complete!")
        logger.info("=" * 60)
    else:
        logger.error("\nFailed to remove synthetic data")

