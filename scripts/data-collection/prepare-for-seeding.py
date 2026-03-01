"""
Prepare Collected Cases for Database Seeding
Removes verification fields (not for database storage)
"""

import json
import sys

def prepare_for_seeding(input_file: str, output_file: str = "verified_cases.json"):
    """Remove verification fields and prepare for database seeding"""
    
    with open(input_file, 'r') as f:
        cases = json.load(f)
    
    # Remove verification fields (not for database)
    db_cases = []
    for case in cases:
        db_case = {
            "jurisdiction": case.get("jurisdiction"),
            "case_type": case.get("case_type"),
            "injury_category": case.get("injury_category", []),
            "primary_diagnosis": case.get("primary_diagnosis"),
            "treatment_type": case.get("treatment_type", []),
            "duration_of_treatment": case.get("duration_of_treatment"),
            "imaging_findings": case.get("imaging_findings", []),
            "medical_bills": case.get("medical_bills", 0.0),
            "lost_wages": case.get("lost_wages"),
            "policy_limits": case.get("policy_limits"),
            "defendant_category": case.get("defendant_category", "Unknown"),
            "outcome_type": case.get("outcome_type", "Settlement"),
            "outcome_amount_range": case.get("outcome_amount_range")
        }
        db_cases.append(db_case)
    
    with open(output_file, 'w') as f:
        json.dump(db_cases, f, indent=2)
    
    print(f"Prepared {len(db_cases)} cases for database seeding")
    print(f"   Saved to: {output_file}")
    print(f"   Verification fields removed (source_url, case_reference, etc.)")
    
    return output_file

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "collected_cases.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "verified_cases.json"
    
    try:
        prepare_for_seeding(input_file, output_file)
    except FileNotFoundError:
        print(f"Error: {input_file} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

