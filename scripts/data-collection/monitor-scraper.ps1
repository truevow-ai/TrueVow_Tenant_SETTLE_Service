# Monitor Casemine scraper progress
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Monitoring Casemine Scraper Progress" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

$outputFile = "casemine_cases.json"
$maxWait = 300  # 5 minutes max wait
$checkInterval = 10  # Check every 10 seconds
$elapsed = 0

while ($elapsed -lt $maxWait) {
    if (Test-Path $outputFile) {
        $content = Get-Content $outputFile -Raw -ErrorAction SilentlyContinue
        if ($content) {
            try {
                $data = $content | ConvertFrom-Json
                $caseCount = $data.Count
                Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] Found $caseCount cases so far..." -ForegroundColor Cyan
                
                if ($caseCount -gt 0) {
                    Write-Host "`nSample cases collected:" -ForegroundColor Yellow
                    $data | Select-Object -First 3 | ForEach-Object {
                        Write-Host "  - $($_.case_name)" -ForegroundColor White
                    }
                }
            } catch {
                Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] File exists but not yet valid JSON..." -ForegroundColor Yellow
            }
        } else {
            Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] File exists but is empty..." -ForegroundColor Yellow
        }
    } else {
        Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] Waiting for output file..." -ForegroundColor Yellow
    }
    
    # Check if Python process is still running
    $pythonProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*scrape-casemine*" }
    if (-not $pythonProcesses) {
        Write-Host "`nScraper process completed!" -ForegroundColor Green
        break
    }
    
    Start-Sleep -Seconds $checkInterval
    $elapsed += $checkInterval
}

Write-Host "`n========================================" -ForegroundColor Green
if (Test-Path $outputFile) {
    $finalContent = Get-Content $outputFile -Raw
    if ($finalContent) {
        try {
            $finalData = $finalContent | ConvertFrom-Json
            Write-Host "FINAL RESULT: $($finalData.Count) cases collected" -ForegroundColor Green
            Write-Host "Output file: $outputFile" -ForegroundColor Cyan
        } catch {
            Write-Host "Output file exists but may be incomplete" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "No output file found yet" -ForegroundColor Yellow
}
Write-Host "========================================`n" -ForegroundColor Green
