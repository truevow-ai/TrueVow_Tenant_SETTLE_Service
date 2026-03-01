#!/usr/bin/env python3
"""Clean up collected cases - remove invalid/captcha entries"""

import json
import sys

def clean_cases(input_file: str, output_file: str):
    """Remove invalid cases (captcha, empty names, etc.)"""
    with open(input_file, 'r', encoding='utf-8') as f:
        cases = json.load(f)
    
    valid_cases = []
    invalid_count = 0
    
    for case in cases:
        case_name = case.get('case_name', '').strip()
        
        # Filter out invalid cases
        if not case_name or len(case_name) < 5:
            invalid_count += 1
            continue
        
        # Only filter if the name is ONLY "Captcha" or similar
        if case_name.lower() in ['captcha', 'casemine'] or case_name.lower().startswith('captcha |'):
            invalid_count += 1
            continue
        
        if case_name == 'Unknown Case':
            invalid_count += 1
            continue
        
        # Valid case
        valid_cases.append(case)
    
    # Save cleaned cases
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(valid_cases, f, indent=2, ensure_ascii=False)
    
    print(f"Cleaned cases: {len(valid_cases)} valid, {invalid_count} removed")
    return valid_cases

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "casemine_cases.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "casemine_cases_cleaned.json"
    
    clean_cases(input_file, output_file)
