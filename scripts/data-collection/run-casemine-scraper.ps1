# Casemine Scraper Runner
# Runs the Casemine scraper with optimized settings for SETTLE database

param(
    [string[]]$SearchTerms = @("car accident", "personal injury settlement", "slip and fall"),
    [string]$Jurisdiction = "",
    [int]$MaxCases = 50,
    [switch]$ShowBrowser = $false
)

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Casemine.com Case Scraper" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python: $pythonVersion" -ForegroundColor Cyan
} catch {
    Write-Host "ERROR: Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Check if required packages are installed
Write-Host "`nChecking dependencies..." -ForegroundColor Yellow
$requiredPackages = @("playwright", "beautifulsoup4")
$missingPackages = @()

foreach ($package in $requiredPackages) {
    $result = python -c "import $($package.Replace('-', '_')); print('OK')" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Host "Installing missing packages: $($missingPackages -join ', ')" -ForegroundColor Yellow
    pip install $missingPackages
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install packages" -ForegroundColor Red
        exit 1
    }
}

# Check if Playwright browsers are installed
Write-Host "Checking Playwright browsers..." -ForegroundColor Yellow
$browserCheck = playwright --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Playwright browsers..." -ForegroundColor Yellow
    playwright install chromium
}

# Build command
$headlessFlag = if ($ShowBrowser) { "" } else { "--headless" }
$jurisdictionFlag = if ($Jurisdiction) { "--jurisdiction `"$Jurisdiction`"" } else { "" }
$searchTermsStr = ($SearchTerms | ForEach-Object { "`"$_`"" }) -join " "

$command = "python scrape-casemine.py --search $searchTermsStr $jurisdictionFlag --max-cases $MaxCases $headlessFlag --output casemine_cases.json"

Write-Host "`nRunning scraper..." -ForegroundColor Yellow
Write-Host "Command: $command`n" -ForegroundColor Gray

# Change to script directory
Push-Location $PSScriptRoot

try {
    Invoke-Expression $command
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n========================================" -ForegroundColor Green
        Write-Host "Scraping Complete!" -ForegroundColor Green
        Write-Host "========================================`n" -ForegroundColor Green
        
        if (Test-Path "casemine_cases.json") {
            $cases = Get-Content "casemine_cases.json" | ConvertFrom-Json
            Write-Host "Cases collected: $($cases.Count)" -ForegroundColor Cyan
            Write-Host "Output file: casemine_cases.json`n" -ForegroundColor Cyan
            
            Write-Host "Next steps:" -ForegroundColor Yellow
            Write-Host "1. Review casemine_cases.json" -ForegroundColor White
            Write-Host "2. Verify cases manually if needed" -ForegroundColor White
            Write-Host "3. Run: python prepare-for-seeding.py casemine_cases.json verified_cases.json" -ForegroundColor White
            Write-Host "4. Run: python seed-via-supabase-client.py verified_cases.json`n" -ForegroundColor White
        } else {
            Write-Host "WARNING: Output file not found" -ForegroundColor Yellow
        }
    } else {
        Write-Host "`nERROR: Scraper failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location
}

