"""
Manual Collection Helper
Interactive tool to help collect real cases from legal publications
"""

import json
from datetime import datetime
from typing import Dict

def create_case_template() -> Dict:
    """Create a template for manual case collection"""
    
    print("\n" + "=" * 60)
    print("Manual Case Collection Template")
    print("=" * 60)
    print("\nFill in the information from a real legal article or court record:\n")
    
    case = {
        "source_url": input("Source URL (article or court record): ").strip(),
        "article_title": input("Article/Record Title: ").strip(),
        "source_publication": input("Publication/Source Name: ").strip(),
        "collection_date": datetime.now().isoformat(),
        
        # Required fields
        "jurisdiction": input("Jurisdiction (e.g., 'Miami-Dade County, FL'): ").strip(),
        "case_type": input("Case Type (Motor Vehicle Accident, Slip and Fall, etc.): ").strip(),
        "outcome_amount_range": input("Settlement Range ($0-$50k, $50k-$100k, etc.): ").strip(),
        
        # Injury information
        "injury_category": [],
        "primary_diagnosis": None,
        "treatment_type": [],
        "duration_of_treatment": None,
        "imaging_findings": [],
        
        # Financial information
        "medical_bills": None,
        "lost_wages": None,
        "policy_limits": None,
        
        # Other
        "defendant_category": input("Defendant Category (Business, Individual, Unknown): ").strip() or "Unknown",
        "outcome_type": "Settlement",
        
        # Verification
        "verification_status": "needs_review",
        "verification_notes": "",
        "verified_by": "",
        "verification_date": ""
    }
    
    # Collect injury categories
    print("\nInjury Categories (press Enter after each, empty to finish):")
    while True:
        injury = input("  Injury: ").strip()
        if not injury:
            break
        case["injury_category"].append(injury)
    
    # Optional fields
    print("\nOptional Fields (press Enter to skip):")
    medical_bills = input("Medical Bills ($): ").strip()
    if medical_bills:
        try:
            case["medical_bills"] = float(medical_bills.replace('$', '').replace(',', ''))
        except:
            pass
    
    lost_wages = input("Lost Wages ($): ").strip()
    if lost_wages:
        try:
            case["lost_wages"] = float(lost_wages.replace('$', '').replace(',', ''))
        except:
            pass
    
    primary_diagnosis = input("Primary Diagnosis: ").strip()
    if primary_diagnosis:
        case["primary_diagnosis"] = primary_diagnosis
    
    # Treatment types
    print("\nTreatment Types (press Enter after each, empty to finish):")
    while True:
        treatment = input("  Treatment: ").strip()
        if not treatment:
            break
        case["treatment_type"].append(treatment)
    
    duration = input("Duration of Treatment: ").strip()
    if duration:
        case["duration_of_treatment"] = duration
    
    # Imaging findings
    print("\nImaging Findings (press Enter after each, empty to finish):")
    while True:
        finding = input("  Finding: ").strip()
        if not finding:
            break
        case["imaging_findings"].append(finding)
    
    return case


def save_case(case: Dict, filename: str = "manually_collected_cases.json"):
    """Save collected case to file"""
    
    # Load existing cases
    try:
        with open(filename, 'r') as f:
            cases = json.load(f)
    except FileNotFoundError:
        cases = []
    
    # Add new case
    cases.append(case)
    
    # Save
    with open(filename, 'w') as f:
        json.dump(cases, f, indent=2, default=str)
    
    print(f"\n✓ Case saved to {filename}")
    print(f"  Total cases: {len(cases)}")


def main():
    """Main interactive function"""
    
    print("\n" + "=" * 60)
    print("Manual Case Collection Helper")
    print("=" * 60)
    print("\nThis tool helps you collect real cases from:")
    print("  - Legal news articles")
    print("  - Law firm blog posts")
    print("  - Court record websites")
    print("  - Legal publications")
    print("\nIMPORTANT: Only collect REAL cases with verifiable sources!\n")
    
    while True:
        case = create_case_template()
        
        # Review
        print("\n" + "=" * 60)
        print("Review Case Information")
        print("=" * 60)
        print(f"Source: {case['source_url']}")
        print(f"Jurisdiction: {case['jurisdiction']}")
        print(f"Case Type: {case['case_type']}")
        print(f"Settlement Range: {case['outcome_amount_range']}")
        print(f"Injuries: {', '.join(case['injury_category']) if case['injury_category'] else 'None'}")
        print("=" * 60)
        
        confirm = input("\nSave this case? (y/n): ").strip().lower()
        if confirm == 'y':
            save_case(case)
        else:
            print("Case not saved.")
        
        another = input("\nCollect another case? (y/n): ").strip().lower()
        if another != 'y':
            break
    
    print("\n" + "=" * 60)
    print("Collection Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review manually_collected_cases.json")
    print("2. Verify each case against source URL")
    print("3. Run: python prepare-for-seeding.py manually_collected_cases.json verified_cases.json")
    print("4. Run: python seed-via-supabase-client.py verified_cases.json")


if __name__ == "__main__":
    main()

