"""
Manual Verification Tool
Allows manual verification of collected court records data

Usage:
    python verify-collected-data.py --file verification_report.json
"""

import argparse
import json
from typing import Dict, List
from datetime import datetime
import webbrowser

def load_verification_report(filename: str) -> Dict:
    """Load verification report"""
    with open(filename, 'r') as f:
        return json.load(f)

def save_verification_report(report: Dict, filename: str):
    """Save verification report"""
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Verification report saved to {filename}")

def verify_case_interactive(case: Dict) -> Dict:
    """Interactive verification of a single case"""
    print("\n" + "=" * 60)
    print(f"Case #{case['case_number']}")
    print("=" * 60)
    print(f"Jurisdiction: {case['jurisdiction']}")
    print(f"Case Type: {case['case_type']}")
    print(f"Outcome Range: {case['outcome_amount_range']}")
    print(f"Filing Year: {case['filing_year']}")
    print(f"\nSource URL: {case.get('source_url', 'N/A')}")
    print(f"Case Reference: {case.get('case_reference', 'N/A')}")
    
    if case.get('source_url'):
        open_url = input("\nOpen source URL in browser? (y/n): ").lower()
        if open_url == 'y':
            webbrowser.open(case['source_url'])
    
    print("\nVerification:")
    print("1. Verified - Data is authentic")
    print("2. Needs Review - Uncertain")
    print("3. Rejected - Data is not authentic")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    status_map = {
        '1': 'verified',
        '2': 'needs_review',
        '3': 'rejected'
    }
    
    case['verification_status'] = status_map.get(choice, 'needs_review')
    
    if case['verification_status'] != 'rejected':
        notes = input("Verification notes (optional): ").strip()
        case['verification_notes'] = notes
        case['verified_by'] = input("Your name/initials: ").strip()
        case['verification_date'] = datetime.now().isoformat()
    else:
        case['verification_notes'] = input("Rejection reason: ").strip()
        case['verified_by'] = input("Your name/initials: ").strip()
        case['verification_date'] = datetime.now().isoformat()
    
    return case

def generate_verification_summary(report: Dict) -> Dict:
    """Generate verification summary"""
    cases = report['cases']
    total = len(cases)
    verified = sum(1 for c in cases if c.get('verification_status') == 'verified')
    needs_review = sum(1 for c in cases if c.get('verification_status') == 'needs_review')
    rejected = sum(1 for c in cases if c.get('verification_status') == 'rejected')
    pending = sum(1 for c in cases if c.get('verification_status') == 'pending')
    
    return {
        'total': total,
        'verified': verified,
        'needs_review': needs_review,
        'rejected': rejected,
        'pending': pending,
        'verification_rate': (verified / total * 100) if total > 0 else 0
    }

def export_verified_cases(report: Dict, output_file: str):
    """Export only verified cases for database seeding"""
    verified_cases = [
        case for case in report['cases']
        if case.get('verification_status') == 'verified'
    ]
    
    # Remove verification fields (not for database)
    db_cases = []
    for case in verified_cases:
        db_case = {
            'jurisdiction': case['jurisdiction'],
            'case_type': case['case_type'],
            'outcome_amount_range': case['outcome_amount_range'],
            'filing_year': case['filing_year'],
            # Add other required fields with defaults
            'injury_category': [],
            'medical_bills': 0.0,
            'defendant_category': 'Unknown',
            'outcome_type': 'Settlement'
        }
        db_cases.append(db_case)
    
    with open(output_file, 'w') as f:
        json.dump(db_cases, f, indent=2)
    
    print(f"\nExported {len(db_cases)} verified cases to {output_file}")
    print("This file is ready for database seeding.")

def main():
    parser = argparse.ArgumentParser(description='Verify collected court records data')
    parser.add_argument('--file', required=True, help='Verification report JSON file')
    parser.add_argument('--summary', action='store_true', help='Show verification summary only')
    parser.add_argument('--export-verified', help='Export verified cases to JSON file')
    
    args = parser.parse_args()
    
    # Load report
    report = load_verification_report(args.file)
    
    if args.summary:
        # Show summary only
        summary = generate_verification_summary(report)
        print("\n" + "=" * 60)
        print("Verification Summary")
        print("=" * 60)
        print(f"Total Cases: {summary['total']}")
        print(f"Verified: {summary['verified']}")
        print(f"Needs Review: {summary['needs_review']}")
        print(f"Rejected: {summary['rejected']}")
        print(f"Pending: {summary['pending']}")
        print(f"Verification Rate: {summary['verification_rate']:.1f}%")
        print("=" * 60)
        return
    
    if args.export_verified:
        # Export verified cases
        export_verified_cases(report, args.export_verified)
        return
    
    # Interactive verification
    print("=" * 60)
    print("Court Records Data Verification")
    print("=" * 60)
    print(f"Total cases to verify: {len(report['cases'])}")
    print("\nInstructions:")
    print("1. Review each case's source URL")
    print("2. Verify it links to authentic court records")
    print("3. Mark as verified, needs review, or rejected")
    print("=" * 60)
    
    input("\nPress Enter to start verification...")
    
    # Verify each case
    for case in report['cases']:
        if case.get('verification_status') == 'pending':
            case = verify_case_interactive(case)
    
    # Save updated report
    save_verification_report(report, args.file)
    
    # Show summary
    summary = generate_verification_summary(report)
    print("\n" + "=" * 60)
    print("Verification Complete")
    print("=" * 60)
    print(f"Total Cases: {summary['total']}")
    print(f"Verified: {summary['verified']}")
    print(f"Needs Review: {summary['needs_review']}")
    print(f"Rejected: {summary['rejected']}")
    print(f"Verification Rate: {summary['verification_rate']:.1f}%")
    print("=" * 60)
    
    if summary['verified'] > 0:
        print(f"\nTo export verified cases for seeding:")
        print(f"python verify-collected-data.py --file {args.file} --export-verified verified_cases.json")

if __name__ == "__main__":
    main()

