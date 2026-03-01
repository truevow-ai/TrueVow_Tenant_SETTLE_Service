# Monitor scraper progress in real-time
$logFile = "casemine-scraper.log"
$outputFile = "settlement_cases_*.json"

Write-Host "`n=== Monitoring Scraper Progress ===" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop monitoring`n" -ForegroundColor Yellow

$lastLineCount = 0
$caseCount = 0

while ($true) {
    if (Test-Path $logFile) {
        $lines = Get-Content $logFile
        $newLines = $lines[$lastLineCount..($lines.Count - 1)]
        
        foreach ($line in $newLines) {
            # Look for success messages
            if ($line -match "SUCCESS! Case #(\d+)") {
                $caseCount = [int]$matches[1]
                Write-Host "`n✅ CASE #$caseCount SUCCESSFULLY SCRAPED!" -ForegroundColor Green
            }
            elseif ($line -match "Case Name: (.+)") {
                Write-Host "   Case: $($matches[1])" -ForegroundColor White
            }
            elseif ($line -match "Progress: (\d+) cases collected") {
                Write-Host "   Total: $($matches[1]) cases collected" -ForegroundColor Cyan
            }
            elseif ($line -match "\[(\d+)/(\d+)\]") {
                $current = $matches[1]
                $total = $matches[2]
                $percent = [math]::Round(($current / $total) * 100, 1)
                Write-Host "   Processing: $current/$total ($percent%)" -ForegroundColor Gray
            }
        }
        
        $lastLineCount = $lines.Count
    }
    
    # Check for output files
    $jsonFiles = Get-ChildItem -Filter $outputFile -ErrorAction SilentlyContinue
    if ($jsonFiles) {
        foreach ($file in $jsonFiles) {
            try {
                $json = Get-Content $file.FullName | ConvertFrom-Json
                Write-Host "`n📊 Current count in $($file.Name): $($json.Count) cases" -ForegroundColor Yellow
            } catch {
                # File might be incomplete
            }
        }
    }
    
    Start-Sleep -Seconds 5
}
