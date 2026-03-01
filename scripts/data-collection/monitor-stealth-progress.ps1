# Monitor stealth scraper progress in real-time
$logFile = "casemine-stealth-scraper.log"
$outputFile = "settlement_cases_stealth_*.json"

Write-Host "`n=== Monitoring Stealth Scraper Progress ===" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop monitoring`n" -ForegroundColor Yellow

$lastLineCount = 0
$caseCount = 0
$lastCheckpoint = 0

while ($true) {
    Clear-Host
    Write-Host "=== STEALTH SCRAPER STATUS ===" -ForegroundColor Cyan
    Write-Host ""
    
    # Check log file
    if (Test-Path $logFile) {
        $lines = Get-Content $logFile
        $newLines = $lines[$lastLineCount..($lines.Count - 1)]
        
        foreach ($line in $newLines) {
            if ($line -match "SUCCESS! Case #(\d+)") {
                $caseCount = [int]$matches[1]
                Write-Host "✅ CASE #$caseCount COLLECTED!" -ForegroundColor Green -NoNewline
                Write-Host " - $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray
            }
            elseif ($line -match "\[(\d+)/(\d+)\]") {
                $current = $matches[1]
                $total = $matches[2]
                $percent = [math]::Round(($current / $total) * 100, 1)
                Write-Host "   Processing: $current/$total ($percent%)" -ForegroundColor Yellow
            }
            elseif ($line -match "Blocked|403|CAPTCHA") {
                Write-Host "   ⚠️  $line" -ForegroundColor Red
            }
        }
        
        $lastLineCount = $lines.Count
    }
    
    # Check output files
    $jsonFiles = Get-ChildItem -Filter $outputFile -ErrorAction SilentlyContinue
    if ($jsonFiles) {
        Write-Host "`n📊 Output Files:" -ForegroundColor Cyan
        foreach ($file in $jsonFiles) {
            try {
                $json = Get-Content $file.FullName -Raw | ConvertFrom-Json -ErrorAction Stop
                $count = if ($json -is [array]) { $json.Count } else { 0 }
                $size = [math]::Round($file.Length / 1KB, 2)
                $modified = $file.LastWriteTime.ToString("HH:mm:ss")
                Write-Host "   $($file.Name): $count cases ($size KB) - Updated: $modified" -ForegroundColor White
                
                if ($count -gt $lastCheckpoint) {
                    Write-Host "   ⬆️  NEW CASES ADDED!" -ForegroundColor Green
                    $lastCheckpoint = $count
                }
            } catch {
                Write-Host "   $($file.Name): (incomplete/processing...)" -ForegroundColor Yellow
            }
        }
    }
    
    # Summary
    Write-Host "`n📈 Summary:" -ForegroundColor Cyan
    Write-Host "   Cases collected: $caseCount" -ForegroundColor $(if ($caseCount -gt 0) { "Green" } else { "Yellow" })
    Write-Host "   Last update: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
    
    Start-Sleep -Seconds 10
}
