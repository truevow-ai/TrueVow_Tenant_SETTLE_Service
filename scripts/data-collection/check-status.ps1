# Quick status check for Casemine scraper
$outputFile = "casemine_cases.json"
$debugFile = "casemine_debug.html"

Write-Host "`n=== Casemine Scraper Status ===" -ForegroundColor Cyan

# Check output file
if (Test-Path $outputFile) {
    $size = (Get-Item $outputFile).Length
    Write-Host "Output file: EXISTS ($size bytes)" -ForegroundColor Green
    
    try {
        $content = Get-Content $outputFile -Raw
        if ($content) {
            $data = $content | ConvertFrom-Json
            Write-Host "Cases collected: $($data.Count)" -ForegroundColor Green
            if ($data.Count -gt 0) {
                Write-Host "`nSample:" -ForegroundColor Yellow
                $data | Select-Object -First 1 | ForEach-Object {
                    Write-Host "  Case: $($_.case_name)" -ForegroundColor White
                    Write-Host "  URL: $($_.source_url)" -ForegroundColor Gray
                }
            }
        }
    } catch {
        Write-Host "File exists but not yet valid JSON" -ForegroundColor Yellow
    }
} else {
    Write-Host "Output file: NOT YET CREATED" -ForegroundColor Yellow
}

# Check debug file
if (Test-Path $debugFile) {
    Write-Host "Debug HTML: EXISTS" -ForegroundColor Green
}

# Check Python processes
$pythonProcs = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcs) {
    Write-Host "`nPython processes running: $($pythonProcs.Count)" -ForegroundColor Green
} else {
    Write-Host "`nPython processes: NONE (scraper may have finished)" -ForegroundColor Yellow
}

Write-Host "`n==============================`n" -ForegroundColor Cyan
