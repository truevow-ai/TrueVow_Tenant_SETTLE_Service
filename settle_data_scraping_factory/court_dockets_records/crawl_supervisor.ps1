# crawl_supervisor.ps1 — keeps the SETTLE crawlers alive (auto-restart).
# Launches and re-launches: 1 CourtListener FL crawler + 11 per-state CAP crawlers.
# Dedups via a lockfile (won't run twice), detects running crawlers by python.exe only
# (never matches a shell), skips crawlers already running or finished (COMPLETE marker),
# and wraps the loop so it cannot crash. Started by the Startup-folder launcher and/or
# manually.

$ErrorActionPreference = "SilentlyContinue"

$wd   = "C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\TrueVow_Tenant_SETTLE-Service\settle_data_scraping_factory\court_dockets_records"
$out  = Join-Path $wd "out"
$log  = Join-Path $out "crawl_supervisor.log"
$lock = Join-Path $out "supervisor.lock"
New-Item -ItemType Directory -Force -Path $out | Out-Null

function Log($m) { Add-Content -Path $log -Value ("{0} {1}" -f (Get-Date).ToString("s"), $m) }

# --- lockfile dedup: exit only if the lock holds a LIVE, real supervisor process ---
if (Test-Path $lock) {
    $oldpid = (Get-Content $lock -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($oldpid) {
        $op = Get-CimInstance Win32_Process -Filter "ProcessId=$oldpid" -ErrorAction SilentlyContinue
        if ($op -and $op.CommandLine -like "*-File*crawl_supervisor.ps1*") {
            Log "supervisor already running (PID $oldpid); exiting"; exit 0
        }
    }
}
Set-Content -Path $lock -Value $PID

function StateSlug($s) { ($s.ToLower() -replace '[^a-z0-9]+', '_').Trim('_') }

$states = @("California","Texas","Florida","New York","Pennsylvania","Illinois",
            "Ohio","Georgia","North Carolina","Michigan","New Jersey")

$crawlers = @()
$crawlers += [pscustomobject]@{
    Name = "cl_fl"; Match = @("cds_courtlistener_crawl.py")
    ArgStr = "cds_courtlistener_crawl.py --hours 720 --min-delay 700"; Complete = $null
}
foreach ($st in $states) {
    $slug = StateSlug $st
    $crawlers += [pscustomobject]@{
        Name     = "cap_$slug"
        Match    = @("cds_cap_crawl.py", $slug)
        ArgStr   = "cds_cap_crawl.py --state $slug --hours 720 --min-delay 1.0 --min-year 1960"
        Complete = (Join-Path $out "cap_crawl_$slug\COMPLETE")
    }
}

Log "supervisor start (PID $PID) managing $($crawlers.Count) crawlers"

while ($true) {
    try {
        # Only python.exe processes can be crawlers — this never matches a shell.
        $procs = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction Stop |
                   Where-Object { $_.CommandLine })
        foreach ($c in $crawlers) {
            if ($c.Complete -and (Test-Path $c.Complete)) { continue }
            $running = $procs | Where-Object {
                $cmd = $_.CommandLine
                ($c.Match | ForEach-Object { $cmd -like "*$_*" }) -notcontains $false
            }
            if (-not $running) {
                Start-Process -FilePath "python" -ArgumentList $c.ArgStr -WorkingDirectory $wd -WindowStyle Hidden
                Log "launched $($c.Name): python $($c.ArgStr)"
            }
        }
    } catch {
        Log "loop error (continuing): $_"
    }
    Start-Sleep -Seconds 180
}
