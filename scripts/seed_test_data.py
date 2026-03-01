"""
Test Data Seeder for SETTLE Service

Generates realistic test data for development and testing.
Creates 100+ settlement contributions across multiple jurisdictions.
"""

import os
import sys
import random
from uuid import uuid4
from datetime import datetime, timedelta
from typing import List
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
from pathlib import Path
env_local = Path(__file__).parent.parent / '.env.local'
if env_local.exists():
    load_dotenv(env_local)
else:
    load_dotenv()


class TestDataSeeder:
    """Seed test data for SETTLE service"""
    
    # Sample data pools
    JURISDICTIONS = [
        "Maricopa County, AZ",
        "Pima County, AZ",
        "Los Angeles County, CA",
        "San Diego County, CA",
        "Orange County, CA",
        "Cook County, IL",
        "Harris County, TX",
        "Dallas County, TX",
        "Miami-Dade County, FL",
        "Broward County, FL"
    ]
    
    CASE_TYPES = [
        "Motor Vehicle Accident",
        "Motorcycle Accident",
        "Truck Accident",
        "Pedestrian Accident",
        "Bicycle Accident",
        "Premises Liability (Slip/Trip/Fall)",
        "Dog Bite",
        "Medical Malpractice",
        "Product Liability",
        "Workers Compensation",
        "Wrongful Death"
    ]
    
    INJURY_CATEGORIES = [
        "Spinal Injury",
        "Traumatic Brain Injury",
        "Fractures",
        "Soft Tissue Injury",
        "Burns",
        "Amputation",
        "Internal Injuries",
        "Multiple Injuries"
    ]
    
    PRIMARY_DIAGNOSES = [
        "Herniated Disc",
        "Spinal Fracture",
        "Concussion",
        "Broken Bones",
        "Whiplash",
        "Torn Ligaments",
        "Internal Bleeding",
        "Severe Lacerations"
    ]
    
    TREATMENT_TYPES = [
        "Physical Therapy",
        "Surgery",
        "Medication Management",
        "Chiropractic Care",
        "Pain Management",
        "Rehabilitation",
        "Home Health Care"
    ]
    
    DURATION_OF_TREATMENT = [
        "<3 months",
        "3-6 months",
        "6-12 months",
        "1-2 years",
        "2+ years"
    ]
    
    IMAGING_FINDINGS = [
        "Fracture",
        "Herniated Disc",
        "Soft Tissue Damage",
        "Internal Bleeding",
        "Bone Displacement",
        "Ligament Tear"
    ]
    
    DEFENDANT_CATEGORIES = [
        "Individual",
        "Business",
        "Government Entity",
        "Unknown"
    ]
    
    OUTCOME_TYPES = [
        "Settlement",
        "Jury Verdict",
        "Arbitration Award",
        "Mediation"
    ]
    
    OUTCOME_RANGES = [
        "$0-$50k",
        "$50k-$100k",
        "$100k-$150k",
        "$150k-$225k",
        "$225k-$300k",
        "$300k-$600k",
        "$600k-$1M",
        "$1M+"
    ]
    
    POLICY_LIMITS = [
        "$15k/$30k",
        "$25k/$50k",
        "$50k/$100k",
        "$100k/$300k",
        "$250k/$500k",
        "$1M/$2M",
        "$1M+",
        "Unknown"
    ]
    
    def __init__(self, num_contributions: int = 100):
        """
        Initialize test data seeder.
        
        Args:
            num_contributions: Number of contributions to generate
        """
        self.num_contributions = num_contributions
        self.contributions = []
    
    def generate_medical_bills(self) -> float:
        """Generate realistic medical bills amount"""
        # Most cases: $5k-$100k
        # Some cases: $100k-$500k
        # Few cases: $500k-$2M
        rand = random.random()
        if rand < 0.7:  # 70% of cases
            return random.uniform(5000, 100000)
        elif rand < 0.95:  # 25% of cases
            return random.uniform(100000, 500000)
        else:  # 5% of cases
            return random.uniform(500000, 2000000)
    
    def generate_outcome_range(self, medical_bills: float) -> str:
        """Generate realistic outcome range based on medical bills"""
        # Typical multiplier: 2-5x
        # Conservative: 1.5-2x
        # Aggressive: 5-10x
        multiplier = random.uniform(1.5, 8.0)
        outcome = medical_bills * multiplier
        
        # Map to bucket
        if outcome < 50000:
            return "$0-$50k"
        elif outcome < 100000:
            return "$50k-$100k"
        elif outcome < 150000:
            return "$100k-$150k"
        elif outcome < 225000:
            return "$150k-$225k"
        elif outcome < 300000:
            return "$225k-$300k"
        elif outcome < 600000:
            return "$300k-$600k"
        elif outcome < 1000000:
            return "$600k-$1M"
        else:
            return "$1M+"
    
    def generate_contribution(self) -> dict:
        """Generate a single realistic contribution"""
        
        medical_bills = self.generate_medical_bills()
        
        contribution = {
            "id": str(uuid4()),
            "jurisdiction": random.choice(self.JURISDICTIONS),
            "case_type": random.choice(self.CASE_TYPES),
            "injury_category": random.sample(
                self.INJURY_CATEGORIES,
                k=random.randint(1, 3)
            ),
            "primary_diagnosis": random.choice(self.PRIMARY_DIAGNOSES),
            "treatment_type": random.sample(
                self.TREATMENT_TYPES,
                k=random.randint(1, 4)
            ),
            "duration_of_treatment": random.choice(self.DURATION_OF_TREATMENT),
            "imaging_findings": random.sample(
                self.IMAGING_FINDINGS,
                k=random.randint(0, 3)
            ),
            "medical_bills": round(medical_bills, 2),
            "lost_wages": round(random.uniform(0, medical_bills * 0.3), 2) if random.random() > 0.3 else None,
            "policy_limits": random.choice(self.POLICY_LIMITS),
            "defendant_category": random.choice(self.DEFENDANT_CATEGORIES),
            "outcome_type": random.choice(self.OUTCOME_TYPES),
            "outcome_amount_range": self.generate_outcome_range(medical_bills),
            "contributed_at": datetime.utcnow() - timedelta(days=random.randint(0, 730)),  # Last 2 years
            "blockchain_hash": f"ots_{uuid4().hex[:16]}",
            "consent_confirmed": True,
            "contributor_api_key_id": str(uuid4()),
            "founding_member": random.random() < 0.3,  # 30% are Founding Members
            "created_at": datetime.utcnow() - timedelta(days=random.randint(0, 730)),
            "updated_at": datetime.utcnow(),
            "status": random.choices(
                ["approved", "pending", "flagged"],
                weights=[0.85, 0.10, 0.05]
            )[0],
            "is_outlier": random.random() < 0.05,  # 5% are outliers
            "confidence_score": random.uniform(0.7, 1.0)
        }
        
        return contribution
    
    def generate_all_contributions(self) -> List[dict]:
        """Generate all test contributions"""
        
        print(f"Generating {self.num_contributions} test contributions...")
        
        self.contributions = [
            self.generate_contribution()
            for _ in range(self.num_contributions)
        ]
        
        print(f"✅ Generated {len(self.contributions)} contributions")
        return self.contributions
    
    def print_summary(self):
        """Print summary of generated data"""
        
        if not self.contributions:
            print("No contributions generated yet. Call generate_all_contributions() first.")
            return
        
        # Statistics
        approved = sum(1 for c in self.contributions if c["status"] == "approved")
        pending = sum(1 for c in self.contributions if c["status"] == "pending")
        flagged = sum(1 for c in self.contributions if c["status"] == "flagged")
        founding_members = sum(1 for c in self.contributions if c["founding_member"])
        
        jurisdictions = set(c["jurisdiction"] for c in self.contributions)
        case_types = set(c["case_type"] for c in self.contributions)
        
        print("\n" + "="*60)
        print("TEST DATA SUMMARY")
        print("="*60)
        print(f"Total Contributions: {len(self.contributions)}")
        print(f"  ✅ Approved: {approved}")
        print(f"  ⏳ Pending: {pending}")
        print(f"  🚩 Flagged: {flagged}")
        print(f"\nFounding Members: {founding_members} ({founding_members/len(self.contributions)*100:.1f}%)")
        print(f"\nJurisdictions: {len(jurisdictions)}")
        print(f"Case Types: {len(case_types)}")
        print("\nMedical Bills Range:")
        print(f"  Min: ${min(c['medical_bills'] for c in self.contributions):,.2f}")
        print(f"  Max: ${max(c['medical_bills'] for c in self.contributions):,.2f}")
        print(f"  Avg: ${sum(c['medical_bills'] for c in self.contributions) / len(self.contributions):,.2f}")
        print("="*60 + "\n")
    
    def seed_database(self):
        """
        Seed database with test data using Supabase.
        """
        try:
            from supabase import create_client, Client
        except ImportError:
            print("❌ Supabase client not installed")
            print("   Run: pip install supabase")
            return False
        
        # Get credentials
        url = (
            os.environ.get("SETTLE_DATABASE_URL") or 
            os.environ.get("SETTLE_SUPABASE_URL") or
            os.environ.get("DATABASE_URL") or
            os.environ.get("SUPABASE_URL")
        )
        key = (
            os.environ.get("SETTLE_DATABASE_SERVICE_KEY") or
            os.environ.get("SETTLE_SUPABASE_SERVICE_KEY") or
            os.environ.get("DATABASE_SERVICE_KEY") or
            os.environ.get("SUPABASE_SERVICE_KEY")
        )
        
        if not url or not key:
            print("❌ Missing database credentials")
            print("   Required: SETTLE_DATABASE_URL and SETTLE_DATABASE_SERVICE_KEY")
            return False
        
        print(f"\nSeeding database at {url}...")
        
        # Create Supabase client
        supabase: Client = create_client(url, key)
        
        # Insert contributions in batches
        batch_size = 10
        inserted = 0
        failed = 0
        
        for i in range(0, len(self.contributions), batch_size):
            batch = self.contributions[i:i+batch_size]
            
            # Convert datetime to ISO string for Supabase
            for contrib in batch:
                contrib['contributed_at'] = contrib['contributed_at'].isoformat()
                contrib['created_at'] = contrib['created_at'].isoformat()
                contrib['updated_at'] = contrib['updated_at'].isoformat()
                contrib['contributor_user_id'] = contrib.pop('contributor_api_key_id')  # Rename field
            
            try:
                response = supabase.table('settle_contributions').insert(batch).execute()
                inserted += len(batch)
                print(f"  ✅ Inserted batch {i//batch_size + 1} ({len(batch)} contributions)")
            except Exception as e:
                failed += len(batch)
                print(f"  ❌ Failed to insert batch {i//batch_size + 1}: {str(e)}")
        
        print(f"\n✅ Database seeding complete!")
        print(f"   Inserted: {inserted}")
        print(f"   Failed: {failed}")
        
        return True


def main():
    """Main function"""
    
    import argparse
    parser = argparse.ArgumentParser(description='Seed SETTLE database with test data')
    parser.add_argument('--count', type=int, default=100, help='Number of contributions to generate (default: 100)')
    parser.add_argument('--no-insert', action='store_true', help='Generate data but do not insert into database')
    args = parser.parse_args()
    
    # Generate test contributions
    seeder = TestDataSeeder(num_contributions=args.count)
    contributions = seeder.generate_all_contributions()
    seeder.print_summary()
    
    # Seed database
    if not args.no_insert:
        print("\n" + "="*60)
        print("SEEDING DATABASE")
        print("="*60)
        seeder.seed_database()
    else:
        print("\n📝 Generated test data (not inserted - use --no-insert to skip insertion)")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()

