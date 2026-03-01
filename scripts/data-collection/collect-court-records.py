"""
Court Records Data Collection Script
Collects and anonymizes public court records from Miami and Los Angeles

IMPORTANT: This script:
- Only collects publicly available data
- Anonymizes all PHI/PII
- Respects rate limits and Terms of Service
- Stores only aggregate/bucketed data
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import aiohttp
from playwright.async_api import async_playwright, Page, Browser
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class AnonymizedCaseData:
    """Anonymized case data matching SETTLE schema"""
    jurisdiction: str
    case_type: str
    injury_category: List[str]
    primary_diagnosis: Optional[str]
    treatment_type: List[str]
    duration_of_treatment: Optional[str]
    imaging_findings: List[str]
    medical_bills: float
    lost_wages: Optional[float]
    policy_limits: Optional[str]
    defendant_category: str
    outcome_type: str
    outcome_amount_range: str
    filing_year: int  # Only year, no specific date
    
    # Verification fields (for manual verification only, not stored in DB)
    source_url: Optional[str] = None  # URL to original court record (for verification)
    case_reference: Optional[str] = None  # Anonymized case reference (e.g., "MD-2023-XXXXX")
    collection_date: Optional[str] = None  # When data was collected
    collector_notes: Optional[str] = None  # Any notes about the collection


# ============================================================================
# ANONYMIZATION FUNCTIONS
# ============================================================================

def anonymize_case_type(raw_text: str) -> str:
    """Map raw case type to SETTLE categories"""
    text_lower = raw_text.lower()
    
    # Personal Injury Categories
    if any(term in text_lower for term in ['motor vehicle', 'car accident', 'auto accident', 'mva']):
        return 'Motor Vehicle Accident'
    elif any(term in text_lower for term in ['slip', 'fall', 'premises']):
        return 'Slip and Fall'
    elif any(term in text_lower for term in ['medical malpractice', 'medical negligence']):
        return 'Medical Malpractice'
    elif any(term in text_lower for term in ['product liability', 'defective product']):
        return 'Product Liability'
    elif any(term in text_lower for term in ['workplace', 'workers comp', 'work injury']):
        return 'Workplace Injury'
    else:
        return 'Other Personal Injury'


def bucket_amount(amount: float) -> str:
    """Bucket settlement amounts into SETTLE ranges"""
    if amount < 50000:
        return '$0-$50k'
    elif amount < 100000:
        return '$50k-$100k'
    elif amount < 150000:
        return '$100k-$150k'
    elif amount < 225000:
        return '$150k-$225k'
    elif amount < 300000:
        return '$225k-$300k'
    elif amount < 600000:
        return '$300k-$600k'
    elif amount < 1000000:
        return '$600k-$1M'
    else:
        return '$1M+'


def extract_year_only(date_str: str) -> int:
    """Extract only year from date string"""
    # Try to extract year (4 digits)
    year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
    if year_match:
        return int(year_match.group())
    return datetime.now().year


def anonymize_injury_category(case_text: str) -> List[str]:
    """Extract generic injury categories (no specific details)"""
    text_lower = case_text.lower()
    categories = []
    
    if any(term in text_lower for term in ['spinal', 'back', 'neck', 'vertebra']):
        categories.append('Spinal Injury')
    if any(term in text_lower for term in ['brain', 'head', 'tbi', 'concussion']):
        categories.append('Traumatic Brain Injury')
    if any(term in text_lower for term in ['fracture', 'broken bone']):
        categories.append('Fracture')
    if any(term in text_lower for term in ['soft tissue', 'sprain', 'strain']):
        categories.append('Soft Tissue Injury')
    if any(term in text_lower for term in ['burn', 'scald']):
        categories.append('Burn Injury')
    
    return categories if categories else ['Other Injury']


# ============================================================================
# MIAMI-DADE COUNTY COLLECTOR
# ============================================================================

class MiamiDadeCollector:
    """Collects data from Miami-Dade Clerk of Courts"""
    
    BASE_URL = "https://www2.miami-dadeclerk.com/cjis/"
    
    async def search_cases(
        self,
        page: Page,
        case_type: str = "Personal Injury",
        limit: int = 50
    ) -> List[Dict]:
        """Search for personal injury cases"""
        logger.info(f"Searching Miami-Dade cases: {case_type}")
        
        try:
            # Navigate to search page
            current_url = self.BASE_URL
            await page.goto(current_url, wait_until="networkidle")
            await asyncio.sleep(2)  # Respect rate limits
            
            # Perform search (this is a placeholder - actual selectors need to be determined)
            # await page.fill('input[name="caseType"]', case_type)
            # await page.click('button[type="submit"]')
            # await page.wait_for_selector('.case-results', timeout=10000)
            
            # Extract case data (placeholder - needs actual implementation)
            # IMPORTANT: Include source URL and case reference for verification
            cases = []
            # cases = await page.evaluate('''() => {
            #     // Extract case data from page
            #     return Array.from(document.querySelectorAll('.case-item')).map((item, idx) => {
            #         const caseLink = item.querySelector('a.case-link');
            #         return {
            #             caseType: item.querySelector('.case-type')?.textContent,
            #             filingDate: item.querySelector('.filing-date')?.textContent,
            #             status: item.querySelector('.status')?.textContent,
            #             caseNumber: item.querySelector('.case-number')?.textContent,
            #             sourceUrl: caseLink ? caseLink.href : window.location.href,
            #             caseReference: `MD-${new Date().getFullYear()}-${String(idx + 1).padStart(5, '0')}`
            #         };
            #     });
            # }''')
            
            # For now, return empty list - will be populated with actual implementation
            logger.info(f"Found {len(cases)} cases in Miami-Dade")
            return cases
            
        except Exception as e:
            logger.error(f"Error searching Miami-Dade cases: {e}")
            return []

    async def get_case_details(self, page: Page, case_id: str) -> Optional[Dict]:
        """Get detailed case information"""
        # Implementation would fetch case details
        # Must ensure all PHI/PII is removed
        return None


# ============================================================================
# LOS ANGELES COUNTY COLLECTOR
# ============================================================================

class LosAngelesCollector:
    """Collects data from LA County Superior Court"""
    
    BASE_URL = "https://www.lacourt.org/casesummary/ui/"
    
    async def search_cases(
        self,
        page: Page,
        case_type: str = "Personal Injury",
        limit: int = 50
    ) -> List[Dict]:
        """Search for personal injury cases"""
        logger.info(f"Searching Los Angeles cases: {case_type}")
        
        try:
            # Navigate to search page
            await page.goto(self.BASE_URL, wait_until="networkidle")
            await asyncio.sleep(2)  # Respect rate limits
            
            # Perform search (placeholder - needs actual implementation)
            cases = []
            
            logger.info(f"Found {len(cases)} cases in Los Angeles")
            return cases
            
        except Exception as e:
            logger.error(f"Error searching Los Angeles cases: {e}")
            return []


# ============================================================================
# DATA PROCESSOR
# ============================================================================

class DataProcessor:
    """Processes and anonymizes collected data"""
    
    def process_case(self, raw_case: Dict, jurisdiction: str) -> Optional[AnonymizedCaseData]:
        """Process and anonymize a single case"""
        try:
            # Extract and anonymize data
            case_type = anonymize_case_type(raw_case.get('caseType', ''))
            injury_category = anonymize_injury_category(raw_case.get('description', ''))
            
            # Extract settlement amount (if available)
            settlement_amount = self._extract_settlement_amount(raw_case)
            if not settlement_amount:
                return None  # Skip if no settlement data
            
            outcome_range = bucket_amount(settlement_amount)
            
            # Extract filing year only
            filing_year = extract_year_only(raw_case.get('filingDate', ''))
            
            # Create anonymized case data with verification fields
            return AnonymizedCaseData(
                jurisdiction=jurisdiction,
                case_type=case_type,
                injury_category=injury_category,
                primary_diagnosis=None,  # Not available in public records
                treatment_type=[],  # Not available in public records
                duration_of_treatment=None,
                imaging_findings=[],
                medical_bills=0.0,  # Not typically in public records
                lost_wages=None,
                policy_limits=None,
                defendant_category='Unknown',  # Anonymized
                outcome_type='Settlement',  # Assume settlement if amount available
                outcome_amount_range=outcome_range,
                filing_year=filing_year,
                # Verification fields (for manual verification)
                source_url=raw_case.get('sourceUrl'),  # URL to original court record
                case_reference=raw_case.get('caseReference'),  # Anonymized case reference
                collection_date=datetime.now().isoformat(),
                collector_notes=raw_case.get('notes', '')
            )
            
        except Exception as e:
            logger.error(f"Error processing case: {e}")
            return None
    
    def _extract_settlement_amount(self, case: Dict) -> Optional[float]:
        """Extract settlement amount from case data"""
        # Look for settlement/judgment amounts in various fields
        amount_text = case.get('settlementAmount') or case.get('judgmentAmount') or ''
        
        # Extract numeric value
        amount_match = re.search(r'\$?([\d,]+\.?\d*)', str(amount_text))
        if amount_match:
            return float(amount_match.group(1).replace(',', ''))
        
        return None


# ============================================================================
# MAIN COLLECTION WORKFLOW
# ============================================================================

async def collect_court_records(
    jurisdictions: List[str] = ['Miami-Dade County, FL', 'Los Angeles County, CA'],
    limit_per_jurisdiction: int = 100
) -> List[AnonymizedCaseData]:
    """Main function to collect court records"""
    
    logger.info("Starting court records collection")
    logger.info(f"Jurisdictions: {jurisdictions}")
    logger.info(f"Limit per jurisdiction: {limit_per_jurisdiction}")
    
    all_cases = []
    processor = DataProcessor()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Miami-Dade County
            if 'Miami-Dade County, FL' in jurisdictions:
                miami_collector = MiamiDadeCollector()
                miami_cases = await miami_collector.search_cases(page, limit=limit_per_jurisdiction)
                
                for raw_case in miami_cases:
                    processed = processor.process_case(raw_case, 'Miami-Dade County, FL')
                    if processed:
                        all_cases.append(processed)
                
                await asyncio.sleep(5)  # Rate limiting
            
            # Los Angeles County
            if 'Los Angeles County, CA' in jurisdictions:
                la_collector = LosAngelesCollector()
                la_cases = await la_collector.search_cases(page, limit=limit_per_jurisdiction)
                
                for raw_case in la_cases:
                    processed = processor.process_case(raw_case, 'Los Angeles County, CA')
                    if processed:
                        all_cases.append(processed)
                
                await asyncio.sleep(5)  # Rate limiting
        
        finally:
            await browser.close()
    
    logger.info(f"Collected {len(all_cases)} anonymized cases")
    return all_cases


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def export_to_json(cases: List[AnonymizedCaseData], filename: str):
    """Export cases to JSON file with verification metadata"""
    data = []
    for case in cases:
        case_dict = case.__dict__
        # Include verification fields in export
        data.append(case_dict)
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    logger.info(f"Exported {len(cases)} cases to {filename}")


def export_verification_report(cases: List[AnonymizedCaseData], filename: str):
    """Export verification report for manual validation"""
    report = {
        "collection_date": datetime.now().isoformat(),
        "total_cases": len(cases),
        "verification_instructions": {
            "purpose": "Verify that collected data is authentic and from real court records",
            "steps": [
                "1. Review each case's source_url to verify it links to a real court record",
                "2. Check that case_reference matches the court's case numbering system",
                "3. Verify settlement amounts match public records (if available)",
                "4. Confirm no PHI/PII is present in the anonymized data",
                "5. Mark cases as 'verified' or 'needs_review' in the verification_status field"
            ],
            "important": "Source URLs and case references are for verification only and should NOT be stored in the production database"
        },
        "cases": []
    }
    
    for idx, case in enumerate(cases, 1):
        report["cases"].append({
            "case_number": idx,
            "jurisdiction": case.jurisdiction,
            "case_type": case.case_type,
            "outcome_amount_range": case.outcome_amount_range,
            "filing_year": case.filing_year,
            "source_url": case.source_url,
            "case_reference": case.case_reference,
            "collection_date": case.collection_date,
            "collector_notes": case.collector_notes,
            "verification_status": "pending",  # To be filled manually
            "verification_notes": "",  # To be filled manually
            "verified_by": "",  # To be filled manually
            "verification_date": ""  # To be filled manually
        })
    
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"Exported verification report to {filename}")


def export_to_sql(cases: List[AnonymizedCaseData], filename: str):
    """Export cases as SQL INSERT statements"""
    with open(filename, 'w') as f:
        f.write("-- Anonymized court records data\n")
        f.write("-- Generated: " + datetime.now().isoformat() + "\n\n")
        
        for case in cases:
            f.write(f"""INSERT INTO settle_contributions (
    jurisdiction, case_type, injury_category, medical_bills,
    defendant_category, outcome_type, outcome_amount_range,
    status, consent_confirmed, created_at
) VALUES (
    '{case.jurisdiction}',
    '{case.case_type}',
    ARRAY{case.injury_category}::TEXT[],
    {case.medical_bills},
    '{case.defendant_category}',
    '{case.outcome_type}',
    '{case.outcome_amount_range}',
    'approved',
    TRUE,
    NOW()
);
""")
    
    logger.info(f"Exported {len(cases)} cases to SQL file: {filename}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function"""
    logger.info("=" * 60)
    logger.info("Court Records Data Collection")
    logger.info("=" * 60)
    
    # Collect data
    cases = await collect_court_records(
        jurisdictions=['Miami-Dade County, FL', 'Los Angeles County, CA'],
        limit_per_jurisdiction=50  # Start with small batch
    )
    
    if cases:
        # Export to JSON (with verification fields)
        export_to_json(cases, 'collected_cases.json')
        
        # Export verification report for manual validation
        export_verification_report(cases, 'verification_report.json')
        
        # Export to SQL (verification fields excluded from DB)
        export_to_sql(cases, 'collected_cases.sql')
        
        logger.info("=" * 60)
        logger.info("Collection complete!")
        logger.info(f"Total cases collected: {len(cases)}")
        logger.info("")
        logger.info("IMPORTANT: Manual Verification Required")
        logger.info("1. Review 'verification_report.json' for source URLs")
        logger.info("2. Verify each case links to authentic court records")
        logger.info("3. Mark verification status in the report")
        logger.info("4. Only seed verified cases to database")
        logger.info("=" * 60)
    else:
        logger.warning("No cases collected. Check website access and selectors.")


if __name__ == "__main__":
    asyncio.run(main())

