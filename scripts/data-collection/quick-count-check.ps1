# Quick count check script
$logFile = "casemine-stealth-scraper.log"
$jsonFile = "settlement_cases_stealth_126.json"

if (Test-Path $logFile) {
    $log = Get-Content $logFile -Raw
    $logCount = ([regex]::Matches($log, "SUCCESS! Case #")).Count
    Write-Host "Log count: $logCount cases" -ForegroundColor Green
} else {
    Write-Host "Log file not found" -ForegroundColor Yellow
}

if (Test-Path $jsonFile) {
    try {
        $json = Get-Content $jsonFile -Raw | ConvertFrom-Json
        $jsonCount = if ($json -is [array]) { $json.Count } else { 0 }
        $validCount = ($json | Where-Object { $_.case_name -ne "Captcha" -and $_.case_name -ne $null -and $_.case_name.Length -gt 3 }).Count
        Write-Host "JSON count: $jsonCount cases" -ForegroundColor Cyan
        Write-Host "Valid cases: $validCount cases" -ForegroundColor Green
    } catch {
        Write-Host "JSON file exists but may be incomplete" -ForegroundColor Yellow
    }
} else {
    Write-Host "JSON file not created yet" -ForegroundColor Gray
}
