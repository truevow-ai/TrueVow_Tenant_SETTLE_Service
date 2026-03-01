"""
Create Verification Report from Manual Collection
Converts manually collected cases into verification report
"""

import json
from datetime import datetime
import sys

def create_verification_report(input_file: str, output_file: str = 'verification_report.json'):
    """Create verification report from manually collected cases"""
    
    print(f"Loading cases from {input_file}...")
    with open(input_file, 'r') as f:
        cases = json.load(f)
    
    print(f"Found {len(cases)} cases")
    
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
            "jurisdiction": case.get("jurisdiction"),
            "case_type": case.get("case_type"),
            "outcome_amount_range": case.get("outcome_amount_range"),
            "filing_year": case.get("filing_year"),
            "source_url": case.get("source_url", ""),
            "case_reference": case.get("case_reference", ""),
            "collection_date": case.get("collection_date", datetime.now().isoformat()),
            "collector_notes": case.get("collector_notes", ""),
            "verification_status": "pending",
            "verification_notes": "",
            "verified_by": "",
            "verification_date": ""
        })
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Verification report created: {output_file}")
    print(f"   Total cases: {len(cases)}")
    print(f"\nNext steps:")
    print(f"1. Review verification_report.json")
    print(f"2. Verify each case's source_url")
    print(f"3. Run: python verify-collected-data.py --file {output_file}")
    
    return report

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "manually_collected_cases.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "verification_report.json"
    
    try:
        create_verification_report(input_file, output_file)
    except FileNotFoundError:
        print(f"❌ Error: {input_file} not found")
        print(f"\nTo start collection:")
        print(f"1. Use manual-collection-template.json as a guide")
        print(f"2. Collect cases from court websites")
        print(f"3. Save as manually_collected_cases.json")
        print(f"4. Run this script again")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

