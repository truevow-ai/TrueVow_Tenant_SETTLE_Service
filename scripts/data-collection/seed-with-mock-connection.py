"""
Seed Database - With Connection Testing
Tests connection and seeds database with collected cases
"""

import json
import asyncio
import asyncpg
import logging
from typing import List, Dict
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables (try .env.local first, then .env)
# Look in parent directory (project root) for .env.local
import pathlib
project_root = pathlib.Path(__file__).parent.parent.parent
env_local = project_root / '.env.local'
env_file = project_root / '.env'

if env_local.exists():
    load_dotenv(env_local)
elif env_file.exists():
    load_dotenv(env_file)
else:
    # Fallback to current directory
    load_dotenv('.env.local')
    load_dotenv('.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_connection(database_url: str) -> bool:
    """Test database connection"""
    try:
        # URL decode the connection string if needed
        import urllib.parse
        # Parse and reconstruct to ensure proper encoding
        parsed = urllib.parse.urlparse(database_url)
        # Reconstruct with proper encoding
        if parsed.password:
            # Password might be URL encoded, decode it
            password = urllib.parse.unquote(parsed.password)
            # Reconstruct URL
            netloc = f"{parsed.username}:{password}@{parsed.hostname}"
            if parsed.port:
                netloc = f"{parsed.username}:{password}@{parsed.hostname}:{parsed.port}"
            database_url = urllib.parse.urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
        
        logger.info(f"Connecting to: {parsed.hostname}:{parsed.port or 5432}")
        conn = await asyncpg.connect(database_url)
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        logger.info(f"Connection string format: {database_url[:50]}...")
        return False


async def seed_database(json_file: str, database_url: str = None):
    """Seed database from JSON file"""
    
    # Get database URL
    if not database_url:
        database_url = (
            os.getenv("SETTLE_DATABASE_URL") or
            os.getenv("SETTLE_SUPABASE_URL") or
            os.getenv("DATABASE_URL") or
            os.getenv("SUPABASE_URL")
        )
    
    if not database_url:
        logger.error("No database URL found. Set DATABASE_URL or SETTLE_DATABASE_URL in .env")
        logger.info("\nTo seed database, you need:")
        logger.info("1. Database connection string in .env file")
        logger.info("2. Or pass --database-url parameter")
        logger.info("\nFor Supabase, try the connection pooler URL:")
        logger.info("  postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:6543/postgres")
        logger.info("Or direct connection:")
        logger.info("  postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres")
        return False
    
    # For Supabase, try connection pooler port (6543) if direct connection (5432) fails
    if "supabase.co" in database_url and ":5432" in database_url:
        logger.info("Detected Supabase connection. If connection fails, try port 6543 (connection pooler)")
    
    # Test connection
    logger.info("Testing database connection...")
    if not await test_connection(database_url):
        logger.error("Cannot connect to database. Check connection string.")
        return False
    
    logger.info("Connection successful!")
    
    # Load cases
    logger.info(f"Loading cases from {json_file}...")
    with open(json_file, 'r') as f:
        cases = json.load(f)
    
    logger.info(f"Found {len(cases)} cases to seed")
    
    # Connect to database
    conn = await asyncpg.connect(database_url)
    
    try:
        inserted = 0
        errors = 0
        
        for case in cases:
            try:
                query = """
                INSERT INTO settle_contributions (
                    jurisdiction,
                    case_type,
                    injury_category,
                    primary_diagnosis,
                    treatment_type,
                    duration_of_treatment,
                    imaging_findings,
                    medical_bills,
                    lost_wages,
                    policy_limits,
                    defendant_category,
                    outcome_type,
                    outcome_amount_range,
                    status,
                    consent_confirmed,
                    created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
                )
                """
                
                await conn.execute(
                    query,
                    case.get('jurisdiction'),
                    case.get('case_type'),
                    case.get('injury_category', []),
                    case.get('primary_diagnosis'),
                    case.get('treatment_type', []),
                    case.get('duration_of_treatment'),
                    case.get('imaging_findings', []),
                    case.get('medical_bills', 0.0),
                    case.get('lost_wages'),
                    case.get('policy_limits'),
                    case.get('defendant_category', 'Unknown'),
                    case.get('outcome_type', 'Settlement'),
                    case.get('outcome_amount_range'),
                    'approved',  # Pre-approved for initial seed
                    True,  # Consent confirmed
                    datetime.now()
                )
                
                inserted += 1
                
                if inserted % 5 == 0:
                    logger.info(f"Inserted {inserted}/{len(cases)} cases...")
                    
            except Exception as e:
                logger.error(f"Error inserting case: {e}")
                errors += 1
        
        logger.info(f"\nSeeding complete: {inserted} inserted, {errors} errors")
        
        # Verify seeding
        total = await conn.fetchval("SELECT COUNT(*) FROM settle_contributions")
        logger.info(f"Total cases in database: {total}")
        
        # Get statistics
        by_jurisdiction = await conn.fetch("""
            SELECT jurisdiction, COUNT(*) as count
            FROM settle_contributions
            GROUP BY jurisdiction
        """)
        
        by_case_type = await conn.fetch("""
            SELECT case_type, COUNT(*) as count
            FROM settle_contributions
            GROUP BY case_type
        """)
        
        logger.info("\n" + "=" * 60)
        logger.info("Database Statistics")
        logger.info("=" * 60)
        logger.info(f"Total cases: {total}")
        logger.info("\nBy Jurisdiction:")
        for row in by_jurisdiction:
            logger.info(f"  {row['jurisdiction']}: {row['count']}")
        logger.info("\nBy Case Type:")
        for row in by_case_type:
            logger.info(f"  {row['case_type']}: {row['count']}")
        logger.info("=" * 60)
        
        return True
        
    finally:
        await conn.close()


async def main():
    """Main execution"""
    import sys
    
    json_file = sys.argv[1] if len(sys.argv) > 1 else "verified_cases.json"
    database_url = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(json_file):
        logger.error(f"File not found: {json_file}")
        logger.info("\nAvailable files:")
        for f in os.listdir("."):
            if f.endswith(".json"):
                logger.info(f"  - {f}")
        return
    
    success = await seed_database(json_file, database_url)
    
    if success:
        logger.info("\n" + "=" * 60)
        logger.info("Database seeding successful!")
        logger.info("=" * 60)
    else:
        logger.error("\nDatabase seeding failed. Check connection and try again.")


if __name__ == "__main__":
    asyncio.run(main())

