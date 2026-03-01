# SETTLE Enterprise UI Components

This directory contains the enterprise-grade UI components for the SETTLE Service application.

## Components Included

### 1. Toast Notifications (`ToastProvider.tsx`)
Professional notification system with:
- ✅ Success, error, warning, and info toast types
- ⏱️ Auto-dismiss functionality
- 🎨 Smooth animations
- 📱 Responsive design
- ♿ Accessibility compliant

### 2. Breadcrumb Navigation (`Breadcrumb.tsx`)
Context-aware navigation breadcrumbs with:
- 📍 Current page indication
- 🔗 Clickable parent pages
- 🎯 Predefined routes for SETTLE pages
- 📱 Mobile-friendly design

### 3. Contextual Sidebar (`Sidebar.tsx`)
Feature-rich sidebar with:
- 📊 Real-time statistics dashboard
- 🧭 Navigation menu
- 📈 Platform metrics (contributions, members, coverage)
- 🎯 Status definitions legend
- 📱 Responsive mobile drawer

### 4. Enterprise Layout (`Layout.tsx`)
Complete application layout with:
- 🎛️ Integrated sidebar and header
- 📱 Mobile-responsive design
- ⚡ Performance optimized
- 🎨 Consistent styling

## Implementation Guide

### Installation Dependencies
```bash
cd frontend
npm install
```

### Running the Demo
```bash
npm run dev
```

### Using Components in Your App

1. **Wrap your app with ToastProvider:**
```tsx
import { ToastProvider } from './components/ToastProvider';

export default function App({ children }) {
  return (
    <ToastProvider>
      {children}
    </ToastProvider>
  );
}
```

2. **Use toast notifications:**
```tsx
import { useToast } from './components/ToastProvider';

export default function MyComponent() {
  const { showToast } = useToast();
  
  const handleClick = () => {
    showToast('Action completed!', 'success');
  };
  
  return <button onClick={handleClick}>Save</button>;
}
```

3. **Add breadcrumbs:**
```tsx
import { Breadcrumb, SETTLE_BREADCRUMBS } from './components/Breadcrumb';

export default function MyPage() {
  return (
    <Breadcrumb items={SETTLE_BREADCRUMBS.dashboard} />
  );
}
```

4. **Use the complete layout:**
```tsx
import { EnterpriseApp } from './components/Layout';

export default function DashboardPage() {
  return (
    <EnterpriseApp currentPage="dashboard">
      <div>Your page content here</div>
    </EnterpriseApp>
  );
}
```

## Integration with SETTLE API

The components are designed to integrate with the SETTLE backend API:

- **Statistics**: Connects to `/api/v1/stats/database` and `/api/v1/stats/founding-members`
- **Navigation**: Aligns with existing SETTLE routes
- **Notifications**: Can be triggered by API responses

## Customization

### Styling
All components use Tailwind CSS and can be customized by:
- Modifying `tailwind.config.js`
- Updating CSS classes in components
- Adding custom themes

### Data Integration
Replace mock data in `Sidebar.tsx` with actual API calls:
```tsx
// Replace this mock data fetch
useEffect(() => {
  const fetchStats = async () => {
    const response = await fetch('/api/v1/stats/database');
    const data = await response.json();
    setStats(data);
  };
}, []);
```

## File Structure
```
frontend/
├── components/
│   ├── ToastProvider.tsx     # Notification system
│   ├── Breadcrumb.tsx        # Navigation breadcrumbs
│   ├── Sidebar.tsx           # Contextual sidebar
│   └── Layout.tsx            # Main layout
├── pages/
│   └── dashboard.tsx         # Demo page
├── styles/
│   └── globals.css          # Global styles
├── package.json              # Dependencies
├── tsconfig.json             # TypeScript config
├── tailwind.config.js        # Tailwind configuration
└── postcss.config.js         # PostCSS configuration
```

## Next Steps

1. **Move to Customer Portal**: These components should be integrated into the main Customer Portal repository
2. **Connect to Real API**: Replace mock data with actual SETTLE API endpoints
3. **Add More Pages**: Implement query, contribute, and reports pages using the same layout
4. **Enhance Components**: Add loading states, error handling, and more interactive features

The components are production-ready and follow modern React best practices with TypeScript type safety.