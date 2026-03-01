# Simple live count display - shows incremental updates
$logFile = "casemine-stealth-scraper.log"
$jsonFile = "settlement_cases_stealth_126.json"

$lastLogCount = 0
$lastJsonCount = 0
$lastValidCount = 0

Write-Host "`n=== LIVE COUNT MONITOR ===" -ForegroundColor Cyan
Write-Host "Watching for count increases..." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Gray

while ($true) {
    $currentTime = Get-Date -Format "HH:mm:ss"
    
    # Get log count
    if (Test-Path $logFile) {
        $log = Get-Content $logFile -Raw
        $logCount = ([regex]::Matches($log, "SUCCESS! Case #")).Count
    } else {
        $logCount = 0
    }
    
    # Get JSON count
    if (Test-Path $jsonFile) {
        try {
            $json = Get-Content $jsonFile -Raw | ConvertFrom-Json -ErrorAction Stop
            $jsonCount = if ($json -is [array]) { $json.Count } else { 0 }
            $validCount = ($json | Where-Object { $_.case_name -ne "Captcha" -and $_.case_name -ne $null -and $_.case_name.Length -gt 3 }).Count
        } catch {
            $jsonCount = 0
            $validCount = 0
        }
    } else {
        $jsonCount = 0
        $validCount = 0
    }
    
    # Check for increases
    if ($logCount -gt $lastLogCount) {
        $increase = $logCount - $lastLogCount
        Write-Host "`n[$currentTime] COUNT INCREASED!" -ForegroundColor Green
        Write-Host "   Log: $lastLogCount -> $logCount (+$increase)" -ForegroundColor White
        if ($jsonCount -gt $lastJsonCount) {
            Write-Host "   JSON: $lastJsonCount -> $jsonCount (+$($jsonCount - $lastJsonCount))" -ForegroundColor Cyan
        }
        if ($validCount -gt $lastValidCount) {
            Write-Host "   Valid: $lastValidCount -> $validCount (+$($validCount - $lastValidCount))" -ForegroundColor Green
        }
        Write-Host "   Total: $logCount cases collected" -ForegroundColor Yellow
        Write-Host ""
        $lastLogCount = $logCount
        $lastJsonCount = $jsonCount
        $lastValidCount = $validCount
    } else {
        # Show current status
        Write-Host "[$currentTime] Current: $logCount cases (JSON: $jsonCount, Valid: $validCount) - Working...`r" -ForegroundColor Gray -NoNewline
    }
    
    Start-Sleep -Seconds 30
}
