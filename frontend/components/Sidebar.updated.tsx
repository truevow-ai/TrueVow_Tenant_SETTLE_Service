// Updated Sidebar.tsx with real API connection
// Save this to: C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow-Customer-Portal\lib\components\settle\Sidebar.tsx

"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  icon?: React.ReactNode;
  isLoading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, 
  value, 
  subtitle, 
  trend, 
  trendValue,
  icon,
  isLoading = false
}) => {
  const getTrendColor = () => {
    switch (trend) {
      case 'up': return 'text-green-600';
      case 'down': return 'text-red-600';
      case 'neutral': return 'text-gray-500';
      default: return 'text-gray-500';
    }
  };

  const getTrendIcon = () => {
    switch (trend) {
      case 'up': return '▲';
      case 'down': return '▼';
      case 'neutral': return '●';
      default: return '';
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border p-4 shadow-sm">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
          <div className="h-6 bg-gray-200 rounded w-3/4 mb-1"></div>
          <div className="h-3 bg-gray-200 rounded w-1/3"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && (
            <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="text-gray-400">
            {icon}
          </div>
        )}
      </div>
      
      {trend && trendValue && (
        <div className={`flex items-center mt-2 text-sm ${getTrendColor()}`}>
          <span className="mr-1">{getTrendIcon()}</span>
          <span>{trendValue}</span>
        </div>
      )}
    </div>
  );
};

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const pathname = usePathname();
  const [stats, setStats] = useState({
    totalContributions: 0,
    approvedContributions: 0,
    pendingContributions: 0,
    foundingMembers: 0,
    jurisdictions: 0,
    states: 0
  });
  const [loading, setLoading] = useState(true);

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

  const navItems = [
    { name: 'Dashboard', href: '/dashboard/settle', icon: '📊' },
    { name: 'Query Database', href: '/dashboard/settle/query', icon: '🔍' },
    { name: 'Contribute Data', href: '/dashboard/settle/contribute', icon: '📤' },
    { name: 'View Reports', href: '/dashboard/settle/reports', icon: '📋' },
    { name: 'My Account', href: '/dashboard/settle/account', icon: '👤' }
  ];

  const isActive = (href: string) => pathname === href;

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`fixed inset-y-0 left-0 z-50 w-80 bg-white border-r transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold">⚖️</span>
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">SETTLE</h2>
                <p className="text-xs text-gray-500">Settlement Intelligence</p>
              </div>
            </div>
            <button 
              onClick={onClose}
              className="lg:hidden text-gray-500 hover:text-gray-700"
              aria-label="Close sidebar"
            >
              ✕
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 overflow-y-auto">
            <ul className="space-y-2">
              {navItems.map((item) => (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    className={`flex items-center px-4 py-3 rounded-lg transition-colors ${
                      isActive(item.href)
                        ? 'bg-blue-50 text-blue-700 border border-blue-200'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                    onClick={onClose}
                  >
                    <span className="text-lg mr-3">{item.icon}</span>
                    <span className="font-medium">{item.name}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {/* Statistics Panel */}
          <div className="border-t p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Platform Statistics</h3>
            
            <div className="grid grid-cols-2 gap-3 mb-6">
              <StatCard
                title="Contributions"
                value={stats.totalContributions.toLocaleString()}
                subtitle="Total"
                isLoading={loading}
              />
              <StatCard
                title="Approved"
                value={stats.approvedContributions.toLocaleString()}
                subtitle="Valid cases"
                trend="up"
                trendValue="+12%"
                isLoading={loading}
              />
              <StatCard
                title="Pending"
                value={stats.pendingContributions}
                subtitle="Review queue"
                isLoading={loading}
              />
              <StatCard
                title="Members"
                value={stats.foundingMembers}
                subtitle="Active"
                isLoading={loading}
              />
            </div>

            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Jurisdictions</span>
                <span className="font-medium">{stats.jurisdictions}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">States</span>
                <span className="font-medium">{stats.states}</span>
              </div>
            </div>
          </div>

          {/* Status Definitions */}
          <div className="border-t p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Status Definitions</h3>
            
            <div className="space-y-3 text-sm">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
                <span className="text-gray-700">Approved</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div>
                <span className="text-gray-700">Pending Review</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-red-500 rounded-full mr-2"></div>
                <span className="text-gray-700">Needs Revision</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
                <span className="text-gray-700">In Progress</span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};