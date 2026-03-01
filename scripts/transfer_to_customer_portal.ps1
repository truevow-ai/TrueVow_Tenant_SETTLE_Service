# Transfer SETTLE Enterprise UI Components to Customer Portal
# And connect to real API

param(
    [string]$SourceDir = "C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\2025-TrueVow-Settle-Service\frontend",
    [string]$TargetDir = "C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow-Customer-Portal"
)

Write-Host "🔄 Transferring SETTLE Enterprise UI Components..." -ForegroundColor Cyan

# Create target directories
$ComponentsDir = "$TargetDir\lib\components\settle"
$PagesDir = "$TargetDir\app\(dashboard)\dashboard\settle"
$StylesDir = "$TargetDir\styles"

New-Item -ItemType Directory -Path $ComponentsDir -Force | Out-Null
New-Item -ItemType Directory -Path $PagesDir -Force | Out-Null
New-Item -ItemType Directory -Path $StylesDir -Force | Out-Null

# Copy component files
Write-Host "📋 Copying components..." -ForegroundColor Yellow
Copy-Item "$SourceDir\components\*" "$ComponentsDir\" -Force
Write-Host "✅ Components copied"

# Copy demo page
Write-Host "📋 Copying demo page..." -ForegroundColor Yellow
Copy-Item "$SourceDir\pages\dashboard.tsx" "$PagesDir\" -Force
Write-Host "✅ Demo page copied"

# Copy styles
Write-Host "📋 Copying styles..." -ForegroundColor Yellow
Copy-Item "$SourceDir\styles\globals.css" "$StylesDir\settle-enterprise.css" -Force
Write-Host "✅ Styles copied"

# Update Sidebar.tsx to connect to real API
Write-Host "🔧 Updating Sidebar to connect to real API..." -ForegroundColor Yellow

$SidebarPath = "$ComponentsDir\Sidebar.tsx"
$SidebarContent = Get-Content $SidebarPath -Raw

# Replace the mock data fetching with real API calls
$UpdatedSidebar = $SidebarContent -replace '(?s)// Mock data fetching - replace with actual API calls.*?fetchStats\(\);\s*\}, \[\]\);', @"
  // Fetch real data from SETTLE API
  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        
        // Fetch database statistics
        const dbResponse = await fetch(`\${process.env.NEXT_PUBLIC_SETTLE_API_URL || 'http://localhost:3008'}/api/v1/stats/database`);
        const dbStats = await dbResponse.json();
        
        // Fetch founding member statistics
        const fmResponse = await fetch(`\${process.env.NEXT_PUBLIC_SETTLE_API_URL || 'http://localhost:3008'}/api/v1/stats/founding-members`);
        const fmStats = await fmResponse.json();
        
        setStats({
          totalContributions: dbStats.total_contributions || 0,
          approvedContributions: dbStats.approved_contributions || 0,
          pendingContributions: dbStats.pending_contributions || 0,
          foundingMembers: fmStats.active_members || 0,
          jurisdictions: dbStats.jurisdictions_covered || 0,
          states: dbStats.states_covered || 0
        });
      } catch (error) {
        console.error('Failed to fetch SETTLE stats:', error);
        // Fallback to mock data on error
        setStats({
          totalContributions: 0,
          approvedContributions: 0,
          pendingContributions: 0,
          foundingMembers: 0,
          jurisdictions: 0,
          states: 0
        });
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);
"@

# Write updated content back to file
$UpdatedSidebar | Out-File -FilePath $SidebarPath -Encoding UTF8
Write-Host "✅ Sidebar updated with real API connection"

# Create/update environment variables documentation
Write-Host "📝 Creating environment documentation..." -ForegroundColor Yellow

# Create environment documentation
$EnvDocsPath = "$TargetDir\SETTLE_ENV_SETUP.md"
$EnvDocsContent = @"
# SETTLE Service Environment Variables

Add these to your Customer Portal .env.local file:

NEXT_PUBLIC_SETTLE_API_URL=http://localhost:3008
NEXT_PUBLIC_SETTLE_API_KEY=your_api_key_here

For production:
NEXT_PUBLIC_SETTLE_API_URL=https://your-settle-service-url.com
"@

$EnvDocsContent | Out-File -FilePath $EnvDocsPath -Encoding UTF8
Write-Host "✅ Environment documentation created"

Write-Host "`n🎉 Transfer Complete!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. cd $TargetDir" -ForegroundColor White
Write-Host "2. Add environment variables to .env.local" -ForegroundColor White
Write-Host "3. npm run dev" -ForegroundColor White
Write-Host "4. Visit http://localhost:3000/dashboard/settle" -ForegroundColor White