# Continuous monitoring and auto-restart script for stealth scraper
# Keeps the scraper running and restarts if it stops

$scriptDir = "C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\2025-TrueVow-Settle-Service\scripts\data-collection"
$urlFile = "all_500_case_urls_aggressive.txt"
$maxCases = 126
$outputFile = "settlement_cases_stealth_126.json"
$logFile = "casemine-stealth-scraper.log"

Write-Host "=== Stealth Scraper Auto-Monitor ===" -ForegroundColor Cyan
Write-Host "This script will keep the scraper running continuously"
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

$checkInterval = 60  # Check every 60 seconds
$lastCaseCount = 0
$stuckCount = 0

while ($true) {
    Clear-Host
    Write-Host "=== Stealth Scraper Monitor ===" -ForegroundColor Cyan
    Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n" -ForegroundColor Gray
    
    # Check if Python process is running
    $pythonProcess = Get-Process python -ErrorAction SilentlyContinue
    
    if (-not $pythonProcess) {
        Write-Host "⚠️  Scraper stopped! Restarting..." -ForegroundColor Yellow
        
        # Find best URL file
        $urlFiles = @(
            "all_500_case_urls_aggressive.txt",
            "all_500_case_urls_slow_scroll.txt",
            "all_500_case_urls_infinite_scroll.txt",
            "all_500_case_urls_paginated.txt",
            "all_500_case_urls.txt"
        )
        
        $bestFile = $null
        $bestCount = 0
        
        foreach ($file in $urlFiles) {
            $filePath = Join-Path $scriptDir $file
            if (Test-Path $filePath) {
                $count = (Get-Content $filePath).Count
                if ($count -gt $bestCount) {
                    $bestCount = $count
                    $bestFile = $file
                }
            }
        }
        
        if ($bestFile) {
            Write-Host "Starting with: $bestFile ($bestCount URLs)" -ForegroundColor Green
            
            $output = "settlement_cases_stealth_$bestCount.json"
            
            Start-Process python -ArgumentList `
                "scrape-casemine-stealth.py", `
                "--urls", $bestFile, `
                "--max-cases", $bestCount, `
                "--headless", `
                "--output", $output `
                -WorkingDirectory $scriptDir `
                -WindowStyle Hidden
            
            Start-Sleep -Seconds 5
            Write-Host "✅ Scraper restarted!`n" -ForegroundColor Green
        } else {
            Write-Host "❌ No URL files found!" -ForegroundColor Red
        }
    } else {
        Write-Host "✅ Scraper running (PID: $($pythonProcess.Id))" -ForegroundColor Green
    }
    
    # Check progress
    $logPath = Join-Path $scriptDir $logFile
    if (Test-Path $logPath) {
        $log = Get-Content $logPath
        $successCount = ($log | Select-String "SUCCESS! Case #").Count
        
        if ($successCount -gt $lastCaseCount) {
            Write-Host "`n📈 Progress: $successCount cases collected" -ForegroundColor Cyan
            $lastCaseCount = $successCount
            $stuckCount = 0
        } elseif ($successCount -eq $lastCaseCount -and $successCount -gt 0) {
            $stuckCount++
            if ($stuckCount -gt 5) {
                Write-Host "`n⚠️  No progress in last 5 checks - may be stuck" -ForegroundColor Yellow
            }
        }
        
        # Show last few log lines
        Write-Host "`nRecent activity:" -ForegroundColor Yellow
        Get-Content $logPath -Tail 5 | ForEach-Object {
            Write-Host "  $_" -ForegroundColor Gray
        }
    }
    
    # Check output file
    $outputPath = Join-Path $scriptDir $outputFile
    if (Test-Path $outputPath) {
        try {
            $json = Get-Content $outputPath -Raw | ConvertFrom-Json -ErrorAction Stop
            $fileCount = if ($json -is [array]) { $json.Count } else { 0 }
            $fileSize = [math]::Round((Get-Item $outputPath).Length / 1KB, 2)
            $lastModified = (Get-Item $outputPath).LastWriteTime
            
            Write-Host "`n📊 Output File:" -ForegroundColor Cyan
            Write-Host "  Cases: $fileCount" -ForegroundColor White
            Write-Host "  Size: $fileSize KB" -ForegroundColor White
            Write-Host "  Updated: $($lastModified.ToString('HH:mm:ss'))" -ForegroundColor White
        } catch {
            Write-Host "`n📊 Output file exists but is incomplete" -ForegroundColor Yellow
        }
    }
    
    Write-Host "`n⏳ Next check in $checkInterval seconds..." -ForegroundColor Gray
    Write-Host "(Press Ctrl+C to stop monitoring)`n" -ForegroundColor DarkGray
    
    Start-Sleep -Seconds $checkInterval
}
