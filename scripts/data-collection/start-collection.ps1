# Start Data Collection Process
# Guides through manual collection first, then automated

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SETTLE Database - Data Collection" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Manual Collection (Recommended First)" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Visit court websites:" -ForegroundColor White
Write-Host "   - Miami-Dade: https://www2.miami-dadeclerk.com/cjis/" -ForegroundColor Gray
Write-Host "   - Los Angeles: https://www.lacourt.org/casesummary/ui/" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Search for personal injury cases" -ForegroundColor White
Write-Host "3. Collect 5-10 sample cases manually" -ForegroundColor White
Write-Host "4. Use 'manual-collection-template.json' as a guide" -ForegroundColor White
Write-Host "5. Save your collection to 'manually_collected_cases.json'" -ForegroundColor White
Write-Host ""
Write-Host "Press Enter when you have collected sample cases..." -ForegroundColor Yellow
Read-Host

# Check if manual collection file exists
if (Test-Path "manually_collected_cases.json") {
    Write-Host ""
    Write-Host "Found manually_collected_cases.json" -ForegroundColor Green
    Write-Host "Creating verification report..." -ForegroundColor Yellow
    
    # Create verification report from manual collection
    python -c @"
import json
from datetime import datetime

with open('manually_collected_cases.json', 'r') as f:
    cases = json.load(f)

report = {
    'collection_date': datetime.now().isoformat(),
    'total_cases': len(cases),
    'verification_instructions': {
        'purpose': 'Verify that collected data is authentic',
        'steps': [
            '1. Review each case source_url',
            '2. Verify it links to real court records',
            '3. Mark verification status'
        ]
    },
    'cases': []
}

for idx, case in enumerate(cases, 1):
    report['cases'].append({
        'case_number': idx,
        'jurisdiction': case.get('jurisdiction'),
        'case_type': case.get('case_type'),
        'outcome_amount_range': case.get('outcome_amount_range'),
        'filing_year': case.get('filing_year'),
        'source_url': case.get('source_url'),
        'case_reference': case.get('case_reference'),
        'collection_date': case.get('collection_date'),
        'collector_notes': case.get('collector_notes'),
        'verification_status': 'pending',
        'verification_notes': '',
        'verified_by': '',
        'verification_date': ''
    })

with open('verification_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(f'Created verification report with {len(cases)} cases')
"@
    
    Write-Host ""
    Write-Host "Verification report created: verification_report.json" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next step: Verify the collected data" -ForegroundColor Yellow
    Write-Host "Run: python verify-collected-data.py --file verification_report.json" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "No manually_collected_cases.json found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Would you like to:" -ForegroundColor White
    Write-Host "1. Start manual collection (recommended)" -ForegroundColor Cyan
    Write-Host "2. Try automated collection (requires website selectors)" -ForegroundColor Cyan
    Write-Host ""
    $choice = Read-Host "Enter choice (1 or 2)"
    
    if ($choice -eq "1") {
        Write-Host ""
        Write-Host "Manual Collection Guide:" -ForegroundColor Green
        Write-Host "1. Open manual-collection-template.json" -ForegroundColor White
        Write-Host "2. Visit court websites and collect case data" -ForegroundColor White
        Write-Host "3. Fill in the template with real case data" -ForegroundColor White
        Write-Host "4. Save as manually_collected_cases.json" -ForegroundColor White
        Write-Host "5. Run this script again to create verification report" -ForegroundColor White
    } elseif ($choice -eq "2") {
        Write-Host ""
        Write-Host "Starting automated collection..." -ForegroundColor Yellow
        Write-Host "Note: This requires actual website selectors" -ForegroundColor Yellow
        Write-Host ""
        python collect-court-records.py
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Collection process started" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

