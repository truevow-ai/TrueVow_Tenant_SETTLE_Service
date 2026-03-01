"""
Database Seeding Script
Seeds SETTLE database with anonymized court records data

Usage:
    python seed-database.py --file collected_cases.json
    python seed-database.py --file collected_cases.sql
"""

import argparse
import json
import asyncio
import asyncpg
from typing import List, Dict
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseSeeder:
    """Seeds SETTLE database with anonymized case data"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
    
    async def connect(self):
        """Connect to database"""
        try:
            self.conn = await asyncpg.connect(self.database_url)
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from database"""
        if self.conn:
            await self.conn.close()
            logger.info("Disconnected from database")
    
    async def seed_from_json(self, json_file: str, skip_verification: bool = False):
        """Seed database from JSON file"""
        logger.info(f"Loading data from {json_file}")
        
        with open(json_file, 'r') as f:
            cases = json.load(f)
        
        # Check if this is a verification report (has verification_status)
        if cases and isinstance(cases, list) and len(cases) > 0:
            if 'verification_status' in cases[0]:
                # Filter to only verified cases
                verified_cases = [c for c in cases if c.get('verification_status') == 'verified']
                if not skip_verification and len(verified_cases) < len(cases):
                    logger.warning(f"Found {len(cases)} total cases, but only {len(verified_cases)} are verified")
                    logger.warning("Only verified cases will be seeded. Use --skip-verification to seed all cases.")
                    cases = verified_cases
        
        logger.info(f"Found {len(cases)} cases to seed")
        
        inserted = 0
        errors = 0
        
        for case in cases:
            try:
                await self.insert_case(case)
                inserted += 1
                
                if inserted % 10 == 0:
                    logger.info(f"Inserted {inserted}/{len(cases)} cases...")
                    
            except Exception as e:
                logger.error(f"Error inserting case: {e}")
                errors += 1
        
        logger.info(f"Seeding complete: {inserted} inserted, {errors} errors")
        return inserted, errors
    
    async def insert_case(self, case: Dict):
        """Insert a single case into database"""
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
        
        await self.conn.execute(
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
            'approved',  # Pre-approved since from public records
            True,  # Consent confirmed
            datetime.now()
        )
    
    async def verify_seeding(self) -> Dict:
        """Verify seeded data"""
        total = await self.conn.fetchval("SELECT COUNT(*) FROM settle_contributions")
        
        by_jurisdiction = await self.conn.fetch("""
            SELECT jurisdiction, COUNT(*) as count
            FROM settle_contributions
            GROUP BY jurisdiction
        """)
        
        by_case_type = await self.conn.fetch("""
            SELECT case_type, COUNT(*) as count
            FROM settle_contributions
            GROUP BY case_type
        """)
        
        return {
            'total': total,
            'by_jurisdiction': {row['jurisdiction']: row['count'] for row in by_jurisdiction},
            'by_case_type': {row['case_type']: row['count'] for row in by_case_type}
        }


async def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Seed SETTLE database with court records')
    parser.add_argument('--file', required=True, help='JSON file with case data')
    parser.add_argument('--database-url', help='Database connection URL (or use DATABASE_URL env var)')
    parser.add_argument('--verify', action='store_true', help='Verify seeding after completion')
    parser.add_argument('--skip-verification', action='store_true', help='Skip verification check (not recommended)')
    
    args = parser.parse_args()
    
    # Get database URL
    database_url = args.database_url or os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("Database URL required (--database-url or DATABASE_URL env var)")
        return
    
    seeder = DatabaseSeeder(database_url)
    
    try:
        await seeder.connect()
        await seeder.seed_from_json(args.file, skip_verification=args.skip_verification)
        
        if args.verify:
            stats = await seeder.verify_seeding()
            logger.info("=" * 60)
            logger.info("Seeding Verification")
            logger.info("=" * 60)
            logger.info(f"Total cases: {stats['total']}")
            logger.info(f"By jurisdiction: {stats['by_jurisdiction']}")
            logger.info(f"By case type: {stats['by_case_type']}")
            logger.info("=" * 60)
    
    finally:
        await seeder.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

