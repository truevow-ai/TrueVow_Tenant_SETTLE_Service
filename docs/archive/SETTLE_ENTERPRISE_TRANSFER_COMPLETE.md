# SETTLE Enterprise UI - Manual Update Instructions

## Components Successfully Transferred ✅

The following components have been transferred to the Customer Portal:

📁 **Location:** `C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow-Customer-Portal`

### Files Copied:
- `lib\components\settle\ToastProvider.tsx`
- `lib\components\settle\Breadcrumb.tsx` 
- `lib\components\settle\Layout.tsx`
- `lib\components\settle\Sidebar.tsx` (needs manual update)
- `app\(dashboard)\dashboard\settle\dashboard.tsx`
- `styles\settle-enterprise.css`
- `SETTLE_ENV_SETUP.md`

## Manual Update Required ⚠️

### 1. Update Sidebar.tsx API Connection

**File to update:** `C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow-Customer-Portal\lib\components\settle\Sidebar.tsx`

**Replace lines 100-125** with this code:

```typescript
  // Fetch real data from SETTLE API
  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        
        // Fetch database statistics
        const dbResponse = await fetch(`${process.env.NEXT_PUBLIC_SETTLE_API_URL || 'http://localhost:3008'}/api/v1/stats/database`);
        const dbStats = await dbResponse.json();
        
        // Fetch founding member statistics
        const fmResponse = await fetch(`${process.env.NEXT_PUBLIC_SETTLE_API_URL || 'http://localhost:3008'}/api/v1/stats/founding-members`);
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
        // Fallback to zero values on error
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
```

### 2. Update Navigation Links

In the same Sidebar.tsx file, update the navItems array (around line 127):

```typescript
const navItems = [
  { name: 'Dashboard', href: '/dashboard/settle', icon: '📊' },
  { name: 'Query Database', href: '/dashboard/settle/query', icon: '🔍' },
  { name: 'Contribute Data', href: '/dashboard/settle/contribute', icon: '📤' },
  { name: 'View Reports', href: '/dashboard/settle/reports', icon: '📋' },
  { name: 'My Account', href: '/dashboard/settle/account', icon: '👤' }
];
```

## Environment Setup

### Add to Customer Portal `.env.local`:

```bash
NEXT_PUBLIC_SETTLE_API_URL=http://localhost:3008
NEXT_PUBLIC_SETTLE_API_KEY=your_api_key_here
```

For production deployment:
```bash
NEXT_PUBLIC_SETTLE_API_URL=https://your-production-url.com
```

## Testing

1. **Start SETTLE Backend:**
   ```bash
   cd C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\2025-TrueVow-Settle-Service
   python -m uvicorn app.main:app --host 0.0.0.0 --port 3008 --reload
   ```

2. **Start Customer Portal:**
   ```bash
   cd C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow-Customer-Portal
   npm run dev
   ```

3. **Visit:** http://localhost:3000/dashboard/settle

## Features Now Available

✅ **Real-time Statistics** - Pulls live data from SETTLE API
✅ **Toast Notifications** - Professional notification system
✅ **Breadcrumb Navigation** - Context-aware navigation
✅ **Responsive Sidebar** - Mobile-friendly collapsible sidebar
✅ **Status Definitions** - Clear status legend
✅ **Loading States** - Skeleton loaders during data fetch

## API Endpoints Connected

- `GET /api/v1/stats/database` - Database statistics
- `GET /api/v1/stats/founding-members` - Member statistics

The sidebar will now display real data from your SETTLE service instead of mock data!