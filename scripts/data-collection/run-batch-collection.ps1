# Batch collection strategy to avoid captchas
# Runs multiple small batches with delays between them

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Batch Case Collection Strategy" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

$outputFile = "casemine_cases_batch.json"
$allCases = @()

# Batch 1: Car accidents
Write-Host "[Batch 1/4] Collecting car accident cases..." -ForegroundColor Cyan
python scrape-casemine.py --search "car accident" --max-cases 8 --headless --output "batch1.json" 2>&1 | Out-Null
Start-Sleep -Seconds 5
if (Test-Path "batch1.json") {
    $batch1 = Get-Content "batch1.json" -Raw | ConvertFrom-Json
    $allCases += $batch1
    Write-Host "  Collected: $($batch1.Count) cases" -ForegroundColor Green
}

# Wait between batches
Write-Host "`nWaiting 60 seconds before next batch...`n" -ForegroundColor Yellow
Start-Sleep -Seconds 60

# Batch 2: Personal injury
Write-Host "[Batch 2/4] Collecting personal injury cases..." -ForegroundColor Cyan
python scrape-casemine.py --search "personal injury" --max-cases 8 --headless --output "batch2.json" 2>&1 | Out-Null
Start-Sleep -Seconds 5
if (Test-Path "batch2.json") {
    $batch2 = Get-Content "batch2.json" -Raw | ConvertFrom-Json
    $allCases += $batch2
    Write-Host "  Collected: $($batch2.Count) cases" -ForegroundColor Green
}

# Wait between batches
Write-Host "`nWaiting 60 seconds before next batch...`n" -ForegroundColor Yellow
Start-Sleep -Seconds 60

# Batch 3: Slip and fall
Write-Host "[Batch 3/4] Collecting slip and fall cases..." -ForegroundColor Cyan
python scrape-casemine.py --search "slip and fall" --max-cases 8 --headless --output "batch3.json" 2>&1 | Out-Null
Start-Sleep -Seconds 5
if (Test-Path "batch3.json") {
    $batch3 = Get-Content "batch3.json" -Raw | ConvertFrom-Json
    $allCases += $batch3
    Write-Host "  Collected: $($batch3.Count) cases" -ForegroundColor Green
}

# Wait between batches
Write-Host "`nWaiting 60 seconds before next batch...`n" -ForegroundColor Yellow
Start-Sleep -Seconds 60

# Batch 4: Motor vehicle
Write-Host "[Batch 4/4] Collecting motor vehicle cases..." -ForegroundColor Cyan
python scrape-casemine.py --search "motor vehicle accident" --max-cases 8 --headless --output "batch4.json" 2>&1 | Out-Null
Start-Sleep -Seconds 5
if (Test-Path "batch4.json") {
    $batch4 = Get-Content "batch4.json" -Raw | ConvertFrom-Json
    $allCases += $batch4
    Write-Host "  Collected: $($batch4.Count) cases" -ForegroundColor Green
}

# Combine and deduplicate
Write-Host "`n=== Combining Results ===" -ForegroundColor Green
$uniqueCases = $allCases | Where-Object { 
    $_.case_name -and 
    $_.case_name -notlike "*Captcha*" -and 
    $_.case_name -notlike "*CaseIQ*" -and 
    $_.case_name.Length -gt 10 
} | Sort-Object source_url -Unique

# Save combined results
$uniqueCases | ConvertTo-Json -Depth 10 | Out-File $outputFile -Encoding UTF8

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Collection Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Total cases collected: $($allCases.Count)" -ForegroundColor Cyan
Write-Host "Valid unique cases: $($uniqueCases.Count)" -ForegroundColor Green
Write-Host "Saved to: $outputFile" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Green

if ($uniqueCases.Count -gt 0) {
    Write-Host "Sample cases:" -ForegroundColor Yellow
    $uniqueCases | Select-Object -First 5 | ForEach-Object {
        Write-Host "  - $($_.case_name) | $($_.case_type)" -ForegroundColor White
    }
}
